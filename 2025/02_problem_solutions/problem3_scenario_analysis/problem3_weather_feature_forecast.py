# -*- coding: utf-8 -*-
"""
Problem 3: weather-enhanced day-ahead PV forecasting.

The model input combines the previous day's measured power profile with the
target day's NWP weather sequence.  This keeps the forecasting setup day-ahead:
target-day power is never used as an input, while target-day weather forecasts
are available to the model.
"""
from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path


def add_local_msvc_runtime_dirs() -> None:
    """Prefer package-bundled MSVC runtimes when the system runtime is stale."""

    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return
    for relative in [
        ("Lib", "site-packages", "sklearn", ".libs"),
        ("Lib", "site-packages", "numpy.libs"),
        ("Lib", "site-packages", "pandas.libs"),
        ("Lib", "site-packages", "scipy.libs"),
        ("Lib", "site-packages", "torch", "lib"),
    ]:
        candidate = Path(sys.prefix).joinpath(*relative)
        if candidate.exists():
            os.add_dll_directory(str(candidate))


add_local_msvc_runtime_dirs()

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared"
    for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
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

BATCH_SIZE = int(os.getenv("PV_FORECAST_BATCH_SIZE", "128"))
TRAINING_EPOCHS = int(os.getenv("PV_FORECAST_EPOCHS", "20"))
TRAINING_PATIENCE = int(os.getenv("PV_FORECAST_PATIENCE", "4"))
LEARNING_RATE = float(os.getenv("PV_FORECAST_LR", "0.001"))
FORCE_RETRAIN = os.getenv("PV_FORCE_RETRAIN", "0").strip().lower() in {"1", "true", "yes"}
HIDDEN_DIM = int(os.getenv("PV_FORECAST_HIDDEN_DIM", "32"))

WEATHER_FEATURES = [
    "nwp_globalirrad",
    "nwp_directirrad",
    "nwp_temperature",
    "nwp_humidity",
    "nwp_windspeed",
    "nwp_pressure",
    "wind_x",
    "wind_y",
]
RAW_SCALE_FEATURES = ["power", *WEATHER_FEATURES]
MODEL_INPUT_LABELS = ["前一日功率", *WEATHER_FEATURES]
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


def load_station_data() -> tuple[pd.DataFrame, list[datetime.date], list[str], list[str]]:
    df = pd.read_csv(resolve_input("station00.csv", __file__))
    df["date_time"] = pd.to_datetime(df["date_time"])
    df["month"] = df["date_time"].dt.month
    df["day"] = df["date_time"].dt.day
    df["date"] = df["date_time"].dt.date

    test_dates = make_tail_test_dates(
        df,
        date_col="date_time",
        months=TEST_MONTHS,
        tail_days=TEST_TAIL_DAYS,
    )
    if not test_dates:
        raise ValueError("未找到可用于问题3测试集的目标日期，请检查 station00.csv 的时间范围。")

    df["set"] = df["date"].apply(lambda d: "test" if d in test_dates else "train")
    df["is_daytime"] = df["power"] > DAYLIGHT_POWER_THRESHOLD

    # Wind direction is circular; split it into two continuous components.
    df["wind_x"] = np.cos(np.radians(df["nwp_winddirection"]))
    df["wind_y"] = np.sin(np.radians(df["nwp_winddirection"]))

    df, _, scaled_columns = minmax_scale_train_only(df, RAW_SCALE_FEATURES)
    weather_scaled = [f"{feature}_scaled" for feature in WEATHER_FEATURES]
    return df, test_dates, scaled_columns, weather_scaled


df, target_test_days, scaled_features, weather_scaled_features = load_station_data()


def build_feature_window(prev_rows: pd.DataFrame, target_rows: pd.DataFrame) -> np.ndarray:
    """Combine previous-day power with target-day weather features."""

    previous_power = prev_rows[["power_scaled"]].to_numpy(dtype=np.float32)
    target_weather = target_rows[weather_scaled_features].to_numpy(dtype=np.float32)
    return np.concatenate([previous_power, target_weather], axis=1)


