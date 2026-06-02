# -*- coding: utf-8 -*-
"""
Problem 4: input-feature ablation for day-ahead PV forecasting.

The experiment compares NWP, LMD, and mixed meteorological inputs under the
same strict day-ahead alignment: previous-day measured power is combined with
target-day weather feature sequences to predict the target day's 96 power
points.  The script writes all predictions, metrics, figures, checkpoints, and
run metadata to the local outputs/ and models/ folders.
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
SAVE_RUN_DIAGNOSTICS = os.getenv("PV_Q4_SAVE_RUN_DIAGNOSTICS", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}

NWP_FEATURES = [
    "nwp_globalirrad",
    "nwp_directirrad",
    "nwp_temperature",
    "nwp_humidity",
    "nwp_windspeed",
    "nwp_pressure",
    "nwp_wind_x",
    "nwp_wind_y",
]
LMD_FEATURES = [
    "lmd_totalirrad",
    "lmd_diffuseirrad",
    "lmd_temperature",
    "lmd_pressure",
    "lmd_windspeed",
    "lmd_wind_x",
    "lmd_wind_y",
]
MODE_FEATURES = {
    "nwp": NWP_FEATURES,
    "lmd": LMD_FEATURES,
    "mixed": [*NWP_FEATURES, *LMD_FEATURES],
}
MODE_LABELS = {
    "nwp": "NWP",
    "lmd": "LMD",
    "mixed": "NWP+LMD",
}
MODEL_LABELS = {
    "PureLSTM": "PureLSTM",
    "FusionModel": "FusionModel",
    "BiFusionModel": "BiFusionModel",
}
METRIC_LABELS = {
    "RMSE": "白昼RMSE/MW",
    "MAE": "白昼MAE/MW",
    "MAPE": "白昼MAPE/%",
    "E_rmse": "归一化均方根误差",
    "E_mae": "归一化平均绝对误差",
    "E_me": "归一化平均误差",
    "r": "相关系数",
    "C_R": "准确率/%",
    "Q_R": "合格率/%",
}
PALETTE = journal_palette(10)


def parse_csv_env(name: str, default: list[str], allowed: set[str]) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    if raw.lower() == "all":
        return list(allowed)

    values = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [item for item in values if item not in allowed]
    if invalid:
        raise ValueError(f"{name} 包含不支持的取值：{invalid}；允许值为 {sorted(allowed)}")
    return values


SELECTED_MODES = parse_csv_env("PV_Q4_MODES", ["nwp", "lmd", "mixed"], set(MODE_FEATURES))
SELECTED_MODELS = parse_csv_env(
    "PV_Q4_MODELS",
    ["FusionModel"],
    {"PureLSTM", "FusionModel", "BiFusionModel"},
)


def load_station_data() -> tuple[pd.DataFrame, list[datetime.date]]:
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
        raise ValueError("未找到可用于问题4测试集的目标日期，请检查 station00.csv 的时间范围。")

    df["set"] = df["date"].apply(lambda d: "test" if d in test_dates else "train")
    df["is_daytime"] = df["power"] > DAYLIGHT_POWER_THRESHOLD
    df["nwp_wind_x"] = np.cos(np.radians(df["nwp_winddirection"]))
    df["nwp_wind_y"] = np.sin(np.radians(df["nwp_winddirection"]))
    df["lmd_wind_x"] = np.cos(np.radians(df["lmd_winddirection"]))
    df["lmd_wind_y"] = np.sin(np.radians(df["lmd_winddirection"]))

    raw_features = ["power"]
    for features in MODE_FEATURES.values():
        for feature in features:
            if feature not in raw_features:
                raw_features.append(feature)

    missing = [feature for feature in raw_features if feature not in df.columns]
    if missing:
        raise ValueError(f"station00.csv 缺少问题4所需字段：{missing}")

    df, _, _ = minmax_scale_train_only(df, raw_features)
    return df, test_dates


df, target_test_days = load_station_data()


def build_feature_window(prev_rows: pd.DataFrame, target_rows: pd.DataFrame, mode: str) -> np.ndarray:
    previous_power = prev_rows[["power_scaled"]].to_numpy(dtype=np.float32)
    weather_columns = [f"{feature}_scaled" for feature in MODE_FEATURES[mode]]
    target_weather = target_rows[weather_columns].to_numpy(dtype=np.float32)
    return np.concatenate([previous_power, target_weather], axis=1)


def construct_mode_samples(
    source_df: pd.DataFrame,
    mode: str,
    input_len: int = INPUT_LENGTH,
    forecast_len: int = FORECAST_LENGTH,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    train_X, train_Y = [], []
    test_X, test_Y, test_timestamps = [], [], []

    for start in range(len(source_df) - input_len - forecast_len + 1):
        prev_rows = source_df.iloc[start : start + input_len]
        target_rows = source_df.iloc[start + input_len : start + input_len + forecast_len]
        if (prev_rows["set"] == "train").all() and (target_rows["set"] == "train").all():
            train_X.append(build_feature_window(prev_rows, target_rows, mode))
            train_Y.append(target_rows["power"].to_numpy(dtype=np.float32))

    for test_day in target_test_days:
        prev_day = test_day - datetime.timedelta(days=1)
        prev_rows = source_df[source_df["date"] == prev_day]
        target_rows = source_df[source_df["date"] == test_day]
        if len(prev_rows) == input_len and len(target_rows) == forecast_len:
            test_X.append(build_feature_window(prev_rows, target_rows, mode))
            test_Y.append(target_rows["power"].to_numpy(dtype=np.float32))
            test_timestamps.append(pd.Timestamp(test_day))

    if not train_X:
        raise ValueError(f"{mode} 输入模式训练样本为空，请检查训练/测试日期划分。")
    if not test_X:
        raise ValueError(f"{mode} 输入模式测试样本为空，请检查目标日前一日与目标日是否均有完整 96 点。")

    return (
        np.asarray(train_X, dtype=np.float32),
        np.asarray(train_Y, dtype=np.float32),
        np.asarray(test_X, dtype=np.float32),
        np.asarray(test_Y, dtype=np.float32),
        np.asarray(test_timestamps),
    )


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
    def __init__(self, input_len: int = INPUT_LENGTH, input_dim: int = 9):
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
    def __init__(self, input_len: int = INPUT_LENGTH, input_dim: int = 9, hidden_dim: int = HIDDEN_DIM):
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
    def __init__(self, input_len: int = INPUT_LENGTH, input_dim: int = 9, hidden_dim: int = HIDDEN_DIM):
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


def create_model(model_name: str, input_dim: int) -> nn.Module:
    if model_name == "PureLSTM":
        return PureLSTM(input_len=INPUT_LENGTH, input_dim=input_dim)
    if model_name == "FusionModel":
        return FusionModel(input_len=INPUT_LENGTH, input_dim=input_dim)
    if model_name == "BiFusionModel":
        return BiFusionModel(input_len=INPUT_LENGTH, input_dim=input_dim)
    raise ValueError(f"未知模型：{model_name}")


def train_model(
    model: nn.Module,
    train_X: np.ndarray,
    train_Y: np.ndarray,
    *,
    mode: str,
    mode_features: list[str],
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

    checkpoint_name = checkpoint_name or f"problem4_{model.__class__.__name__}_{mode}"
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
            "architecture_version": "problem4_target_weather_ablation_v2",
            "mode": mode,
            "input_dim": int(train_X.shape[-1]),
            "input_features": ["前一日功率", *mode_features],
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


def target_day_daylight_mask(ts, source_df: pd.DataFrame) -> np.ndarray:
    target_start = pd.to_datetime(ts)
    mask = (source_df["date_time"] >= target_start) & (
        source_df["date_time"] < target_start + pd.Timedelta(days=1)
    )
    is_daytime = source_df.loc[mask, "is_daytime"].to_numpy()[:FORECAST_LENGTH]
    if len(is_daytime) != FORECAST_LENGTH:
        raise ValueError(f"{target_start.date()} 的目标日数据不足 {FORECAST_LENGTH} 点。")
    return is_daytime


def daylight_arrays(true_values, pred_values, timestamps, source_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    all_true, all_pred = [], []
    for idx, ts in enumerate(pd.to_datetime(list(timestamps))):
        is_daytime = target_day_daylight_mask(ts, source_df)
        all_true.extend(np.asarray(true_values[idx])[is_daytime])
        all_pred.extend(np.asarray(pred_values[idx])[is_daytime])

    if not all_true:
        raise ValueError("白昼样本为空，无法计算问题4评价指标。")
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


def intraday_hour_axis(length=FORECAST_LENGTH) -> np.ndarray:
    return np.arange(length) * 0.25


def format_intraday_axis(ax) -> None:
    ax.set_xlim(0, 23.75)
    ticks = np.arange(0, 24, 3)
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(tick):02d}:00" for tick in ticks])


def export_prediction_table(
    preds,
    test_Y,
    test_timestamps,
    *,
    method_name: str,
    output_file: str,
) -> Path:
    records = []
    for idx, ts in enumerate(test_timestamps):
        target_start = pd.to_datetime(ts).replace(hour=0, minute=0, second=0)
        issue_time = target_start - pd.Timedelta(days=1)
        for step in range(FORECAST_LENGTH):
            records.append(
                {
                    "起报时间": issue_time,
                    "预报时间": target_start + pd.Timedelta(minutes=15 * step),
                    "实际功率 (MW)": float(test_Y[idx, step]),
                    f"{method_name} (MW)": float(preds[idx, step]),
                }
            )

    df_pred = pd.DataFrame(records)
    target = ARTIFACTS.write_csv("predictions", output_file, df_pred, index=False)
    print(f"预测结果已保存至 {target}", flush=True)
    return target


def plot_forecast_diagnostics(preds, test_Y, test_timestamps, source_df, run_name: str, display_name: str) -> None:
    model_slug = slugify_checkpoint_name(run_name)
    sample_index = 0
    ts = test_timestamps[sample_index]
    is_daytime = target_day_daylight_mask(ts, source_df)
    time_axis = intraday_hour_axis()
    sample_true = test_Y[sample_index]
    sample_pred = preds[sample_index]
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
    ax.set_title(f"{display_name} 目标日预测曲线（{pd.Timestamp(ts).date()}）")
    ax.set_xlabel("日内时刻")
    ax.set_ylabel("功率/MW")
    format_intraday_axis(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_forecast_curve.png", fig=fig, show=SHOW_PLOTS)

    all_true, all_pred = daylight_arrays(test_Y, preds, test_timestamps, source_df)
    errors = all_pred - all_true
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    sns.histplot(errors, kde=True, bins=42, color=PALETTE[2], edgecolor="white", linewidth=0.4, ax=ax)
    ax.axvline(x=0, color=PALETTE[3], linestyle="--", linewidth=1.5, label="零误差")
    ax.axvline(x=np.mean(errors), color=PALETTE[1], linestyle="-", linewidth=1.5, label="均值")
    ax.set_title(f"{display_name} 白昼预测误差分布")
    ax.set_xlabel("预测误差/MW")
    ax.set_ylabel("频数")
    ax.legend()
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_daylight_error_distribution.png", fig=fig, show=SHOW_PLOTS)

    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    sns.scatterplot(x=all_true, y=all_pred, alpha=0.42, s=24, edgecolor=None, color=PALETTE[0], ax=ax)
    max_val = max(float(np.max(all_true)), float(np.max(all_pred))) * 1.05
    ax.plot([0, max_val], [0, max_val], linestyle="--", color=PALETTE[3], label="理想预测线")
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    ax.set_title(f"{display_name} 实测-预测散点")
    ax.set_xlabel("实测功率/MW")
    ax.set_ylabel("预测功率/MW")
    ax.legend()
    apply_journal_axes(ax)
    fig.tight_layout()
    ARTIFACTS.save_figure(f"{model_slug}_actual_vs_predicted_scatter.png", fig=fig, show=SHOW_PLOTS)

    heatmap_errors = preds - test_Y
    for idx, ts_day in enumerate(test_timestamps):
        day_mask = target_day_daylight_mask(ts_day, source_df)
        heatmap_errors[idx, ~day_mask] = np.nan

    fig = plt.figure(figsize=(10.8, 8.2), constrained_layout=True)
    gs = fig.add_gridspec(3, 2)

    ax1 = fig.add_subplot(gs[0, 0])
    sns.histplot(x=errors, kde=True, ax=ax1, bins=36, color=PALETTE[0], edgecolor="white", linewidth=0.4)
    ax1.axvline(np.mean(errors), color=PALETTE[3], linestyle="--", linewidth=1.4)
    ax1.set_title("白昼误差分布")
    ax1.set_xlabel("预测误差/MW")
    ax1.set_ylabel("频数")

    ax2 = fig.add_subplot(gs[0, 1])
    sns.heatmap(
        heatmap_errors,
        cmap="RdBu_r",
        center=0,
        ax=ax2,
        cbar_kws={"label": "误差/MW"},
        xticklabels=12,
        yticklabels=4,
    )
    ax2.set_title("测试日白昼误差热力图")
    ax2.set_xlabel("日内 15 min 序号")
    ax2.set_ylabel("测试日序号")

    ax3 = fig.add_subplot(gs[1, 0])
    stats.probplot(errors, dist="norm", plot=ax3)
    ax3.get_lines()[0].set_markerfacecolor(PALETTE[0])
    ax3.get_lines()[0].set_markeredgecolor(PALETTE[0])
    ax3.get_lines()[1].set_color(PALETTE[3])
    ax3.title.set_text("误差正态性 Q-Q 图")
    ax3.set_xlabel("理论分位数")
    ax3.set_ylabel("有序误差")

    ax4 = fig.add_subplot(gs[1, 1])
    sns.residplot(
        x=all_true,
        y=all_pred,
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

    fig.suptitle(f"{display_name} 多维误差诊断", fontsize=13)
    apply_journal_figure(fig)
    ARTIFACTS.save_figure(f"{model_slug}_error_analysis_matrix.png", fig=fig, show=SHOW_PLOTS)

    time_points = [pd.Timestamp(ts) + pd.Timedelta(minutes=15 * step) for step in range(FORECAST_LENGTH)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_points, y=sample_true, name="实测功率", line=dict(color=PALETTE[0], width=3)))
    fig.add_trace(go.Scatter(x=time_points, y=sample_pred, name="预测功率", line=dict(color=PALETTE[1], width=3, dash="dot")))
    fig.update_layout(
        title=f"{display_name} 交互式预测曲线 - {pd.Timestamp(ts).date()}",
        xaxis_title="时间",
        yaxis_title="功率/MW",
        hovermode="x unified",
        template="plotly_white",
        height=500,
        margin=dict(l=50, r=50, b=80, t=80),
    )
    ARTIFACTS.save_plotly_html(f"{model_slug}_interactive_forecast_sample0.html", fig)


def metric_score_frame(df_results: pd.DataFrame) -> pd.DataFrame:
    metrics = [metric for metric in METRIC_LABELS if metric in df_results.columns]
    score = pd.DataFrame(index=df_results.index)
    lower_is_better = {"RMSE", "MAE", "MAPE", "E_rmse", "E_mae", "E_me"}
    for metric in metrics:
        source = df_results[metric].abs() if metric == "E_me" else df_results[metric]
        denominator = source.max() - source.min()
        if denominator == 0:
            score[metric] = 0.5
        elif metric in lower_is_better:
            score[metric] = 1 - (source - source.min()) / denominator
        else:
            score[metric] = (source - source.min()) / denominator
    return score


def plot_q4_result_overview(df_results: pd.DataFrame) -> None:
    metric_columns = [metric for metric in METRIC_LABELS if metric in df_results.columns]
    score = metric_score_frame(df_results)
    annotations = df_results[metric_columns].round(3).astype(str)

    fig, ax = plt.subplots(figsize=(11.2, 5.8))
    sns.heatmap(
        score.rename(columns=METRIC_LABELS),
        annot=annotations.rename(columns=METRIC_LABELS),
        fmt="",
        cmap="YlGnBu",
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": "列内表现得分"},
        ax=ax,
    )
    ax.set_title("问题4：输入特征消融白昼指标对比")
    ax.set_xlabel("评价指标")
    ax.set_ylabel("模型_输入")
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=28, ha="right")
    apply_journal_axes(ax, grid=False)
    fig.tight_layout()
    ARTIFACTS.save_figure("Q4_模型输入对比结果热力图.png", fig=fig, show=SHOW_PLOTS)

    run_column = df_results.index.name or "index"
    table = df_results.reset_index().rename(columns={run_column: "run"})
    table[["模型", "输入模式"]] = table["run"].str.rsplit("_", n=1, expand=True)
    mode_order = [mode for mode in SELECTED_MODES if mode in table["输入模式"].values]
    model_order = [model for model in SELECTED_MODELS if model in table["模型"].values]

    for metric in ["RMSE", "MAPE", "E_rmse"]:
        fig, ax = plt.subplots(figsize=(8.8, 4.6))
        sns.barplot(
            data=table,
            x="模型",
            y=metric,
            hue="输入模式",
            order=model_order,
            hue_order=mode_order,
            palette=PALETTE[: max(1, len(mode_order))],
            edgecolor="#222222",
            ax=ax,
        )
        ax.set_title(f"{METRIC_LABELS[metric]}：不同输入模式对比")
        ax.set_xlabel("模型")
        ax.set_ylabel(METRIC_LABELS[metric])
        ax.legend(title="输入模式")
        apply_journal_axes(ax)
        fig.tight_layout()
        ARTIFACTS.save_figure(f"{slugify_checkpoint_name(metric)}_指标对比_不同输入模式.png", fig=fig, show=SHOW_PLOTS)

    input_dims = {mode: 1 + len(MODE_FEATURES[mode]) for mode in SELECTED_MODES}
    for metric in ["C_R", "Q_R"]:
        fig, ax = plt.subplots(figsize=(8.2, 4.6))
        for idx, model in enumerate(model_order):
            model_table = table[table["模型"] == model]
            points = []
            for mode in mode_order:
                rows = model_table[model_table["输入模式"] == mode]
                if not rows.empty:
                    points.append((input_dims[mode], float(rows.iloc[0][metric]), MODE_LABELS[mode]))
            if points:
                points = sorted(points)
                ax.plot(
                    [item[0] for item in points],
                    [item[1] for item in points],
                    marker="o",
                    color=PALETTE[idx],
                    label=model,
                    linewidth=1.9,
                )
                for x_val, y_val, mode_label in points:
                    ax.text(x_val, y_val, mode_label, fontsize=8.5, ha="center", va="bottom")
        ax.set_title(f"{METRIC_LABELS[metric]} 与输入维度关系")
        ax.set_xlabel("输入特征维度")
        ax.set_ylabel(METRIC_LABELS[metric])
        ax.legend()
        apply_journal_axes(ax)
        fig.tight_layout()
        ARTIFACTS.save_figure(f"{slugify_checkpoint_name(metric)}_vs_输入特征维度.png", fig=fig, show=SHOW_PLOTS)

    if len(mode_order) >= 2:
        score_run_column = score.index.name or "index"
        score_table = score.reset_index().rename(columns={score_run_column: "run"})
        score_table[["模型", "输入模式"]] = score_table["run"].str.rsplit("_", n=1, expand=True)
        radar_metrics = [metric for metric in ["RMSE", "MAE", "E_rmse", "r", "C_R", "Q_R"] if metric in score.columns]
        angles = np.linspace(0, 2 * np.pi, len(radar_metrics), endpoint=False).tolist()
        angles += angles[:1]
        for model in model_order:
            fig, ax = plt.subplots(figsize=(6.4, 6.4), subplot_kw={"polar": True})
            for idx, mode in enumerate(mode_order):
                rows = score_table[(score_table["模型"] == model) & (score_table["输入模式"] == mode)]
                if rows.empty:
                    continue
                values = rows.iloc[0][radar_metrics].astype(float).tolist()
                values += values[:1]
                ax.plot(angles, values, label=MODE_LABELS[mode], linewidth=1.8, color=PALETTE[idx])
                ax.fill(angles, values, alpha=0.12, color=PALETTE[idx])
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels([METRIC_LABELS[metric] for metric in radar_metrics])
            ax.set_ylim(0, 1)
            ax.set_title(f"{model} 输入模式综合得分雷达图", y=1.1)
            ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.12))
            fig.tight_layout()
            ARTIFACTS.save_figure(f"{slugify_checkpoint_name(model)}_输入对比雷达图.png", fig=fig, show=SHOW_PLOTS)


def main() -> None:
    print(
        f"问题4配置：modes={SELECTED_MODES}, models={SELECTED_MODELS}, "
        f"epochs={TRAINING_EPOCHS}, batch_size={BATCH_SIZE}, patience={TRAINING_PATIENCE}, "
        f"save_run_diagnostics={SAVE_RUN_DIAGNOSTICS}",
        flush=True,
    )

    results: dict[str, dict[str, float]] = {}
    reused_checkpoints: dict[str, bool] = {}
    sample_summary: dict[str, dict[str, int]] = {}
    input_dimensions: dict[str, int] = {}

    for mode in SELECTED_MODES:
        mode_features = MODE_FEATURES[mode]
        train_X, train_Y, test_X, test_Y, test_timestamps = construct_mode_samples(df, mode)
        sample_summary[mode] = {
            "train_samples": int(len(train_X)),
            "test_days": int(len(test_X)),
        }
        input_dimensions[mode] = int(train_X.shape[-1])
        print(
            f"\n===== 输入模式：{mode.upper()} | 特征维度={train_X.shape[-1]} | "
            f"训练窗口={len(train_X)} | 测试日={len(test_X)} =====",
            flush=True,
        )

        for model_name in SELECTED_MODELS:
            run_name = f"{model_name}_{mode}"
            display_name = f"{MODEL_LABELS[model_name]}-{MODE_LABELS[mode]}"
            print(f"\n>> 模型：{model_name} | 输入：{mode}", flush=True)
            model = create_model(model_name, input_dim=train_X.shape[-1])
            model_trained, target_scale, reused = train_model(
                model,
                train_X,
                train_Y,
                mode=mode,
                mode_features=mode_features,
                checkpoint_name=f"problem4_{run_name}",
                force_retrain=FORCE_RETRAIN,
            )
            preds, rmse, mae, mape = evaluate_model(model_trained, test_X, test_Y, test_timestamps, df, target_scale)
            metrics = compute_all_metrics(test_Y, preds, test_timestamps, df)

            results[run_name] = {
                "RMSE": rmse,
                "MAE": mae,
                "MAPE": mape,
                **metrics,
            }
            reused_checkpoints[run_name] = reused

            export_prediction_table(
                preds,
                test_Y,
                test_timestamps,
                method_name=run_name,
                output_file=f"Q4_pred_{run_name}.csv",
            )
            if SAVE_RUN_DIAGNOSTICS:
                plot_forecast_diagnostics(
                    preds,
                    test_Y,
                    test_timestamps,
                    df,
                    run_name=run_name,
                    display_name=display_name,
                )

    df_results = pd.DataFrame(results).T
    df_results.index.name = "模型_输入"
    print("\n======= 问题4输入特征消融结果表 =======", flush=True)
    print(df_results.round(4), flush=True)
    ARTIFACTS.write_csv("metrics", "Q4_模型输入对比结果.csv", df_results, index=True)
    plot_q4_result_overview(df_results)

    best_key = str(df_results["E_rmse"].idxmin())
    ARTIFACTS.write_summary(
        {
            "problem": "problem4_feature_ablation",
            "models": SELECTED_MODELS,
            "input_modes": SELECTED_MODES,
            "feature_modes": MODE_FEATURES,
            "input_dimensions": input_dimensions,
            "sample_summary": sample_summary,
            "test_date_first_in_problem_order": str(pd.to_datetime(target_test_days[0]).date()),
            "test_date_last_in_problem_order": str(pd.to_datetime(target_test_days[-1]).date()),
            "test_date_min": str(pd.to_datetime(target_test_days).min().date()),
            "test_date_max": str(pd.to_datetime(target_test_days).max().date()),
            "training": {
                "epochs": TRAINING_EPOCHS,
                "batch_size": BATCH_SIZE,
                "patience": TRAINING_PATIENCE,
                "learning_rate": LEARNING_RATE,
                "hidden_dim": HIDDEN_DIM,
                "force_retrain": FORCE_RETRAIN,
                "save_run_diagnostics": SAVE_RUN_DIAGNOSTICS,
                "checkpoint_reused": reused_checkpoints,
            },
            "best_run_by_E_rmse": best_key,
            "best_run_metrics": df_results.loc[best_key].to_dict(),
            "metric_heatmap_scoring": "RMSE/MAE/MAPE/E_rmse/E_mae/abs(E_me) are inverted; r/C_R/Q_R are direct, all normalized by column.",
            "table_time_alignment": "issue_time is previous-day 00:00; forecast_time covers the target test day",
            "weather_feature_alignment": "previous-day measured power plus target-day weather feature sequence",
            "elapsed_seconds": time.time() - SCRIPT_START_TIME,
        }
    )


if __name__ == "__main__":
    main()
