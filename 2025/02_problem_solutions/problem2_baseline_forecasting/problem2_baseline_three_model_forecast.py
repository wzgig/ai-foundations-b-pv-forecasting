# -*- coding: utf-8 -*-
"""
Created on 2025/5/25 09:13

@author: Prince
"""
import sys
import time
import datetime
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import plotly.graph_objects as go
import seaborn as sns
from sklearn.metrics import mean_squared_error, mean_absolute_error
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared" for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
    if (parent / "_shared").exists()
)
sys.path.insert(0, str(SHARED_DIR))

from pv_project import (  # noqa: E402
    ExperimentArtifacts,
    apply_journal_axes,
    apply_journal_figure,
    build_torch_checkpoint_signature,
    configure_matplotlib,
    daylight_metrics,
    journal_palette,
    make_tail_test_dates,
    resolve_input,
    save_torch_checkpoint,
    set_random_seed,
    set_working_directory,
    slugify_checkpoint_name,
    torch_checkpoint_path,
    try_load_torch_checkpoint,
)

set_working_directory(__file__)
configure_matplotlib()
set_random_seed(torch_module=torch)
SCRIPT_START_TIME = time.time()
ARTIFACTS = ExperimentArtifacts(__file__)
SHOW_PLOTS = False

INPUT_LENGTH = 96
FORECAST_LENGTH = 96
TEST_MONTHS = (2, 5, 8, 11)
TEST_TAIL_DAYS = 7
CAPACITY_KW = 6600
DAYLIGHT_POWER_THRESHOLD = 0.05

BATCH_SIZE = int(os.getenv("PV_FORECAST_BATCH_SIZE", "64"))
TRAINING_EPOCHS = int(os.getenv("PV_FORECAST_EPOCHS", "50"))
TRAINING_PATIENCE = int(os.getenv("PV_FORECAST_PATIENCE", "5"))
LEARNING_RATE = float(os.getenv("PV_FORECAST_LR", "0.001"))
FORCE_RETRAIN = os.getenv("PV_FORCE_RETRAIN", "0").strip().lower() in {"1", "true", "yes"}

MODEL_LABELS = {
    "PureLSTM": "PureLSTM",
    "FusionModel": "FusionModel",
    "BiFusionModel": "BiFusionModel",
}
METRIC_LABELS = {
    "E_rmse": "归一化均方根误差",
    "E_mae": "归一化平均绝对误差",
    "E_me": "归一化平均误差",
    "r": "相关系数",
    "C_R": "准确率/%",
    "Q_R": "合格率/%",
}
PALETTE = journal_palette(8)
df = pd.read_csv(resolve_input("station00.csv", __file__))
df['date_time'] = pd.to_datetime(df['date_time'])

# 添加日期信息
df['month'] = df['date_time'].dt.month
df['day'] = df['date_time'].dt.day
df['date'] = df['date_time'].dt.date

# 指定测试集：2、5、8、11 月最后 7 天
test_dates = make_tail_test_dates(
    df,
    date_col="date_time",
    months=TEST_MONTHS,
    tail_days=TEST_TAIL_DAYS,
)
if not test_dates:
    raise ValueError("未找到可用于问题2测试集的目标日期，请检查 station00.csv 的时间范围。")

df['set'] = df['date'].apply(lambda d: 'test' if d in test_dates else 'train')
df['is_daytime'] = df['power'] > DAYLIGHT_POWER_THRESHOLD

# 构造滑动窗口样本
input_length, forecast_length = INPUT_LENGTH, FORECAST_LENGTH
values = df['power'].values
date_times = df['date_time'].values
set_flags = df['set'].values

train_X, train_Y, train_timestamps = [], [], []

for i in range(len(df) - input_length - forecast_length):
    if set_flags[i] == 'train' and set_flags[i + input_length + forecast_length - 1] == 'train':
        train_X.append(values[i: i + input_length])
        train_Y.append(values[i + input_length: i + input_length + forecast_length])
        train_timestamps.append(date_times[i + input_length])

train_X = np.array(train_X, dtype=np.float32)
train_Y = np.array(train_Y, dtype=np.float32)
if len(train_X) == 0:
    raise ValueError("训练样本为空，请检查训练/测试日期划分。")

# 使用每日严格样本：前一日 96 点作为输入，目标日 96 点作为输出。
target_test_days = test_dates

strict_test_X, strict_test_Y, strict_test_timestamps = [], [], []