def construct_weather_enhanced_samples(
    source_df: pd.DataFrame,
    input_len: int = INPUT_LENGTH,
    forecast_len: int = FORECAST_LENGTH,
) -> tuple[np.ndarray, np.ndarray]:
    train_X, train_Y = [], []

    for start in range(len(source_df) - input_len - forecast_len + 1):
        prev_rows = source_df.iloc[start : start + input_len]
        target_rows = source_df.iloc[start + input_len : start + input_len + forecast_len]
        if (prev_rows["set"] == "train").all() and (target_rows["set"] == "train").all():
            train_X.append(build_feature_window(prev_rows, target_rows))
            train_Y.append(target_rows["power"].to_numpy(dtype=np.float32))

    if not train_X:
        raise ValueError("问题3训练样本为空，请检查训练/测试日期划分。")
    return np.asarray(train_X, dtype=np.float32), np.asarray(train_Y, dtype=np.float32)


def construct_strict_test_samples(
    source_df: pd.DataFrame,
    test_days: list[datetime.date],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    test_X, test_Y, test_timestamps = [], [], []

    for test_day in test_days:
        prev_day = test_day - datetime.timedelta(days=1)
        prev_rows = source_df[source_df["date"] == prev_day]
        target_rows = source_df[source_df["date"] == test_day]
        if len(prev_rows) == INPUT_LENGTH and len(target_rows) == FORECAST_LENGTH:
            test_X.append(build_feature_window(prev_rows, target_rows))
            test_Y.append(target_rows["power"].to_numpy(dtype=np.float32))
            test_timestamps.append(pd.Timestamp(test_day))

    if not test_X:
        raise ValueError("问题3测试样本为空，请检查测试日前一日和目标日是否均具备完整 96 点。")
    return (
        np.asarray(test_X, dtype=np.float32),
        np.asarray(test_Y, dtype=np.float32),
        np.asarray(test_timestamps),
    )


train_X, train_Y = construct_weather_enhanced_samples(df)
test_X, test_Y, test_timestamps = construct_strict_test_samples(df, target_test_days)
INPUT_DIM = train_X.shape[-1]


class LSTMBranch(nn.Module):
    def __init__(self, input_len: int, input_dim: int, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class TCNBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3, dilation: int = 1):
        super().__init__()
        self.conv = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size,
            padding=(kernel_size - 1) * dilation // 2,
            dilation=dilation,
        )
        self.bn = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class TCNBranch(nn.Module):
    def __init__(self, input_len: int, input_dim: int, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.net = nn.Sequential(
            TCNBlock(input_dim, hidden_dim, dilation=1),
            TCNBlock(hidden_dim, hidden_dim, dilation=2),
            TCNBlock(hidden_dim, hidden_dim, dilation=4),
        )
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.net(x)
        return self.fc(x.mean(dim=2))


class MLPBranch(nn.Module):
    def __init__(self, input_len: int, input_dim: int, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(input_len * input_dim, hidden_dim * 4),
            nn.ReLU(),
            nn.Linear(hidden_dim * 4, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, input_len),
        )

    def forward(self, x):
        return self.fc(x)


class FusionModel(nn.Module):
    def __init__(self, input_len: int = INPUT_LENGTH, input_dim: int = INPUT_DIM):
        super().__init__()
        self.lstm_branch = LSTMBranch(input_len, input_dim)
        self.tcn_branch = TCNBranch(input_len, input_dim)
        self.mlp_branch = MLPBranch(input_len, input_dim)
        self.attn = nn.Sequential(
            nn.Linear(3 * input_len, 96),
            nn.ReLU(),
            nn.Linear(96, 3),
            nn.Softmax(dim=1),
        )
        self.output_layer = nn.Linear(input_len, input_len)

    def forward(self, x):
        lstm_out = self.lstm_branch(x)
        tcn_out = self.tcn_branch(x)
        mlp_out = self.mlp_branch(x)
        weights = self.attn(torch.cat([lstm_out, tcn_out, mlp_out], dim=1))
        fused = (
            weights[:, 0:1] * lstm_out
            + weights[:, 1:2] * tcn_out
            + weights[:, 2:3] * mlp_out
        )
        return self.output_layer(fused)


class PureLSTM(nn.Module):
    def __init__(
        self,
        input_len: int = INPUT_LENGTH,
        input_dim: int = INPUT_DIM,
        hidden_dim: int = HIDDEN_DIM,
    ):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, input_len)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])


