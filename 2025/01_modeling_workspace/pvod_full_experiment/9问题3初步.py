# -*- coding: utf-8 -*-
"""
Created on 2025/5/25 09:13

@author: Prince
"""
import sys
import time
from pathlib import Path

# 开始计时
start_time = time.time()
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from sklearn.preprocessing import MinMaxScaler
from matplotlib import rcParams

# ================== 新增库导入 ==================
import matplotlib.dates as mdates
from scipy import stats
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
# ===============================================

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared" for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
    if (parent / "_shared").exists()
)
sys.path.insert(0, str(SHARED_DIR))

from pv_project import (  # noqa: E402
    ExperimentArtifacts,
    build_torch_checkpoint_signature,
    configure_matplotlib,
    minmax_scale_train_only,
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
set_random_seed()
ARTIFACTS = ExperimentArtifacts(__file__)
SHOW_PLOTS = False
#
# rcParams['font.family'] = 'SimHei'
# rcParams['axes.unicode_minus'] = False

import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文支持字体
plt.rcParams['axes.unicode_minus'] = False   # 修复负号显示问题

# ================ 全局样式设置 ==================
# plt.style.use('seaborn-whitegrid')  # 注释此行，删除无效样式调用
sns.set_theme(style='whitegrid')  # 保留Seaborn的白色网格样式配置
rcParams.update({
    'figure.figsize': (10, 5),
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'grid.linestyle': '--',
    'figure.dpi': 150
})
# ===============================================
df = pd.read_csv(resolve_input("station00.csv", __file__))

df['date_time'] = pd.to_datetime(df['date_time'])

# 添加日期信息
df['month'] = df['date_time'].dt.month
df['day'] = df['date_time'].dt.day
df['date'] = df['date_time'].dt.date

df['date_time'] = pd.to_datetime(df['date_time'])
df['date'] = df['date_time'].dt.date

# =========== 提前放置：先生成 test_dates ===========
unique_dates = df['date'].drop_duplicates().reset_index(drop=True)
test_months = [2, 5, 8, 11]
test_dates = []
for m in test_months:
    month_dates = unique_dates[unique_dates.map(lambda d: d.month) == m]
    if len(month_dates) >= 7:
        test_dates.extend(month_dates[-7:].tolist())

# =========== 然后再使用 test_dates ===========
df['set'] = df['date'].apply(lambda d: 'test' if d in test_dates else 'train')
df['is_daytime'] = df['power'] > 0.05

# 添加风向分解特征
df['wind_x'] = np.cos(np.radians(df['nwp_winddirection']))
df['wind_y'] = np.sin(np.radians(df['nwp_winddirection']))
df.drop(columns=['nwp_winddirection'], inplace=True)

# 选定用于模型的气象变量
features = ['power', 'nwp_globalirrad', 'nwp_directirrad', 'nwp_temperature',
            'nwp_humidity', 'nwp_windspeed', 'nwp_pressure', 'wind_x', 'wind_y']


# 归一化（仅对训练集拟合，全部样本变换，避免测试集信息泄漏）
from sklearn.preprocessing import MinMaxScaler

df, scalers, scaled_features = minmax_scale_train_only(df, features)


# 指定测试集：2、5、8、11 月最后 7 天
unique_dates = df['date'].drop_duplicates().reset_index(drop=True)
test_months = [2, 5, 8, 11]
test_dates = []
for m in test_months:
    month_dates = unique_dates[unique_dates.map(lambda d: d.month) == m]
    if len(month_dates) >= 7:
        test_dates.extend(month_dates[-7:].tolist())



# ========== 新增模块：多变量样本构造函数 ==========
def construct_multivariate_samples(df, scaled_features, input_len=96, forecast_len=96):
    train_X, train_Y, test_X, test_Y, test_timestamps = [], [], [], [], []
    values = df[scaled_features].values
    powers = df['power'].values
    flags = df['set'].values
    timestamps = df['date_time'].values

    for i in range(len(df) - input_len - forecast_len):
        X_seq = values[i:i + input_len]
        Y_seq = powers[i + input_len: i + input_len + forecast_len]
        ts_flag = flags[i + input_len + forecast_len - 1]
        ts_point = timestamps[i + input_len]

        if flags[i] == ts_flag == 'train':
            train_X.append(X_seq)
            train_Y.append(Y_seq)
        elif flags[i] == ts_flag == 'test':
            test_X.append(X_seq)
            test_Y.append(Y_seq)
            test_timestamps.append(ts_point)

    return (np.array(train_X), np.array(train_Y),
            np.array(test_X), np.array(test_Y),
            np.array(test_timestamps))


# 替换原始一维样本构造逻辑
scaled_features = [col + '_scaled' for col in features]  # 9个特征列名
train_X_mv, train_Y, test_X_mv, test_Y, test_timestamps = construct_multivariate_samples(
    df, scaled_features, input_len=96, forecast_len=96)

# 将多变量返回值直接覆盖原变量名（兼容后续代码）
train_X = train_X_mv  # shape=(N, 96, 9)
test_X = test_X_mv     # shape=(M, 96, 9)
# train_Y/test_Y/test_timestamps 变量名已兼容

# 可在训练流程中控制是否启用NWP数据
def get_inputs(use_mv):
    if use_mv:
        return train_X_mv, test_X_mv  # 多变量输入 shape=(N, 96, 9)
    else:
        return train_X[..., None], test_X[..., None]  # 单变量输入 shape=(N, 96, 1)

import torch
import torch.nn as nn
set_random_seed(torch_module=torch)

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

# 修改 FusionModel 中 3 个子模块：使用 x[:,:,0] 提取功率输入进行兼容
class FusionModel(nn.Module):
    def __init__(self, input_len=96):
        super().__init__()
        self.lstm_branch = LSTMBranch(input_len)
        self.tcn_branch = TCNBranch(input_len)
        self.mlp_branch = MLPBranch(input_len)
        self.attn = nn.Sequential(
            nn.Linear(3 * input_len, 128), nn.ReLU(), nn.Linear(128, 3), nn.Softmax(dim=1))
        self.output_layer = nn.Linear(input_len, input_len)

    def forward(self, x):
        x1d = x[:, :, 0]  # 提取功率作为单通道用于三支路兼容
        lstm_out = self.lstm_branch(x1d)
        tcn_out = self.tcn_branch(x1d)
        mlp_out = self.mlp_branch(x1d)
        concat = torch.cat([lstm_out, tcn_out, mlp_out], dim=1)
        weights = self.attn(concat)
        out = (weights[:, 0:1] * lstm_out + weights[:, 1:2] * tcn_out + weights[:, 2:3] * mlp_out)
        return self.output_layer(out)

# ===================== 模型定义区：新增两种模型 =====================

# ================= 模型输入调整 =================
# 所有模型前向传播 now uses x.shape = (batch, 96, num_feat)

# 修改 PureLSTM
class PureLSTM(nn.Module):
    def __init__(self, input_len=96, input_dim=9, hidden_dim=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
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


# 修改 BiFusionModel
class BiFusionModel(nn.Module):
    def __init__(self, input_len=96, input_dim=9):
        super().__init__()
        self.bilstm = nn.LSTM(input_dim, 64, batch_first=True, bidirectional=True)
        self.tcn = nn.Sequential(
            TCNBlock(1, 32, dilation=1),
            TCNBlock(32, 64, dilation=2)
        )
        self.input_proj = nn.Linear(input_dim, 64)  # <<< 添加此层
        self.transformer = TransformerBlock(input_dim=64)
        self.fc = nn.Sequential(
            nn.Linear(64 * 2 + 64 + 64, 128), nn.ReLU(), nn.Linear(128, input_len))

    def forward(self, x):
        bilstm_feat = self.bilstm(x)[0][:, -1, :]
        tcn_feat = self.tcn(x[:, :, 0].unsqueeze(1)).mean(dim=2)
        trans_feat = self.transformer(self.input_proj(x)).mean(dim=1)  # <<< 添加映射
        feat = torch.cat([bilstm_feat, tcn_feat, trans_feat], dim=1)
        return self.fc(feat)


import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader, TensorDataset


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
    checkpoint_name = checkpoint_name or model.__class__.__name__
    checkpoint_path = torch_checkpoint_path(checkpoint_name)
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
            print(f"已复用训练好的模型：{checkpoint_path}")
            return model, float(checkpoint_max_power or max_power)

    train_X, train_Y = train_X / max_power, train_Y / max_power

    # 创建验证集
    val_size = int(len(train_X) * val_split)
    idx = np.random.permutation(len(train_X))
    val_idx, train_idx = idx[:val_size], idx[val_size:]

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
        print(f"Epoch {epoch + 1}: Train={train_loss:.4f}, Val={val_loss:.4f}")

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
            print(f"模型保存于 {checkpoint_path}")
        else:
            counter += 1
            if counter >= patience:
                print(f"早停触发，最佳验证损失: {best_loss:.4f}")
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
    return model, max_power

# ----------------------- 预测与评估 -----------------------
from sklearn.metrics import mean_squared_error, mean_absolute_error

def evaluate_model(model, test_X, test_Y, test_timestamps, df, max_power):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()

    # 标准化输入
    X_tensor = torch.tensor(test_X / max_power, dtype=torch.float32).to(device)

    # 执行预测
    with torch.no_grad():
        preds = model(X_tensor).cpu().numpy() * max_power  # 反归一化
    true = test_Y

    # 评估白昼指标（只在白昼时间段评估误差）
    day_indices = []
    for ts in test_timestamps:
        day_mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
        is_daytime = df.loc[day_mask, 'is_daytime'].values
        day_indices.append(is_daytime)

    all_preds, all_true = [], []
    for pred, real, mask in zip(preds, true, day_indices):
        mask = mask[:96]  # 确保掩码长度一致
        all_preds.extend(pred[mask])
        all_true.extend(real[mask])

    rmse = np.sqrt(mean_squared_error(all_true, all_preds))
    mae = mean_absolute_error(all_true, all_preds)
    mape = np.mean(np.abs((np.array(all_true) - np.array(all_preds)) / (np.array(all_true) + 1e-5))) * 100

    print(f"白昼 RMSE: {rmse:.4f}  MAE: {mae:.4f}  MAPE: {mape:.2f}%")

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
    C = capacity_kW / 1000.0  # 转为 MW
    all_true, all_pred = [], []

    for i, ts in enumerate(timestamps):
        mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
        is_day = df.loc[mask, 'is_daytime'].values[:96]
        pred = pred_values[i][is_day]
        true = true_values[i][is_day]

        all_true.extend(true)
        all_pred.extend(pred)

    all_true = np.array(all_true)
    all_pred = np.array(all_pred)

    # 附件1公式指标计算
    err = (all_true - all_pred) / C
    abs_err = np.abs(err)

    E_rmse = np.sqrt(np.mean(err**2))
    E_mae = np.mean(abs_err)
    E_me = np.mean(err)
    r = np.corrcoef(all_true, all_pred)[0, 1]
    C_R = (1 - E_rmse) * 100
    Q_R = np.mean(abs_err < 0.25) * 100

    print(f"【附件1考核指标】基于装机容量 {C:.2f} MW")
    print(f"E_rmse: {E_rmse:.4f}")
    print(f"E_mae : {E_mae:.4f}")
    print(f"E_me  : {E_me:.4f}")
    print(f"r     : {r:.4f}")
    print(f"C_R   : {C_R:.2f}%")
    print(f"Q_R   : {Q_R:.2f}%")

    return {
        'E_rmse': E_rmse,
        'E_mae': E_mae,
        'E_me': E_me,
        'r': r,
        'C_R': C_R,
        'Q_R': Q_R
    }
# ----------------------- 使用示例 -----------------------
# 训练模型
# model = FusionModel(input_len=96)
# model, max_power = train_model(model, train_X, train_Y)
#
# # 评估测试集
# preds, rmse, mae, mape = evaluate_model(model, test_X, test_Y, test_timestamps, df, max_power)

import pandas as pd

def export_prediction_table(preds, test_Y, test_timestamps, df, method_name='融合模型预测', output_file='prediction_table.csv'):
    """
    将模型预测结果展开为标准提交表格格式
    :param preds: 模型预测值 (N, 96)
    :param test_Y: 实际值 (N, 96)
    :param test_timestamps: 起报时间列表（应为目标日 00:00:00）
    :param df: 原始 DataFrame，含真实功率
    :param method_name: 列标题中方法名
    :param output_file: 保存文件路径
    """
    records = []
    df = df.copy()
    df['date_time'] = pd.to_datetime(df['date_time'])

    for i, ts in enumerate(test_timestamps):
        start_time = pd.to_datetime(ts)
        for j in range(96):
            forecast_time = start_time + pd.Timedelta(days=1) + pd.Timedelta(minutes=15 * j)

            # 查找实际功率
            real_val_row = df[df['date_time'] == forecast_time]
            if not real_val_row.empty:
                actual_power = real_val_row['power'].values[0]
            else:
                actual_power = np.nan  # 若没有记录，用 nan 占位

            records.append({
                "起报时间": start_time.replace(hour=0, minute=0, second=0),
                "预报时间": forecast_time,
                "实际功率 (MW)": actual_power,
                f"{method_name} (MW)": preds[i, j]
            })

    df_pred = pd.DataFrame(records)
    target = ARTIFACTS.write_csv("predictions", output_file, df_pred, index=False)
    print(f"预测结果已保存至 {target}")
    return target


# 使用方法
# 计算所有指标
# export_prediction_table(preds, test_Y, test_timestamps, df, method_name='问题2融合模型预测')


# metrics = compute_all_metrics(test_Y, preds, test_timestamps, df, capacity_kW=6600)

import matplotlib.pyplot as plt
import seaborn as sns

def visualize_predictions(preds, test_Y, test_timestamps, df, model_name="model"):
    model_slug = slugify_checkpoint_name(model_name)
    # 设置全局绘图风格
    # plt.style.use('seaborn-whitegrid')  # 删除这一行或注释掉
    sns.set_theme(style='whitegrid')  # seaborn本身即可设定风格

    sns.set_context("notebook", font_scale=1.1)
    # 原代码开头添加字体配置
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号问题

    # ---------- 1. 可视化第一个样本的白昼时段功率曲线 ----------
    sample_index = 0
    ts = test_timestamps[sample_index]
    mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
    is_daytime = df.loc[mask, 'is_daytime'].values[:96]
    time_axis = df.loc[mask, 'date_time'].values[:96][is_daytime]

    sample_pred = preds[sample_index][is_daytime]
    sample_true = test_Y[sample_index][is_daytime]

    plt.figure(figsize=(12, 5))
    plt.plot(time_axis, sample_true, label='真实功率', linewidth=2, color='royalblue')
    plt.plot(time_axis, sample_pred, label='预测功率', linewidth=2, linestyle='--', color='darkorange')
    plt.fill_between(time_axis, sample_true, sample_pred, color='gray', alpha=0.3, label='误差区域')
    plt.title(f'白昼时段预测曲线（起报时间：{ts}）')
    plt.xlabel('时间')
    plt.ylabel('功率 (MW)')
    plt.legend()
    plt.tight_layout()
    plt.grid(True)
    ARTIFACTS.save_figure(f"{model_slug}_daylight_forecast_curve.png", show=SHOW_PLOTS)

    # ---------- 2. 所有白昼误差分布图 ----------
    all_true, all_pred = [], []
    for i, ts in enumerate(test_timestamps):
        mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
        is_daytime = df.loc[mask, 'is_daytime'].values[:96]
        all_true.extend(test_Y[i][is_daytime])
        all_pred.extend(preds[i][is_daytime])
    errors = np.array(all_pred) - np.array(all_true)

    plt.figure(figsize=(10, 4))
    sns.histplot(errors, kde=True, bins=50, color='teal')
    plt.axvline(x=0, color='red', linestyle='--')
    plt.title('预测误差分布（白昼时段）')
    plt.xlabel('误差 (预测 - 实际) (MW)')
    plt.ylabel('频数')
    plt.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_error_distribution.png", show=SHOW_PLOTS)

    # ---------- 3. 散点图：预测值 vs 实际值 ----------
    plt.figure(figsize=(6, 6))
    sns.scatterplot(x=all_true, y=all_pred, alpha=0.5, edgecolor=None)
    max_val = max(max(all_true), max(all_pred))
    plt.plot([0, max_val], [0, max_val], linestyle='--', color='red', label='理想预测线')
    plt.xlabel('实际功率 (MW)')
    plt.ylabel('预测功率 (MW)')
    plt.title('预测 vs 实际（白昼）')
    plt.legend()
    plt.tight_layout()
    plt.grid(True)
    ARTIFACTS.save_figure(f"{model_slug}_actual_vs_predicted_scatter.png", show=SHOW_PLOTS)


def plot_professional_forecast(preds, test_Y, test_timestamps, df, sample_index=0, model_name="model"):
    """专业级预测曲线可视化"""
    plt.figure(figsize=(14, 6))

    # 数据准备
    ts = test_timestamps[sample_index]
    mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
    is_daytime = df.loc[mask, 'is_daytime'].values[:96]
    time_axis = pd.to_datetime(df.loc[mask, 'date_time'].values[:96][is_daytime])

    sample_true = test_Y[sample_index][is_daytime]
    sample_pred = preds[sample_index][is_daytime]
    time_str = pd.to_datetime(ts).strftime("%Y-%m-%d")

    # 动态时间轴格式化
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))

    # 增强可视化元素
    plt.plot(time_axis, sample_true, label='实际功率',
             color='#2c7bb6', lw=2, marker='o', markersize=6, zorder=3)
    plt.plot(time_axis, sample_pred, label='预测功率',
             color='#d7191c', lw=2, linestyle='--', zorder=2)

    # 误差带填充
    plt.fill_between(time_axis, sample_pred, sample_true,
                     where=sample_pred > sample_true,
                     facecolor='#fdae61', alpha=0.3, label='正向误差')
    plt.fill_between(time_axis, sample_pred, sample_true,
                     where=sample_pred <= sample_true,
                     facecolor='#abdda4', alpha=0.3, label='负向误差')

    # 统计标注
    rmse = np.sqrt(mean_squared_error(sample_true, sample_pred))
    mae = mean_absolute_error(sample_true, sample_pred)
    plt.text(0.02, 0.95, f'RMSE: {rmse:.2f} MW\nMAE: {mae:.2f} MW',
             transform=ax.transAxes, fontsize=12,
             bbox=dict(facecolor='white', alpha=0.8))

    # 图例与装饰
    plt.title(f'专业预测可视化 - {time_str}', pad=20)
    plt.xlabel('时间 (15分钟间隔)')
    plt.ylabel('功率 (MW)')
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3)
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_figure(
        f"{model_slug}_professional_forecast_sample{sample_index}.png",
        show=SHOW_PLOTS,
    )