for test_day in target_test_days:
    prev_day = test_day - datetime.timedelta(days=1)
    input_seq = df[df['date'] == prev_day]['power'].values
    output_seq = df[df['date'] == test_day]['power'].values

    if len(input_seq) == 96 and len(output_seq) == 96:
        strict_test_X.append(input_seq)
        strict_test_Y.append(output_seq)
        strict_test_timestamps.append(pd.Timestamp(test_day))

# 替换变量
test_X = np.array(strict_test_X, dtype=np.float32)
test_Y = np.array(strict_test_Y, dtype=np.float32)
test_timestamps = np.array(strict_test_timestamps)
if len(test_X) == 0:
    raise ValueError("测试样本为空，请检查测试日期前一日是否具备完整 96 点输入。")


class LSTMBranch(nn.Module):
    def __init__(self, input_len, hidden_dim=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
        x = x.unsqueeze(-1)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

class TCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=3, dilation=1):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size,
                              padding=(kernel_size - 1) * dilation // 2, dilation=dilation)
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))

class TCNBranch(nn.Module):
    def __init__(self, input_len):
        super().__init__()
        self.net = nn.Sequential(
            TCNBlock(1, 16, dilation=1),
            TCNBlock(16, 32, dilation=2),
            TCNBlock(32, 64, dilation=4)
        )
        self.fc = nn.Linear(64, input_len)

    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.net(x)
        return self.fc(x.mean(dim=2))

class MLPBranch(nn.Module):
    def __init__(self, input_len):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_len, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, input_len)
        )

    def forward(self, x):
        return self.fc(x)

class FusionModel(nn.Module):
    def __init__(self, input_len=96):
        super().__init__()
        self.lstm_branch = LSTMBranch(input_len)
        self.tcn_branch = TCNBranch(input_len)
        self.mlp_branch = MLPBranch(input_len)

        self.attn = nn.Sequential(
            nn.Linear(3 * input_len, 128),
            nn.ReLU(),
            nn.Linear(128, 3),
            nn.Softmax(dim=1)
        )
        self.output_layer = nn.Linear(input_len, input_len)

    def forward(self, x):
        lstm_out = self.lstm_branch(x)
        tcn_out = self.tcn_branch(x)
        mlp_out = self.mlp_branch(x)

        concat = torch.cat([lstm_out, tcn_out, mlp_out], dim=1)
        weights = self.attn(concat)
        out = (weights[:, 0:1] * lstm_out +
               weights[:, 1:2] * tcn_out +
               weights[:, 2:3] * mlp_out)
        return self.output_layer(out)


# ===================== 模型定义区：新增两种模型 =====================