class TransformerBlock(nn.Module):
    def __init__(self, hidden_dim: int = HIDDEN_DIM, nhead: int = 4):
        super().__init__()
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=nhead,
            dim_feedforward=hidden_dim * 2,
            dropout=0.05,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=1)

    def forward(self, x):
        return self.transformer(x)


class BiFusionModel(nn.Module):
    def __init__(
        self,
        input_len: int = INPUT_LENGTH,
        input_dim: int = INPUT_DIM,
        hidden_dim: int = HIDDEN_DIM,
    ):
        super().__init__()
        self.bilstm = nn.LSTM(input_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.tcn = nn.Sequential(
            TCNBlock(input_dim, hidden_dim, dilation=1),
            TCNBlock(hidden_dim, hidden_dim, dilation=2),
        )
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.transformer = TransformerBlock(hidden_dim=hidden_dim)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim * 3),
            nn.ReLU(),
            nn.Linear(hidden_dim * 3, input_len),
        )

    def forward(self, x):
        bilstm_feat = self.bilstm(x)[0][:, -1, :]
        tcn_feat = self.tcn(x.transpose(1, 2)).mean(dim=2)
        trans_feat = self.transformer(self.input_proj(x)).mean(dim=1)
        feat = torch.cat([bilstm_feat, tcn_feat, trans_feat], dim=1)
        return self.fc(feat)


def train_model(
    model,
    train_X,
    train_Y,
    *,
    val_split: float = 0.1,
    batch_size: int = BATCH_SIZE,
    epochs: int = TRAINING_EPOCHS,
    lr: float = LEARNING_RATE,
    patience: int = TRAINING_PATIENCE,
    checkpoint_name: str | None = None,
    force_retrain: bool = FORCE_RETRAIN,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    target_scale = float(np.max(train_Y))
    if target_scale <= 0:
        raise ValueError("训练集功率最大值必须大于 0，无法归一化训练目标。")

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
        extra={
            "checkpoint_name": checkpoint_name,
            "architecture_version": "problem3_weather_target_nwp_v2",
            "input_dim": int(train_X.shape[-1]),
            "input_features": MODEL_INPUT_LABELS,
            "hidden_dim": HIDDEN_DIM,
            "target_scale": "train_Y_max",
        },
    )
    if not force_retrain:
        loaded, checkpoint_scale = try_load_torch_checkpoint(
            model,
            checkpoint_path,
            checkpoint_signature,
            torch_module=torch,
            device=device,
        )
        if loaded:
            print(f"已复用训练好的模型：{checkpoint_path}", flush=True)
            return model, float(checkpoint_scale or target_scale), True

    scaled_Y = train_Y / target_scale
    val_size = max(1, int(len(train_X) * val_split))
    indices = np.random.permutation(len(train_X))
    val_idx, train_idx = indices[:val_size], indices[val_size:]
    if len(train_idx) == 0:
        raise ValueError("训练集过小，无法划分验证集。")

    X_train = torch.tensor(train_X[train_idx], dtype=torch.float32)
    Y_train = torch.tensor(scaled_Y[train_idx], dtype=torch.float32)
    X_val = torch.tensor(train_X[val_idx], dtype=torch.float32)
    Y_val = torch.tensor(scaled_Y[val_idx], dtype=torch.float32)

    train_loader = DataLoader(TensorDataset(X_train, Y_train), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, Y_val), batch_size=batch_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    best_loss, counter = float("inf"), 0

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * xb.size(0)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_loss += criterion(model(xb), yb).item() * xb.size(0)

        train_loss = total_loss / len(train_loader.dataset)
        val_loss /= len(val_loader.dataset)
        print(f"Epoch {epoch + 1}: Train={train_loss:.4f}, Val={val_loss:.4f}", flush=True)

        if val_loss < best_loss:
            best_loss = val_loss
            counter = 0
            save_torch_checkpoint(
                model,
                checkpoint_path,
                checkpoint_signature,
                torch_module=torch,
                max_power=target_scale,
                best_val_loss=best_loss,
            )
            print(f"模型保存于 {checkpoint_path}", flush=True)
        else:
            counter += 1
            if counter >= patience:
                print(f"早停触发，最佳验证损失: {best_loss:.4f}", flush=True)
                break

    loaded, _ = try_load_torch_checkpoint(
        model,
        checkpoint_path,
        checkpoint_signature,
        torch_module=torch,
        device=device,
    )
    if not loaded:
        raise RuntimeError(f"未能加载最佳模型检查点：{checkpoint_path}")
    return model, target_scale, False


