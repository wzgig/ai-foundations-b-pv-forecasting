# -*- coding: utf-8 -*-
"""
Created on 2025/5/24 15:54

@author: Prince
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import odeint  # 使用odeint替代ode45
from sklearn.preprocessing import MinMaxScaler
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'  # 或者其他中文字体，如 'Microsoft YaHei'
rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
df = pd.read_csv("station00.csv")
df['date_time'] = pd.to_datetime(df['date_time'])

# 添加日期信息
df['month'] = df['date_time'].dt.month
df['day'] = df['date_time'].dt.day
df['date'] = df['date_time'].dt.date

# 指定测试集：2、5、8、11 月最后 7 天
unique_dates = df['date'].drop_duplicates().reset_index(drop=True)
test_months = [2, 5, 8, 11]
test_dates = []
for m in test_months:
    month_dates = unique_dates[unique_dates.map(lambda d: d.month) == m]
    if len(month_dates) >= 7:
        test_dates.extend(month_dates[-7:].tolist())

df['set'] = df['date'].apply(lambda d: 'test' if d in test_dates else 'train')
df['is_daytime'] = df['power'] > 0.05

# 构造滑动窗口样本
input_length, forecast_length = 96, 96
values = df['power'].values
date_times = df['date_time'].values
set_flags = df['set'].values

train_X, train_Y, train_timestamps = [], [], []

for i in range(len(df) - input_length - forecast_length):
    if set_flags[i] == 'train' and set_flags[i + input_length + forecast_length - 1] == 'train':
        train_X.append(values[i: i + input_length])
        train_Y.append(values[i + input_length: i + input_length + forecast_length])
        train_timestamps.append(date_times[i + input_length])

train_X = np.array(train_X)
train_Y = np.array(train_Y)

# 替代错误的 test_X/Y 构造逻辑 —— 使用每日严格样本（共28天）
import datetime

# 标注白昼和日期
df['is_daytime'] = df['power'] > 0.05
df['date'] = df['date_time'].dt.date
df['month'] = df['date_time'].dt.month

# 仅第 2、5、8、11 月的最后 7 天为测试集
test_months = [2, 5, 8, 11]
unique_dates = df['date'].drop_duplicates().reset_index(drop=True)
target_test_days = []

for m in test_months:
    month_dates = unique_dates[unique_dates.map(lambda d: d.month) == m]
    target_test_days.extend(month_dates[-7:].tolist())

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
test_X = np.array(strict_test_X)
test_Y = np.array(strict_test_Y)
test_timestamps = np.array(strict_test_timestamps)
# 确保 test_X/Y 是 28 天的严格样本

import torch
import torch.nn as nn

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

import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader, TensorDataset


def train_model(model, train_X, train_Y, val_split=0.1, batch_size=64, epochs=50, lr=0.001, patience=5):
    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # 数据归一化
    max_power = train_X.max()
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

    # 创建保存模型的目录
    import os
    os.makedirs('models', exist_ok=True)
    model_path = f"models/{model.__class__.__name__}.pth"
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"已复用训练好的模型：{model_path}")
        return model, max_power

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
            torch.save(model.state_dict(), model_path)
            print(f"模型保存于 {model_path}")
        else:
            counter += 1
            if counter >= patience:
                print(f"早停触发，最佳验证损失: {best_loss:.4f}")
                break

    # 加载最佳模型
    model.load_state_dict(torch.load(model_path, map_location=device))
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
model = FusionModel(input_len=96)
model, max_power = train_model(model, train_X, train_Y)

# 评估测试集
preds, rmse, mae, mape = evaluate_model(model, test_X, test_Y, test_timestamps, df, max_power)

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
    df_pred.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"预测结果已保存至 {output_file}")


# 使用方法
# 计算所有指标
export_prediction_table(preds, test_Y, test_timestamps, df, method_name='问题2融合模型预测')


metrics = compute_all_metrics(test_Y, preds, test_timestamps, df, capacity_kW=6600)

import matplotlib.pyplot as plt
import seaborn as sns

def visualize_predictions(preds, test_Y, test_timestamps, df):
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
    plt.show()

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
    plt.show()

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
    plt.show()


# 3. 展示图形可视化
visualize_predictions(preds, test_Y, test_timestamps, df)


# import matplotlib.pyplot as plt
#
# # 可视化某个测试样本的真实值与预测值（第 0 个为例）
# sample_index = 0
# ts = test_timestamps[sample_index]
# pred = preds[sample_index]
# true = test_Y[sample_index]
#
# # 构建白昼掩码
# day_mask = (df['date_time'] >= ts) & (df['date_time'] < ts + pd.Timedelta(days=1))
# mask = df.loc[day_mask, 'is_daytime'].values[:96]
#
# # 提取白昼对应的时间戳
# time_axis = df.loc[day_mask, 'date_time'].values[:96][mask]
# sample_pred_day = pred[mask]
# sample_true_day = true[mask]
#
# # 绘图
# plt.figure(figsize=(12, 5))
# plt.plot(time_axis, sample_true_day, label='真实功率', color='blue')
# plt.plot(time_axis, sample_pred_day, label='预测功率', color='orange', linestyle='--')
# plt.title(f'预测 vs 实际（白昼） | 起报时间：{ts}')
# plt.xlabel('时间')
# plt.ylabel('功率 (MW)')
# plt.legend()
# plt.grid(True)
# plt.tight_layout()
# plt.show()