# 1. 单独 LSTM 模型（基线）
class PureLSTM(nn.Module):
    def __init__(self, input_len=96, hidden_dim=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(1, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
        x = x.unsqueeze(-1)
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


# 2. BiLSTM + TCN + Transformer（BiFusion）
class TransformerBlock(nn.Module):
    def __init__(self, input_dim, nhead=4, num_layers=2):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(d_model=input_dim, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

    def forward(self, x):
        return self.transformer(x)


class BiFusionModel(nn.Module):
    def __init__(self, input_len=96):
        super().__init__()
        self.bilstm = nn.LSTM(1, 64, batch_first=True, bidirectional=True)
        self.tcn = nn.Sequential(
            TCNBlock(1, 32, dilation=1),
            TCNBlock(32, 64, dilation=2)
        )
        self.transformer = TransformerBlock(input_dim=64)

        self.fc = nn.Sequential(
            nn.Linear(64 * 2 + 64 + 64, 128),
            nn.ReLU(),
            nn.Linear(128, input_len)
        )

    def forward(self, x):
        # BiLSTM
        bilstm_out, _ = self.bilstm(x.unsqueeze(-1))
        bilstm_feat = bilstm_out[:, -1, :]

        # TCN
        tcn_feat = self.tcn(x.unsqueeze(1)).mean(dim=2)

        # Transformer
        trans_feat = self.transformer(x.unsqueeze(-1).repeat(1, 1, 64))[:, -1, :]

        feat = torch.cat([bilstm_feat, tcn_feat, trans_feat], dim=1)
        return self.fc(feat)

def train_model(
    model,
    train_X,
    train_Y,
    val_split=0.1,
    batch_size=64,
    epochs=50,
    lr=0.001,
    patience=5,
    checkpoint_name=None,
    force_retrain=False,
):
    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 数据归一化
    max_power = float(train_X.max())
    if max_power <= 0:
        raise ValueError("训练集功率最大值必须大于 0，无法归一化训练。")

    checkpoint_name = checkpoint_name or model.__class__.__name__
    checkpoint_path = torch_checkpoint_path(checkpoint_name)
    ARTIFACTS.record("models", checkpoint_path)
    checkpoint_signature = build_torch_checkpoint_signature(
        model,
        train_X,
        train_Y,
        input_length=train_X.shape[1],
        batch_size=batch_size,
        epochs=epochs,
        lr=lr,
        patience=patience,
        extra={"checkpoint_name": checkpoint_name},
    )
    if not force_retrain:
        loaded, checkpoint_max_power = try_load_torch_checkpoint(
            model,
            checkpoint_path,
            checkpoint_signature,
            torch_module=torch,
            device=device,
        )
        if loaded:
            print(f"已复用训练好的模型：{checkpoint_path}", flush=True)
            return model, float(checkpoint_max_power or max_power), True

    train_X, train_Y = train_X / max_power, train_Y / max_power

    # 创建验证集
    val_size = max(1, int(len(train_X) * val_split))
    idx = np.random.permutation(len(train_X))
    val_idx, train_idx = idx[:val_size], idx[val_size:]
    if len(train_idx) == 0:
        raise ValueError("训练集过小，无法划分验证集。")

    # 转换为PyTorch张量
    X_train = torch.tensor(train_X[train_idx], dtype=torch.float32)
    Y_train = torch.tensor(train_Y[train_idx], dtype=torch.float32)
    X_val = torch.tensor(train_X[val_idx], dtype=torch.float32)
    Y_val = torch.tensor(train_Y[val_idx], dtype=torch.float32)

    # 创建数据加载器
    train_loader = DataLoader(TensorDataset(X_train, Y_train), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, Y_val), batch_size=batch_size)

    # 定义优化器和损失函数
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    best_loss, counter = float('inf'), 0

    # 训练循环
    for epoch in range(epochs):
        # 训练阶段
        model.train()
        total_loss = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * xb.size(0)

        # 验证阶段
        val_loss = 0
        model.eval()
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_loss += criterion(model(xb), yb).item() * xb.size(0)

        # 计算平均损失
        train_loss = total_loss / len(train_loader.dataset)
        val_loss /= len(val_loader.dataset)
        print(f"Epoch {epoch + 1}: Train={train_loss:.4f}, Val={val_loss:.4f}", flush=True)

        # 早停机制
        if val_loss < best_loss:
            best_loss = val_loss
            counter = 0
            save_torch_checkpoint(
                model,
                checkpoint_path,
                checkpoint_signature,
                torch_module=torch,
                max_power=max_power,
                best_val_loss=best_loss,
            )
            print(f"模型保存于 {checkpoint_path}", flush=True)
        else:
            counter += 1
            if counter >= patience:
                print(f"早停触发，最佳验证损失: {best_loss:.4f}", flush=True)
                break

    # 加载最佳模型
    loaded, _ = try_load_torch_checkpoint(
        model,
        checkpoint_path,
        checkpoint_signature,
        torch_module=torch,
        device=device,
    )
    if not loaded:
        raise RuntimeError(f"未能加载最佳模型检查点：{checkpoint_path}")
    return model, max_power, False

# ----------------------- 预测与评估 -----------------------

def daylight_arrays(true_values, pred_values, timestamps, source_df):
    """Return flattened daylight true/pred arrays aligned with target days."""

    all_true, all_pred = [], []
    for idx, ts in enumerate(pd.to_datetime(list(timestamps))):
        day_mask = (source_df['date_time'] >= ts) & (source_df['date_time'] < ts + pd.Timedelta(days=1))
        is_daytime = source_df.loc[day_mask, 'is_daytime'].values[:FORECAST_LENGTH]
        if len(is_daytime) != FORECAST_LENGTH:
            raise ValueError(f"{ts.date()} 的测试日数据不足 {FORECAST_LENGTH} 点。")
        all_true.extend(np.asarray(true_values[idx])[is_daytime])
        all_pred.extend(np.asarray(pred_values[idx])[is_daytime])

    if not all_true:
        raise ValueError("白昼样本为空，无法计算问题2评价指标。")
    return np.asarray(all_true, dtype=float), np.asarray(all_pred, dtype=float)


def evaluate_model(model, test_X, test_Y, test_timestamps, df, max_power):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    # 标准化输入
    X_tensor = torch.tensor(test_X / max_power, dtype=torch.float32).to(device)

    # 执行预测
    with torch.no_grad():
        preds = model(X_tensor).cpu().numpy() * max_power  # 反归一化
    preds = np.clip(preds, 0.0, max_power)
    true = test_Y

    # 评估白昼指标（只在白昼时间段评估误差）
    all_true, all_preds = daylight_arrays(true, preds, test_timestamps, df)

    rmse = np.sqrt(mean_squared_error(all_true, all_preds))
    mae = mean_absolute_error(all_true, all_preds)
    mape = np.mean(np.abs((np.array(all_true) - np.array(all_preds)) / (np.array(all_true) + 1e-5))) * 100

    print(f"白昼 RMSE: {rmse:.4f}  MAE: {mae:.4f}  MAPE: {mape:.2f}%", flush=True)

    return preds, rmse, mae, mape


def compute_all_metrics(true_values, pred_values, timestamps, df, capacity_kW=6600):
    """
    计算附件1中的所有误差评估指标
    :param true_values: np.array, shape = (N, 96)
    :param pred_values: np.array, shape = (N, 96)
    :param timestamps: list of datetime 起报时间
    :param df: 原始 dataframe（用于白昼判断）
    :param capacity_kW: 单位为千瓦（默认 6600）
    """
    metrics = daylight_metrics(
        true_values,
        pred_values,
        timestamps,
        df,
        capacity_kw=capacity_kW,
    )

    print(f"【附件1考核指标】基于装机容量 {capacity_kW / 1000.0:.2f} MW", flush=True)
    print(f"E_rmse: {metrics['E_rmse']:.4f}", flush=True)
    print(f"E_mae : {metrics['E_mae']:.4f}", flush=True)
    print(f"E_me  : {metrics['E_me']:.4f}", flush=True)
    print(f"r     : {metrics['r']:.4f}", flush=True)
    print(f"C_R   : {metrics['C_R']:.2f}%", flush=True)
    print(f"Q_R   : {metrics['Q_R']:.2f}%", flush=True)

    return metrics


def target_day_daylight_mask(ts, source_df):
    """Return the 96-point daylight mask for one target day."""

    target_start = pd.to_datetime(ts)
    mask = (source_df['date_time'] >= target_start) & (
        source_df['date_time'] < target_start + pd.Timedelta(days=1)
    )
    is_daytime = source_df.loc[mask, 'is_daytime'].values[:FORECAST_LENGTH]
    if len(is_daytime) != FORECAST_LENGTH:
        raise ValueError(f"{target_start.date()} 的目标日数据不足 {FORECAST_LENGTH} 点。")
    return is_daytime


def intraday_hour_axis(length=FORECAST_LENGTH):
    """Use numeric hours to avoid Matplotlib datetime timezone shifts."""

    return np.arange(length, dtype=float) * 24.0 / length


def format_intraday_axis(ax):
    ax.set_xlim(0, 24)
    ticks = np.arange(0, 25, 3)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(hour):02d}:00" for hour in ticks])
# ----------------------- 使用示例 -----------------------
# 训练模型
# model = FusionModel(input_len=96)
# model, max_power = train_model(model, train_X, train_Y)
#
# # 评估测试集
# preds, rmse, mae, mape = evaluate_model(model, test_X, test_Y, test_timestamps, df, max_power)

def export_prediction_table(preds, test_Y, test_timestamps, df, method_name='融合模型预测', output_file='prediction_table.csv'):
    """
    将模型预测结果展开为标准提交表格格式
    :param preds: 模型预测值 (N, 96)
    :param test_Y: 实际值 (N, 96)
    :param test_timestamps: 目标日 00:00:00 列表；起报时间按前一日 00:00:00 记录
    :param df: 原始 DataFrame，含真实功率
    :param method_name: 列标题中方法名
    :param output_file: 保存文件路径
    """
    records = []
    df = df.copy()
    df['date_time'] = pd.to_datetime(df['date_time'])

    for i, ts in enumerate(test_timestamps):
        target_start = pd.to_datetime(ts).replace(hour=0, minute=0, second=0)
        issue_time = target_start - pd.Timedelta(days=1)
        for j in range(FORECAST_LENGTH):
            forecast_time = target_start + pd.Timedelta(minutes=15 * j)

            records.append({
                "起报时间": issue_time,
                "预报时间": forecast_time,
                "实际功率 (MW)": float(test_Y[i, j]),
                f"{method_name} (MW)": preds[i, j]
            })

    df_pred = pd.DataFrame(records)
    target = ARTIFACTS.write_csv("predictions", output_file, df_pred, index=False)
    print(f"预测结果已保存至 {target}", flush=True)
    return target


# 使用方法
# 计算所有指标
# export_prediction_table(preds, test_Y, test_timestamps, df, method_name='问题2融合模型预测')


# metrics = compute_all_metrics(test_Y, preds, test_timestamps, df, capacity_kW=6600)

def visualize_predictions(preds, test_Y, test_timestamps, df, model_name="model"):
    model_slug = slugify_checkpoint_name(model_name)

    # ---------- 1. 可视化第一个样本的白昼时段功率曲线 ----------
    sample_index = 0
    ts = test_timestamps[sample_index]
    is_daytime = target_day_daylight_mask(ts, df)
    time_axis = intraday_hour_axis()

    sample_pred = preds[sample_index]
    sample_true = test_Y[sample_index]
    daylight_rmse = np.sqrt(mean_squared_error(sample_true[is_daytime], sample_pred[is_daytime]))

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.plot(time_axis, sample_true, label='实测功率', color=PALETTE[0], linewidth=2.1)
    ax.plot(time_axis, sample_pred, label='预测功率', color=PALETTE[1], linewidth=2.0, linestyle='--')
    ax.fill_between(time_axis, sample_true, sample_pred, color="#8c8c8c", alpha=0.18, label='绝对误差')
    ax.text(
        0.02,
        0.95,
        f'白昼RMSE={daylight_rmse:.2f} MW',
        transform=ax.transAxes,
        va='top',
        fontsize=9.5,
        bbox=dict(facecolor='white', edgecolor='#bdbdbd', linewidth=0.6, alpha=0.9),
    )
    ax.set_title(f'{MODEL_LABELS.get(model_name, model_name)} 目标日预测曲线（{pd.Timestamp(ts).date()}）')
    ax.set_xlabel('日内时刻')
    ax.set_ylabel('功率/MW')
    format_intraday_axis(ax)
    ax.legend(loc='upper left', ncol=3)
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_forecast_curve.png", fig=fig, show=SHOW_PLOTS)

    # ---------- 2. 所有白昼误差分布图 ----------
    all_true, all_pred = daylight_arrays(test_Y, preds, test_timestamps, df)
    errors = all_pred - all_true

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    sns.histplot(errors, kde=True, bins=42, color=PALETTE[2], edgecolor='white', linewidth=0.4, ax=ax)
    ax.axvline(x=0, color=PALETTE[3], linestyle='--', linewidth=1.5, label='零误差')
    ax.axvline(x=np.mean(errors), color=PALETTE[1], linestyle='-', linewidth=1.5, label='均值')
    ax.set_title(f'{MODEL_LABELS.get(model_name, model_name)} 白昼预测误差分布')
    ax.set_xlabel('预测误差/MW')
    ax.set_ylabel('频数')
    ax.legend(loc='upper right')
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_error_distribution.png", fig=fig, show=SHOW_PLOTS)

    # ---------- 3. 散点图：预测值 vs 实际值 ----------
    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    sns.scatterplot(x=all_true, y=all_pred, alpha=0.42, s=24, edgecolor=None, color=PALETTE[0], ax=ax)
    max_val = max(float(np.max(all_true)), float(np.max(all_pred)))
    ax.plot([0, max_val], [0, max_val], linestyle='--', color=PALETTE[3], label='理想预测线')
    ax.set_xlabel('实测功率/MW')
    ax.set_ylabel('预测功率/MW')
    ax.set_title(f'{MODEL_LABELS.get(model_name, model_name)} 白昼预测一致性')
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc='upper left')
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_actual_vs_predicted_scatter.png", fig=fig, show=SHOW_PLOTS)