def daylight_arrays(true_values, pred_values, timestamps, source_df):
    all_true, all_pred = [], []
    for idx, ts in enumerate(pd.to_datetime(list(timestamps))):
        day_mask = (source_df["date_time"] >= ts) & (source_df["date_time"] < ts + pd.Timedelta(days=1))
        is_daytime = source_df.loc[day_mask, "is_daytime"].values[:FORECAST_LENGTH]
        if len(is_daytime) != FORECAST_LENGTH:
            raise ValueError(f"{ts.date()} 的测试日数据不足 {FORECAST_LENGTH} 点。")
        all_true.extend(np.asarray(true_values[idx])[is_daytime])
        all_pred.extend(np.asarray(pred_values[idx])[is_daytime])

    if not all_true:
        raise ValueError("白昼样本为空，无法计算问题3评价指标。")
    return np.asarray(all_true, dtype=float), np.asarray(all_pred, dtype=float)


def evaluate_model(model, test_X, test_Y, test_timestamps, source_df, target_scale):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    X_tensor = torch.tensor(test_X, dtype=torch.float32).to(device)
    with torch.no_grad():
        preds = model(X_tensor).cpu().numpy() * target_scale
    preds = np.clip(preds, 0.0, target_scale)

    all_true, all_pred = daylight_arrays(test_Y, preds, test_timestamps, source_df)
    rmse = float(np.sqrt(mean_squared_error(all_true, all_pred)))
    mae = float(mean_absolute_error(all_true, all_pred))
    mape = float(np.mean(np.abs((all_true - all_pred) / (all_true + 1e-5))) * 100)
    print(f"白昼 RMSE: {rmse:.4f}  MAE: {mae:.4f}  MAPE: {mape:.2f}%", flush=True)
    return preds, rmse, mae, mape


def compute_all_metrics(true_values, pred_values, timestamps, source_df, capacity_kW=CAPACITY_KW):
    metrics = daylight_metrics(
        true_values,
        pred_values,
        timestamps,
        source_df,
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
    target_start = pd.to_datetime(ts)
    mask = (source_df["date_time"] >= target_start) & (
        source_df["date_time"] < target_start + pd.Timedelta(days=1)
    )
    is_daytime = source_df.loc[mask, "is_daytime"].values[:FORECAST_LENGTH]
    if len(is_daytime) != FORECAST_LENGTH:
        raise ValueError(f"{target_start.date()} 的目标日数据不足 {FORECAST_LENGTH} 点。")
    return is_daytime


def intraday_hour_axis(length=FORECAST_LENGTH):
    return np.arange(length, dtype=float) * 24.0 / length


def format_intraday_axis(ax):
    ax.set_xlim(0, 24)
    ticks = np.arange(0, 25, 3)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(hour):02d}:00" for hour in ticks])


def export_prediction_table(
    preds,
    test_Y,
    test_timestamps,
    method_name="融合模型预测",
    output_file="prediction_table.csv",
):
    records = []
    for idx, ts in enumerate(test_timestamps):
        target_start = pd.to_datetime(ts).replace(hour=0, minute=0, second=0)
        issue_time = target_start - pd.Timedelta(days=1)
        for step in range(FORECAST_LENGTH):
            forecast_time = target_start + pd.Timedelta(minutes=15 * step)
            records.append(
                {
                    "起报时间": issue_time,
                    "预报时间": forecast_time,
                    "实际功率 (MW)": float(test_Y[idx, step]),
                    f"{method_name} (MW)": float(preds[idx, step]),
                }
            )

    df_pred = pd.DataFrame(records)
    target = ARTIFACTS.write_csv("predictions", output_file, df_pred, index=False)
    print(f"预测结果已保存至 {target}", flush=True)
    return target