def plot_error_analysis(preds, test_Y, model_name="model"):
    """多维误差分析矩阵"""
    errors = preds - test_Y
    errors_flat = errors.flatten()

    fig = plt.figure(figsize=(16, 12), constrained_layout=True)
    gs = fig.add_gridspec(3, 2)

    # 误差分布
    ax1 = fig.add_subplot(gs[0, 0])
    sns.histplot(x=errors_flat, kde=True, ax=ax1, bins=30,
                 color='#2c7bb6', edgecolor='white')
    ax1.axvline(np.mean(errors_flat), color='red', linestyle='--')
    ax1.set_title("误差分布分析", fontsize=14, pad=15)

    # 误差热力图
    ax2 = fig.add_subplot(gs[0, 1])
    sns.heatmap(errors[:28], cmap="coolwarm", center=0,
                ax=ax2, cbar_kws={'label': '误差 (MW)'})
    ax2.set_title("误差时间分布模式 (前28个样本)", fontsize=14)

    # Q-Q图
    ax3 = fig.add_subplot(gs[1, 0])
    stats.probplot(errors_flat, dist="norm", plot=ax3)
    ax3.get_lines()[0].set_markerfacecolor('#2c7bb6')
    ax3.title.set_text('正态性检验 Q-Q 图')

    # 残差分析
    ax4 = fig.add_subplot(gs[1, 1])
    sns.residplot(x=test_Y.flatten(), y=preds.flatten(),
                  lowess=True, color='#2c7bb6',
                  line_kws={'color': 'red'}, ax=ax4)
    ax4.set_title("残差分析图", fontsize=14)

    # 综合统计
    plt.suptitle("多维误差分析报告", y=1.02, fontsize=16)
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
        "BiFusionModel": BiFusionModel(input_len=96), # 你需要预先定义这个模型结构
        "PureLSTM": PureLSTM(input_len=96),
        "FusionModel": FusionModel(input_len=96),
        # "BiFusionModel": BiFusionModel(input_len=96)  # 你需要预先定义这个模型结构
    }

    predictions = {}
    metrics_all = {}

    for name, model in model_dict.items():
        print(f"\n===== 正在训练模型：{name} =====")
        use_mv = True  # True：问题3，False：问题2
        X_train, X_test = get_inputs(use_mv)

        model, max_power = train_model(model, X_train, train_Y, checkpoint_name=f"problem3_{name}")
        preds, rmse, mae, mape = evaluate_model(model, X_test, test_Y, test_timestamps, df, max_power)

        metrics = compute_all_metrics(test_Y, preds, test_timestamps, df)
        predictions[name] = preds
        metrics_all[name] = metrics

        # 每个模型分别导出预测表格
        export_prediction_table(preds, test_Y, test_timestamps, df, method_name=f"{name}预测功率", output_file=f"3prediction_{name}.csv")

        # 每个模型分别可视化
        print(f"\n>> 可视化：{name}")
        visualize_predictions(preds, test_Y, test_timestamps, df, model_name=name)
        plot_professional_forecast(preds, test_Y, test_timestamps, df, model_name=name)
        plot_error_analysis(preds, test_Y, model_name=name)

    # ======= 指标对比表格 =======
    df_metrics = pd.DataFrame(metrics_all).T
    print("\n3三模型评估指标对比：")
    print(df_metrics.round(4))
    ARTIFACTS.write_csv("metrics", "三模型白昼指标对比.csv", df_metrics, index=True)

    # 可视化热图
    plt.figure(figsize=(10, 6))
    sns.heatmap(df_metrics, annot=True, fmt=".3f", cmap="YlGnBu")
    plt.title("三模型评估指标热力图 (白昼时段)")
    plt.tight_layout()
    ARTIFACTS.save_figure("三模型评估指标热力图_白昼时段.png", show=SHOW_PLOTS)

    # ======= 三模型每日对比图 (默认 index = 0) =======
    day_idx = 0
    ts = test_timestamps[day_idx]
    plt.figure(figsize=(12, 6))
    for name in predictions:
        pred = predictions[name][day_idx]
        mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
        is_daytime = df.loc[mask, 'is_daytime'].values[:96]
        time_axis = df.loc[mask, 'date_time'].values[:96][is_daytime]
        plt.plot(time_axis, pred[is_daytime], label=f"{name}预测")

    # 添加真实值
    true = test_Y[day_idx]
    plt.plot(time_axis, true[is_daytime], label="真实功率", linestyle='--', linewidth=2, color='black')
    # plt.title(f"每日预测对比图（白昼） | 起报时间：{ts.date()}")
    plt.title(f"每日预测对比图（白昼） | 起报时间：{pd.to_datetime(ts).date()}")

    plt.xlabel("时间")
    plt.ylabel("功率 (MW)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    ARTIFACTS.save_figure("三模型每日预测对比图_白昼.png", show=SHOW_PLOTS)

    # ======= 统一输出预测对比表格 =======
    records = []
    for i, ts in enumerate(test_timestamps):
        start_time = pd.to_datetime(ts)
        for j in range(96):
            forecast_time = start_time + pd.Timedelta(days=1) + pd.Timedelta(minutes=15 * j)
            real_val_row = df[df['date_time'] == forecast_time]
            actual_power = real_val_row['power'].values[0] if not real_val_row.empty else np.nan

            row = {
                "起报时间": start_time.replace(hour=0, minute=0, second=0),
                "预报时间": forecast_time,
                "实际功率": actual_power
            }
            for name in predictions:
                row[f"{name}预测功率"] = predictions[name][i, j]
            records.append(row)

    df_all_preds = pd.DataFrame(records)
    all_preds_path = ARTIFACTS.write_csv("predictions", "3三模型预测结果对比表.csv", df_all_preds, index=False)
    print(f"\n已保存统一预测对比表格为：{all_preds_path}")

# 结束计时
end_time = time.time()
elapsed_time = end_time - start_time

print(f"代码执行时间: {elapsed_time:.4f} 秒")
ARTIFACTS.write_summary(
    {
        "problem": "problem3_scenario_analysis",
        "models": list(model_dict.keys()) if "model_dict" in globals() else [],
        "train_samples": len(train_X),
        "test_samples": len(test_X),
        "elapsed_seconds": elapsed_time,
    }
)