def plot_professional_forecast(preds, test_Y, test_timestamps, df, sample_index=0, model_name="model"):
    """单日白昼预测曲线与样本级误差统计。"""
    fig, ax = plt.subplots(figsize=(9.6, 4.8))

    # 数据准备
    ts = test_timestamps[sample_index]
    is_daytime = target_day_daylight_mask(ts, df)
    time_axis = intraday_hour_axis()

    sample_true = test_Y[sample_index]
    sample_pred = preds[sample_index]
    time_str = pd.Timestamp(ts).strftime("%Y-%m-%d")

    # 增强可视化元素
    ax.plot(time_axis, sample_true, label='实测功率',
            color=PALETTE[0], lw=2, marker='o', markersize=3.5, zorder=3)
    ax.plot(time_axis, sample_pred, label='预测功率',
            color=PALETTE[1], lw=2, linestyle='--', zorder=2)

    # 误差带填充
    ax.fill_between(time_axis, sample_pred, sample_true,
                    where=sample_pred > sample_true,
                    facecolor=PALETTE[4], alpha=0.24, label='高估区间')
    ax.fill_between(time_axis, sample_pred, sample_true,
                    where=sample_pred <= sample_true,
                    facecolor=PALETTE[2], alpha=0.20, label='低估区间')

    # 统计标注
    rmse = np.sqrt(mean_squared_error(sample_true[is_daytime], sample_pred[is_daytime]))
    mae = mean_absolute_error(sample_true[is_daytime], sample_pred[is_daytime])
    ax.text(
        0.02,
        0.95,
        f'RMSE={rmse:.2f} MW\nMAE={mae:.2f} MW',
        transform=ax.transAxes,
        fontsize=9.5,
        va='top',
        bbox=dict(facecolor='white', edgecolor='#bdbdbd', linewidth=0.6, alpha=0.9),
    )

    # 图例与装饰
    ax.set_title(f'{MODEL_LABELS.get(model_name, model_name)} 单日预测细节（目标日：{time_str}）')
    ax.set_xlabel('日内时刻')
    ax.set_ylabel('功率/MW')
    format_intraday_axis(ax)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=4)
    apply_journal_axes(ax)
    fig.tight_layout()
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_figure(
        f"{model_slug}_professional_forecast_sample{sample_index}.png",
        fig=fig,
        show=SHOW_PLOTS,
    )