def visualize_predictions(preds, test_Y, test_timestamps, source_df, model_name="model"):
    model_slug = slugify_checkpoint_name(model_name)
    sample_index = 0
    ts = test_timestamps[sample_index]
    is_daytime = target_day_daylight_mask(ts, source_df)
    time_axis = intraday_hour_axis()
    sample_pred = preds[sample_index]
    sample_true = test_Y[sample_index]
    daylight_rmse = np.sqrt(mean_squared_error(sample_true[is_daytime], sample_pred[is_daytime]))

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.plot(time_axis, sample_true, label="实测功率", color=PALETTE[0], linewidth=2.1)
    ax.plot(time_axis, sample_pred, label="预测功率", color=PALETTE[1], linewidth=2.0, linestyle="--")
    ax.fill_between(time_axis, sample_true, sample_pred, color="#8c8c8c", alpha=0.18, label="绝对误差")
    ax.text(
        0.02,
        0.95,
        f"白昼RMSE={daylight_rmse:.2f} MW",
        transform=ax.transAxes,
        va="top",
        fontsize=9.5,
        bbox=dict(facecolor="white", edgecolor="#bdbdbd", linewidth=0.6, alpha=0.9),
    )
    ax.set_title(f"{MODEL_LABELS.get(model_name, model_name)} 目标日预测曲线（{pd.Timestamp(ts).date()}）")
    ax.set_xlabel("日内时刻")
    ax.set_ylabel("功率/MW")
    format_intraday_axis(ax)
    ax.legend(loc="upper left", ncol=3)
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_forecast_curve.png", fig=fig, show=SHOW_PLOTS)

    all_true, all_pred = daylight_arrays(test_Y, preds, test_timestamps, source_df)
    errors = all_pred - all_true
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    sns.histplot(errors, kde=True, bins=42, color=PALETTE[2], edgecolor="white", linewidth=0.4, ax=ax)
    ax.axvline(x=0, color=PALETTE[3], linestyle="--", linewidth=1.5, label="零误差")
    ax.axvline(x=np.mean(errors), color=PALETTE[1], linestyle="-", linewidth=1.5, label="均值")
    ax.set_title(f"{MODEL_LABELS.get(model_name, model_name)} 白昼预测误差分布")
    ax.set_xlabel("预测误差/MW")
    ax.set_ylabel("频数")
    ax.legend(loc="upper right")
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_error_distribution.png", fig=fig, show=SHOW_PLOTS)

    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    sns.scatterplot(x=all_true, y=all_pred, alpha=0.42, s=24, edgecolor=None, color=PALETTE[0], ax=ax)
    max_val = max(float(np.max(all_true)), float(np.max(all_pred)))
    ax.plot([0, max_val], [0, max_val], linestyle="--", color=PALETTE[3], label="理想预测线")
    ax.set_xlabel("实测功率/MW")
    ax.set_ylabel("预测功率/MW")
    ax.set_title(f"{MODEL_LABELS.get(model_name, model_name)} 白昼预测一致性")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left")
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_actual_vs_predicted_scatter.png", fig=fig, show=SHOW_PLOTS)


def plot_professional_forecast(preds, test_Y, test_timestamps, source_df, sample_index=0, model_name="model"):
    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    ts = test_timestamps[sample_index]
    is_daytime = target_day_daylight_mask(ts, source_df)
    time_axis = intraday_hour_axis()
    sample_true = test_Y[sample_index]
    sample_pred = preds[sample_index]
    time_str = pd.Timestamp(ts).strftime("%Y-%m-%d")

    ax.plot(time_axis, sample_true, label="实测功率", color=PALETTE[0], lw=2, marker="o", markersize=3.5, zorder=3)
    ax.plot(time_axis, sample_pred, label="预测功率", color=PALETTE[1], lw=2, linestyle="--", zorder=2)
    ax.fill_between(time_axis, sample_pred, sample_true, where=sample_pred > sample_true, facecolor=PALETTE[4], alpha=0.24, label="高估区间")
    ax.fill_between(time_axis, sample_pred, sample_true, where=sample_pred <= sample_true, facecolor=PALETTE[2], alpha=0.20, label="低估区间")

    rmse = np.sqrt(mean_squared_error(sample_true[is_daytime], sample_pred[is_daytime]))
    mae = mean_absolute_error(sample_true[is_daytime], sample_pred[is_daytime])
    ax.text(
        0.02,
        0.95,
        f"RMSE={rmse:.2f} MW\nMAE={mae:.2f} MW",
        transform=ax.transAxes,
        fontsize=9.5,
        va="top",
        bbox=dict(facecolor="white", edgecolor="#bdbdbd", linewidth=0.6, alpha=0.9),
    )

    ax.set_title(f"{MODEL_LABELS.get(model_name, model_name)} 单日预测细节（目标日：{time_str}）")
    ax.set_xlabel("日内时刻")
    ax.set_ylabel("功率/MW")
    format_intraday_axis(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4)
    apply_journal_axes(ax)
    fig.tight_layout()
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_figure(f"{model_slug}_professional_forecast_sample{sample_index}.png", fig=fig, show=SHOW_PLOTS)