def plot_error_analysis(preds, test_Y, test_timestamps, df, model_name="model"):
    """多维误差分析矩阵，热力图保留全天时段，统计图仅使用白昼样本。"""
    errors = preds - test_Y
    daylight_true, daylight_pred = daylight_arrays(test_Y, preds, test_timestamps, df)
    errors_flat = daylight_pred - daylight_true
    heatmap_errors = errors.copy()
    for i, ts in enumerate(test_timestamps):
        mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
        is_daytime = df.loc[mask, 'is_daytime'].values[:FORECAST_LENGTH]
        heatmap_errors[i, ~is_daytime] = np.nan

    fig = plt.figure(figsize=(10.8, 8.2), constrained_layout=True)
    gs = fig.add_gridspec(3, 2)

    # 误差分布
    ax1 = fig.add_subplot(gs[0, 0])
    sns.histplot(x=errors_flat, kde=True, ax=ax1, bins=36,
                 color=PALETTE[0], edgecolor='white', linewidth=0.4)
    ax1.axvline(np.mean(errors_flat), color=PALETTE[3], linestyle='--', linewidth=1.4)
    ax1.set_title("白昼误差分布")
    ax1.set_xlabel("预测误差/MW")
    ax1.set_ylabel("频数")

    # 误差热力图
    ax2 = fig.add_subplot(gs[0, 1])
    sns.heatmap(heatmap_errors, cmap="RdBu_r", center=0,
                ax=ax2, cbar_kws={'label': '误差/MW'}, xticklabels=12, yticklabels=4)
    ax2.set_title("测试日白昼误差热力图")
    ax2.set_xlabel("日内 15 min 序号")
    ax2.set_ylabel("测试日序号")

    # Q-Q图
    ax3 = fig.add_subplot(gs[1, 0])
    stats.probplot(errors_flat, dist="norm", plot=ax3)
    ax3.get_lines()[0].set_markerfacecolor(PALETTE[0])
    ax3.get_lines()[0].set_markeredgecolor(PALETTE[0])
    ax3.get_lines()[1].set_color(PALETTE[3])
    ax3.title.set_text('误差正态性 Q-Q 图')

    # 残差分析
    ax4 = fig.add_subplot(gs[1, 1])
    sns.residplot(x=daylight_true, y=daylight_pred,
                  lowess=True, color=PALETTE[0],
                  scatter_kws={'alpha': 0.35, 's': 20},
                  line_kws={'color': PALETTE[3], 'linewidth': 1.6}, ax=ax4)
    ax4.set_title("白昼残差趋势")
    ax4.set_xlabel("实测功率/MW")
    ax4.set_ylabel("残差/MW")

    # 误差随日内时刻变化
    ax5 = fig.add_subplot(gs[2, :])
    daytime_error_frame = pd.DataFrame(heatmap_errors).melt(var_name="step", value_name="error").dropna()
    sns.lineplot(
        data=daytime_error_frame,
        x="step",
        y="error",
        estimator="mean",
        errorbar=("ci", 95),
        color=PALETTE[1],
        ax=ax5,
    )
    ax5.axhline(0, color=PALETTE[3], linestyle="--", linewidth=1.2)
    ax5.set_title("白昼平均误差日内变化")
    ax5.set_xlabel("日内 15 min 序号")
    ax5.set_ylabel("平均误差/MW")

    # 综合统计
    fig.suptitle(f"{MODEL_LABELS.get(model_name, model_name)} 多维误差诊断", fontsize=13)
    apply_journal_figure(fig)
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_figure(f"{model_slug}_error_analysis_matrix.png", fig=fig, show=SHOW_PLOTS)


def interactive_forecast_plot(preds, test_Y, test_timestamps, df, sample_index=0, model_name="model"):
    """交互式可视化（需安装plotly）"""
    ts = test_timestamps[sample_index]
    mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
    time_points = df.loc[mask, 'date_time'].values
    is_daytime = df.loc[mask, 'is_daytime'].values[:96]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_points[is_daytime],
        y=test_Y[sample_index][is_daytime],
        name='实际功率',
        line=dict(color='#1f77b4', width=3))
    )
    fig.add_trace(go.Scatter(
        x=time_points[is_daytime],
        y=preds[sample_index][is_daytime],
        name='预测功率',
        line=dict(color='#ff7f0e', width=3, dash='dot'))
    )

    fig.update_layout(
        title=f'交互式预测可视化 - {ts.strftime("%Y-%m-%d")}',
        xaxis_title='时间',
        yaxis_title='功率 (MW)',
        hovermode="x unified",
        template='plotly_white',
        height=500,
        margin=dict(l=50, r=50, b=80, t=80),
        annotations=[
            dict(
                text=f"样本编号: {sample_index}",
                x=0.05, y=0.95,
                showarrow=False,
                xref="paper", yref="paper"
            )
        ]
    )
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_plotly_html(
        f"{model_slug}_interactive_forecast_sample{sample_index}.html",
        fig,
    )