def plot_error_analysis(preds, test_Y, test_timestamps, source_df, model_name="model"):
    errors = preds - test_Y
    daylight_true, daylight_pred = daylight_arrays(test_Y, preds, test_timestamps, source_df)
    errors_flat = daylight_pred - daylight_true
    heatmap_errors = errors.copy()
    for idx, ts in enumerate(test_timestamps):
        is_daytime = target_day_daylight_mask(ts, source_df)
        heatmap_errors[idx, ~is_daytime] = np.nan

    fig = plt.figure(figsize=(10.8, 8.2), constrained_layout=True)
    gs = fig.add_gridspec(3, 2)

    ax1 = fig.add_subplot(gs[0, 0])
    sns.histplot(x=errors_flat, kde=True, ax=ax1, bins=36, color=PALETTE[0], edgecolor="white", linewidth=0.4)
    ax1.axvline(np.mean(errors_flat), color=PALETTE[3], linestyle="--", linewidth=1.4)
    ax1.set_title("白昼误差分布")
    ax1.set_xlabel("预测误差/MW")
    ax1.set_ylabel("频数")

    ax2 = fig.add_subplot(gs[0, 1])
    sns.heatmap(heatmap_errors, cmap="RdBu_r", center=0, ax=ax2, cbar_kws={"label": "误差/MW"}, xticklabels=12, yticklabels=4)
    ax2.set_title("测试日白昼误差热力图")
    ax2.set_xlabel("日内 15 min 序号")
    ax2.set_ylabel("测试日序号")

    ax3 = fig.add_subplot(gs[1, 0])
    stats.probplot(errors_flat, dist="norm", plot=ax3)
    ax3.get_lines()[0].set_markerfacecolor(PALETTE[0])
    ax3.get_lines()[0].set_markeredgecolor(PALETTE[0])
    ax3.get_lines()[1].set_color(PALETTE[3])
    ax3.title.set_text("误差正态性 Q-Q 图")

    ax4 = fig.add_subplot(gs[1, 1])
    sns.residplot(
        x=daylight_true,
        y=daylight_pred,
        lowess=True,
        color=PALETTE[0],
        scatter_kws={"alpha": 0.35, "s": 20},
        line_kws={"color": PALETTE[3], "linewidth": 1.6},
        ax=ax4,
    )
    ax4.set_title("白昼残差趋势")
    ax4.set_xlabel("实测功率/MW")
    ax4.set_ylabel("残差/MW")

    ax5 = fig.add_subplot(gs[2, :])
    daytime_error_frame = pd.DataFrame(heatmap_errors).melt(var_name="step", value_name="error").dropna()
    sns.lineplot(data=daytime_error_frame, x="step", y="error", estimator="mean", errorbar=("ci", 95), color=PALETTE[1], ax=ax5)
    ax5.axhline(0, color=PALETTE[3], linestyle="--", linewidth=1.2)
    ax5.set_title("白昼平均误差日内变化")
    ax5.set_xlabel("日内 15 min 序号")
    ax5.set_ylabel("平均误差/MW")

    fig.suptitle(f"{MODEL_LABELS.get(model_name, model_name)} 多维误差诊断", fontsize=13)
    apply_journal_figure(fig)
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_figure(f"{model_slug}_error_analysis_matrix.png", fig=fig, show=SHOW_PLOTS)


def interactive_forecast_plot(preds, test_Y, test_timestamps, sample_index=0, model_name="model"):
    ts = pd.Timestamp(test_timestamps[sample_index])
    time_points = [ts + pd.Timedelta(minutes=15 * step) for step in range(FORECAST_LENGTH)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_points, y=test_Y[sample_index], name="实测功率", line=dict(color=PALETTE[0], width=3)))
    fig.add_trace(go.Scatter(x=time_points, y=preds[sample_index], name="预测功率", line=dict(color=PALETTE[1], width=3, dash="dot")))
    fig.update_layout(
        title=f"交互式预测可视化 - {ts.strftime('%Y-%m-%d')}",
        xaxis_title="时间",
        yaxis_title="功率/MW",
        hovermode="x unified",
        template="plotly_white",
        height=500,
        margin=dict(l=50, r=50, b=80, t=80),
    )
    model_slug = slugify_checkpoint_name(model_name)
    ARTIFACTS.save_plotly_html(f"{model_slug}_interactive_forecast_sample{sample_index}.html", fig)


def plot_metric_heatmap(df_metrics: pd.DataFrame):
    score_metrics = df_metrics.copy()
    score_metrics["E_me"] = score_metrics["E_me"].abs()
    normalized_metrics = pd.DataFrame(index=df_metrics.index)
    for column in df_metrics.columns:
        source = score_metrics[column]
        denominator = source.max() - source.min()
        if denominator == 0:
            normalized_metrics[column] = 0.5
        elif column in {"E_rmse", "E_mae", "E_me"}:
            normalized_metrics[column] = 1 - (source - source.min()) / denominator
        else:
            normalized_metrics[column] = (source - source.min()) / denominator

    annot_metrics = df_metrics.rename(columns=METRIC_LABELS).round(3).astype(str)

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    sns.heatmap(
        normalized_metrics.rename(columns=METRIC_LABELS),
        annot=annot_metrics,
        fmt="",
        cmap="YlGnBu",
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": "列内表现得分"},
        ax=ax,
    )
    ax.set_title("问题3三模型白昼评价指标对比")
    ax.set_xlabel("评价指标")
    ax.set_ylabel("模型")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=28, ha="right")
    apply_journal_axes(ax, grid=False)
    fig.tight_layout()
    ARTIFACTS.save_figure("三模型评估指标热力图_白昼时段.png", fig=fig, show=SHOW_PLOTS)


def plot_three_model_day(predictions: dict[str, np.ndarray]):
    day_idx = 0
    ts = test_timestamps[day_idx]
    is_daytime = target_day_daylight_mask(ts, df)
    time_axis = intraday_hour_axis()

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    for idx, (name, pred_values) in enumerate(predictions.items()):
        ax.plot(time_axis, pred_values[day_idx], label=f"{name}预测", color=PALETTE[idx + 1], linewidth=1.9)

    ax.plot(time_axis, test_Y[day_idx], label="实测功率", linestyle="--", linewidth=2.2, color="#222222")
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
    ax.set_title(f"问题3三模型单日预测对比（目标日：{pd.Timestamp(ts).date()}）")
    ax.set_xlabel("日内时刻")
    ax.set_ylabel("功率/MW")
    format_intraday_axis(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4)
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure("三模型每日预测对比图_白昼.png", fig=fig, show=SHOW_PLOTS)


def export_all_predictions(predictions: dict[str, np.ndarray]):
    records = []
    for idx, ts in enumerate(test_timestamps):
        target_start = pd.to_datetime(ts).replace(hour=0, minute=0, second=0)
        issue_time = target_start - pd.Timedelta(days=1)
        for step in range(FORECAST_LENGTH):
            row = {
                "起报时间": issue_time,
                "预报时间": target_start + pd.Timedelta(minutes=15 * step),
                "实际功率": float(test_Y[idx, step]),
            }
            for name, pred_values in predictions.items():
                row[f"{name}预测功率"] = float(pred_values[idx, step])
            records.append(row)

    df_all_preds = pd.DataFrame(records)
    path = ARTIFACTS.write_csv("predictions", "3三模型预测结果对比表.csv", df_all_preds, index=False)
    print(f"\n已保存统一预测对比表格为：{path}", flush=True)
    return path