if __name__ == "__main__":
    model_dict = {
        "PureLSTM": PureLSTM(input_len=96),
        "FusionModel": FusionModel(input_len=96),
        "BiFusionModel": BiFusionModel(input_len=96),
    }

    predictions = {}
    metrics_all = {}
    reused_checkpoints = {}
    scalar_metrics = {}

    print(
        f"问题2样本概况：训练窗口 {len(train_X)} 个，严格测试日 {len(test_timestamps)} 天，"
        f"epochs={TRAINING_EPOCHS}, batch_size={BATCH_SIZE}, patience={TRAINING_PATIENCE}",
        flush=True,
    )

    for name, model in model_dict.items():
        print(f"\n===== 正在训练/加载模型：{name} =====", flush=True)
        model, max_power, reused = train_model(
            model,
            train_X,
            train_Y,
            batch_size=BATCH_SIZE,
            epochs=TRAINING_EPOCHS,
            lr=LEARNING_RATE,
            patience=TRAINING_PATIENCE,
            checkpoint_name=f"problem2_{name}",
            force_retrain=FORCE_RETRAIN,
        )
        preds, rmse, mae, mape = evaluate_model(model, test_X, test_Y, test_timestamps, df, max_power)
        metrics = compute_all_metrics(test_Y, preds, test_timestamps, df, capacity_kW=CAPACITY_KW)
        predictions[name] = preds
        metrics_all[name] = metrics
        reused_checkpoints[name] = reused
        scalar_metrics[name] = {"rmse_mw": rmse, "mae_mw": mae, "mape_percent": mape}

        # 每个模型分别导出预测表格
        export_prediction_table(preds, test_Y, test_timestamps, df, method_name=f"{name}预测功率", output_file=f"prediction_{name}.csv")

        # 每个模型分别可视化
        print(f"\n>> 可视化：{name}", flush=True)
        visualize_predictions(preds, test_Y, test_timestamps, df, model_name=name)
        plot_professional_forecast(preds, test_Y, test_timestamps, df, model_name=name)
        plot_error_analysis(preds, test_Y, test_timestamps, df, model_name=name)
        interactive_forecast_plot(preds, test_Y, test_timestamps, df, model_name=name)

    # ======= 指标对比表格 =======
    df_metrics = pd.DataFrame(metrics_all).T
    df_metrics.index.name = "模型"
    print("\n三模型评估指标对比：")
    print(df_metrics.round(4), flush=True)
    ARTIFACTS.write_csv("metrics", "三模型白昼指标对比.csv", df_metrics, index=True)

    # 可视化热图：不同指标量纲差异较大，颜色按列归一化，标注保留原始数值。
    normalized_metrics = (df_metrics - df_metrics.min(axis=0)) / (
        df_metrics.max(axis=0) - df_metrics.min(axis=0)
    ).replace(0, np.nan)
    normalized_metrics = normalized_metrics.fillna(0.5)
    annot_metrics = df_metrics.rename(columns=METRIC_LABELS).round(3).astype(str)
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    sns.heatmap(
        normalized_metrics.rename(columns=METRIC_LABELS),
        annot=annot_metrics,
        fmt="",
        cmap="YlGnBu",
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": "列内归一化水平"},
        ax=ax,
    )
    ax.set_title("三模型白昼评价指标对比")
    ax.set_xlabel("评价指标")
    ax.set_ylabel("模型")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=28, ha="right")
    apply_journal_axes(ax, grid=False)
    fig.tight_layout()
    ARTIFACTS.save_figure("三模型评估指标热力图_白昼时段.png", fig=fig, show=SHOW_PLOTS)

    # ======= 三模型每日对比图 (默认 index = 0) =======
    day_idx = 0
    ts = test_timestamps[day_idx]
    is_daytime = target_day_daylight_mask(ts, df)
    time_axis = intraday_hour_axis()

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    for idx, name in enumerate(predictions):
        pred = predictions[name][day_idx]
        ax.plot(time_axis, pred, label=f"{name}预测", color=PALETTE[idx + 1], linewidth=1.9)

    # 添加真实值
    true = test_Y[day_idx]
    ax.plot(time_axis, true, label="实测功率", linestyle='--', linewidth=2.2, color="#222222")
    ax.text(
        0.98,
        0.95,
        f"白昼样本数={int(is_daytime.sum())}",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=9.5,
        bbox=dict(facecolor="white", edgecolor="#bdbdbd", linewidth=0.6, alpha=0.9),
    )
    ax.set_title(f"三模型单日预测对比（目标日：{pd.Timestamp(ts).date()}）")
    ax.set_xlabel("日内时刻")
    ax.set_ylabel("功率/MW")
    format_intraday_axis(ax)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=4)
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure("三模型每日预测对比图_白昼.png", fig=fig, show=SHOW_PLOTS)

    # ======= 统一输出预测对比表格 =======
    records = []
    for i, ts in enumerate(test_timestamps):
        target_start = pd.to_datetime(ts).replace(hour=0, minute=0, second=0)
        issue_time = target_start - pd.Timedelta(days=1)
        for j in range(FORECAST_LENGTH):
            forecast_time = target_start + pd.Timedelta(minutes=15 * j)

            row = {
                "起报时间": issue_time,
                "预报时间": forecast_time,
                "实际功率": float(test_Y[i, j]),
            }
            for name in predictions:
                row[f"{name}预测功率"] = predictions[name][i, j]
            records.append(row)

    df_all_preds = pd.DataFrame(records)
    all_preds_path = ARTIFACTS.write_csv("predictions", "三模型预测结果对比表.csv", df_all_preds, index=False)
    print(f"\n已保存统一预测对比表格为：{all_preds_path}", flush=True)

    ARTIFACTS.write_summary(
        {
            "problem": "problem2_baseline_forecasting",
            "models": list(model_dict.keys()),
            "train_samples": len(train_X),
            "test_days": len(test_timestamps),
            "test_date_first_in_problem_order": str(pd.to_datetime(test_timestamps[0]).date()),
            "test_date_last_in_problem_order": str(pd.to_datetime(test_timestamps[-1]).date()),
            "test_date_min": str(pd.to_datetime(test_timestamps).min().date()),
            "test_date_max": str(pd.to_datetime(test_timestamps).max().date()),
            "input_length": INPUT_LENGTH,
            "forecast_length": FORECAST_LENGTH,
            "capacity_kw": CAPACITY_KW,
            "training": {
                "epochs": TRAINING_EPOCHS,
                "batch_size": BATCH_SIZE,
                "patience": TRAINING_PATIENCE,
                "learning_rate": LEARNING_RATE,
                "force_retrain": FORCE_RETRAIN,
                "checkpoint_reused": reused_checkpoints,
            },
            "daylight_scalar_metrics": scalar_metrics,
            "table_time_alignment": "issue_time is previous-day 00:00; forecast_time covers the target test day",
            "elapsed_seconds": time.time() - SCRIPT_START_TIME,
        }
    )