def main() -> None:
    model_dict = {
        "PureLSTM": PureLSTM(input_len=INPUT_LENGTH, input_dim=INPUT_DIM),
        "FusionModel": FusionModel(input_len=INPUT_LENGTH, input_dim=INPUT_DIM),
        "BiFusionModel": BiFusionModel(input_len=INPUT_LENGTH, input_dim=INPUT_DIM),
    }
    predictions: dict[str, np.ndarray] = {}
    metrics_all: dict[str, dict[str, float]] = {}
    reused_checkpoints: dict[str, bool] = {}
    scalar_metrics: dict[str, dict[str, float]] = {}

    print(
        f"问题3样本概况：训练窗口 {len(train_X)} 个，严格测试日 {len(test_timestamps)} 天，"
        f"输入维度={INPUT_DIM}, epochs={TRAINING_EPOCHS}, batch_size={BATCH_SIZE}, patience={TRAINING_PATIENCE}",
        flush=True,
    )

    for name, model in model_dict.items():
        print(f"\n===== 正在训练/加载模型：{name} =====", flush=True)
        model, target_scale, reused = train_model(
            model,
            train_X,
            train_Y,
            batch_size=BATCH_SIZE,
            epochs=TRAINING_EPOCHS,
            lr=LEARNING_RATE,
            patience=TRAINING_PATIENCE,
            checkpoint_name=f"problem3_{name}",
            force_retrain=FORCE_RETRAIN,
        )
        preds, rmse, mae, mape = evaluate_model(model, test_X, test_Y, test_timestamps, df, target_scale)
        metrics = compute_all_metrics(test_Y, preds, test_timestamps, df, capacity_kW=CAPACITY_KW)

        predictions[name] = preds
        metrics_all[name] = metrics
        reused_checkpoints[name] = reused
        scalar_metrics[name] = {"rmse_mw": rmse, "mae_mw": mae, "mape_percent": mape}

        export_prediction_table(
            preds,
            test_Y,
            test_timestamps,
            method_name=f"{name}预测功率",
            output_file=f"3prediction_{name}.csv",
        )

        print(f"\n>> 可视化：{name}", flush=True)
        visualize_predictions(preds, test_Y, test_timestamps, df, model_name=name)
        plot_professional_forecast(preds, test_Y, test_timestamps, df, model_name=name)
        plot_error_analysis(preds, test_Y, test_timestamps, df, model_name=name)
        interactive_forecast_plot(preds, test_Y, test_timestamps, model_name=name)

    df_metrics = pd.DataFrame(metrics_all).T
    df_metrics.index.name = "模型"
    print("\n问题3三模型评估指标对比：", flush=True)
    print(df_metrics.round(4), flush=True)
    ARTIFACTS.write_csv("metrics", "三模型白昼指标对比.csv", df_metrics, index=True)
    plot_metric_heatmap(df_metrics)
    plot_three_model_day(predictions)
    export_all_predictions(predictions)

    ARTIFACTS.write_summary(
        {
            "problem": "problem3_scenario_analysis",
            "models": list(model_dict.keys()),
            "train_samples": len(train_X),
            "test_days": len(test_timestamps),
            "test_date_first_in_problem_order": str(pd.to_datetime(test_timestamps[0]).date()),
            "test_date_last_in_problem_order": str(pd.to_datetime(test_timestamps[-1]).date()),
            "test_date_min": str(pd.to_datetime(test_timestamps).min().date()),
            "test_date_max": str(pd.to_datetime(test_timestamps).max().date()),
            "input_length": INPUT_LENGTH,
            "forecast_length": FORECAST_LENGTH,
            "input_dim": INPUT_DIM,
            "input_features": MODEL_INPUT_LABELS,
            "capacity_kw": CAPACITY_KW,
            "training": {
                "epochs": TRAINING_EPOCHS,
                "batch_size": BATCH_SIZE,
                "patience": TRAINING_PATIENCE,
                "learning_rate": LEARNING_RATE,
                "hidden_dim": HIDDEN_DIM,
                "force_retrain": FORCE_RETRAIN,
                "checkpoint_reused": reused_checkpoints,
            },
            "daylight_scalar_metrics": scalar_metrics,
            "best_models": {
                "E_rmse_min": str(df_metrics["E_rmse"].idxmin()),
                "E_mae_min": str(df_metrics["E_mae"].idxmin()),
                "C_R_max": str(df_metrics["C_R"].idxmax()),
                "Q_R_max": str(df_metrics["Q_R"].idxmax()),
                "daylight_rmse_mw_min": min(
                    scalar_metrics,
                    key=lambda model_name: scalar_metrics[model_name]["rmse_mw"],
                ),
            },
            "metric_heatmap_scoring": "E_rmse/E_mae/abs(E_me) are inverted; r/C_R/Q_R are direct, all normalized by column.",
            "table_time_alignment": "issue_time is previous-day 00:00; forecast_time covers the target test day",
            "elapsed_seconds": time.time() - SCRIPT_START_TIME,
        }
    )


if __name__ == "__main__":
    main()
