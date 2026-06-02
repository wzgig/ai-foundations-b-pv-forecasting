# -*- coding: utf-8 -*-
"""Problem 1 theoretical-power diagnostics for station 5.

This script compares measured PV output with a physically derived theoretical
power curve and writes reproducible diagnostic artifacts under ``outputs/``.
The primary ``P_theo`` column uses measured ground irradiance directly.  The
older atmospheric-transmission variant is retained as ``P_theo_atmospheric``
for model-audit comparison.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
SHARED_DIR = PROJECT_ROOT / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from pv_project import ExperimentArtifacts, configure_matplotlib, resolve_input  # noqa: E402


INPUT_FILENAME = "Solar station site 5 (Nominal capacity-110MW).xlsx"
DATA_COLUMNS = ["Time", "TSI", "DNI", "GHI", "Air_Temp", "Pressure", "RH", "Power"]
DEFAULT_TYPICAL_DATE = "2019-06-15"
STANDARD_MERIDIAN = 120.0
DAYLIGHT_THRESHOLD_MW = 0.5


@dataclass(frozen=True)
class PhysicalParams:
    """Physical and empirical parameters used by the station-5 model."""

    latitude: float = 31.1708218
    longitude: float = 115.0159244
    beta: float = 31.1708218
    panel_azimuth: float = 180.0
    eta_ref: float = 0.18
    gamma: float = 0.0045
    kappa: float = 0.03
    module_area_m2: float = 611111.11
    ground_albedo: float = 0.2
    aerosol_optical_depth: float = 0.15
    ozone_column: float = 0.3
    standard_pressure_hpa: float = 1013.25
    nominal_capacity_mw: float = 110.0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate station-5 theoretical-power diagnostics.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional Excel input path. Defaults to the station-5 file beside this script.",
    )
    parser.add_argument(
        "--date",
        default=DEFAULT_TYPICAL_DATE,
        help="Typical-day date for the intraday plot, formatted as YYYY-MM-DD.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show figures interactively after saving them. Default is save-only.",
    )
    return parser.parse_args(argv)


def load_station_data(input_path: Path) -> tuple[pd.DataFrame, int]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    raw = pd.read_excel(input_path)
    if raw.shape[1] < len(DATA_COLUMNS):
        raise ValueError(
            f"Expected at least {len(DATA_COLUMNS)} columns in {input_path.name}, "
            f"but found {raw.shape[1]}."
        )

    df = raw.iloc[:, : len(DATA_COLUMNS)].copy()
    df.columns = DATA_COLUMNS
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    for column in DATA_COLUMNS[1:]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    before_drop = len(df)
    required = ["Time", "DNI", "GHI", "Air_Temp", "Pressure", "RH", "Power"]
    df = df.dropna(subset=required).sort_values("Time").reset_index(drop=True)
    dropped_rows = before_drop - len(df)

    df["Power_actual"] = df["Power"].clip(lower=0)
    df["DayOfYear"] = df["Time"].dt.dayofyear
    df["Hour"] = df["Time"].dt.hour + df["Time"].dt.minute / 60
    df["Month"] = df["Time"].dt.month
    df["Date"] = df["Time"].dt.date
    return df, dropped_rows


def infer_interval_hours(time_values: pd.Series) -> float:
    deltas = time_values.sort_values().diff().dropna().dt.total_seconds() / 3600
    positive = deltas[deltas > 0]
    if positive.empty:
        return 0.25
    return float(positive.median())


def solar_position(
    day_of_year: np.ndarray,
    hour: np.ndarray,
    params: PhysicalParams,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    b = 2 * np.pi * (day_of_year - 81) / 364
    equation_of_time = 9.87 * np.sin(2 * b) - 7.53 * np.cos(b) - 1.5 * np.sin(b)
    time_correction = 4 * (params.longitude - STANDARD_MERIDIAN) + equation_of_time
    local_solar_time = hour + time_correction / 60

    declination = 23.45 * np.sin(2 * np.pi * (284 + day_of_year) / 365)
    hour_angle = 15 * (local_solar_time - 12)

    latitude_rad = np.radians(params.latitude)
    declination_rad = np.radians(declination)
    hour_angle_rad = np.radians(hour_angle)
    cos_zenith = (
        np.sin(latitude_rad) * np.sin(declination_rad)
        + np.cos(latitude_rad) * np.cos(declination_rad) * np.cos(hour_angle_rad)
    )
    cos_zenith = np.clip(cos_zenith, -1.0, 1.0)
    theta_z = np.degrees(np.arccos(cos_zenith))

    phi_s = np.degrees(
        np.arctan2(
            -np.sin(hour_angle_rad),
            np.tan(declination_rad) * np.cos(latitude_rad)
            - np.sin(latitude_rad) * np.cos(hour_angle_rad),
        )
    )
    phi_s = (phi_s + 360) % 360
    return theta_z, phi_s, cos_zenith


def add_theoretical_power(df: pd.DataFrame, params: PhysicalParams) -> pd.DataFrame:
    result = df.copy()
    theta_z, phi_s, cos_zenith = solar_position(
        result["DayOfYear"].to_numpy(dtype=float),
        result["Hour"].to_numpy(dtype=float),
        params,
    )

    beta_rad = np.radians(params.beta)
    cos_theta_i = (
        np.cos(np.radians(theta_z)) * np.cos(beta_rad)
        + np.sin(np.radians(theta_z))
        * np.sin(beta_rad)
        * np.cos(np.radians(phi_s - params.panel_azimuth))
    )
    cos_theta_i = np.clip(cos_theta_i, 0, None)
    cos_zenith_positive = np.clip(cos_zenith, 0, None)
    sun_up = cos_zenith > 0

    dni = result["DNI"].to_numpy(dtype=float)
    ghi = result["GHI"].to_numpy(dtype=float)
    dhi = np.clip(ghi - dni * cos_zenith_positive, 0, None)

    geff = (
        dni * cos_theta_i
        + dhi * (1 + np.cos(beta_rad)) / 2
        + params.ground_albedo * ghi * (1 - np.cos(beta_rad)) / 2
    )
    geff = np.where(sun_up, geff, 0)

    eta = params.eta_ref * (
        1 - params.gamma * (result["Air_Temp"].to_numpy(dtype=float) + params.kappa * ghi - 25)
    )
    eta = np.clip(eta, 0, None)

    p_uncapped = eta * geff * params.module_area_m2 / 1e6
    p_theo = np.clip(p_uncapped, 0, params.nominal_capacity_mw)

    zenith_for_airmass = np.minimum(theta_z, 89.9)
    air_mass = 1 / (
        np.cos(np.radians(zenith_for_airmass))
        + 0.50572 * (96.07995 - zenith_for_airmass) ** -1.6364
    )
    air_mass = np.where(sun_up, air_mass, np.nan)

    pressure = result["Pressure"].to_numpy(dtype=float)
    relative_humidity = result["RH"].to_numpy(dtype=float)
    air_temp = result["Air_Temp"].to_numpy(dtype=float)
    cos_zenith_for_airmass = np.cos(np.radians(zenith_for_airmass))

    tr = np.exp(
        -0.0903
        * (pressure / params.standard_pressure_hpa) ** 0.84
        * (1 + cos_zenith_for_airmass) ** -1.01
    )
    ta = np.exp(
        -params.aerosol_optical_depth
        * (
            0.6777
            + 0.1464 * params.aerosol_optical_depth
            - 0.00626 * params.aerosol_optical_depth**2
        )
        * air_mass
    )
    to = 1 - (0.011 * params.ozone_column * air_mass) / (
        1 + 0.006 * (params.ozone_column * air_mass) ** 1.5
    )
    precipitable_water = 0.1 * relative_humidity * np.exp(0.07 * air_temp)
    tw = 1 - 0.077 * (precipitable_water * air_mass) ** 0.3
    tg = np.exp(-0.0117 * air_mass**0.3139)

    transmission = np.clip(tr, 0, 1) * np.clip(ta, 0, 1) * np.clip(to, 0, 1)
    transmission *= np.clip(tw, 0, 1) * np.clip(tg, 0, 1)
    p_atmospheric = eta * transmission * geff * params.module_area_m2 / 1e6
    p_atmospheric = np.nan_to_num(p_atmospheric, nan=0.0, posinf=0.0, neginf=0.0)
    p_atmospheric = np.clip(p_atmospheric, 0, params.nominal_capacity_mw)

    result["theta_z"] = theta_z
    result["phi_s"] = phi_s
    result["cos_theta_i"] = cos_theta_i
    result["DHI"] = dhi
    result["Geff"] = geff
    result["air_mass"] = air_mass
    result["transmission"] = np.nan_to_num(transmission, nan=0.0, posinf=0.0, neginf=0.0)
    result["eta"] = eta
    result["P_theo_uncapped"] = np.clip(p_uncapped, 0, None)
    result["P_theo"] = p_theo
    result["P_theo_atmospheric"] = p_atmospheric
    return result


def compute_model_metrics(
    df: pd.DataFrame,
    prediction_col: str,
    label: str,
    params: PhysicalParams,
    daylight_threshold: float,
) -> dict[str, float | int | str]:
    mask = df[prediction_col] > daylight_threshold
    evaluation = df.loc[mask, ["Power_actual", prediction_col]].dropna()
    if evaluation.empty:
        return {
            "Model": label,
            "PredictionColumn": prediction_col,
            "Samples": 0,
            "RMSE_MW": np.nan,
            "MAE_MW": np.nan,
            "ME_MW": np.nan,
            "Mean_Relative_Error": np.nan,
            "Median_Relative_Error": np.nan,
            "MAPE": np.nan,
            "NRMSE_Capacity": np.nan,
            "Correlation": np.nan,
        }

    actual = evaluation["Power_actual"].to_numpy(dtype=float)
    pred = evaluation[prediction_col].to_numpy(dtype=float)
    err = pred - actual
    rel_err = err / pred
    actual_positive = actual > daylight_threshold
    mape = (
        np.mean(np.abs(err[actual_positive] / actual[actual_positive]))
        if np.any(actual_positive)
        else np.nan
    )
    corr = np.corrcoef(actual, pred)[0, 1] if len(evaluation) > 1 else np.nan

    return {
        "Model": label,
        "PredictionColumn": prediction_col,
        "Samples": int(len(evaluation)),
        "RMSE_MW": float(np.sqrt(np.mean(err**2))),
        "MAE_MW": float(np.mean(np.abs(err))),
        "ME_MW": float(np.mean(err)),
        "Mean_Relative_Error": float(np.mean(rel_err)),
        "Median_Relative_Error": float(np.median(rel_err)),
        "MAPE": float(mape) if np.isfinite(mape) else np.nan,
        "NRMSE_Capacity": float(np.sqrt(np.mean(err**2)) / params.nominal_capacity_mw),
        "Correlation": float(corr) if np.isfinite(corr) else np.nan,
    }


def build_monthly_stats(df: pd.DataFrame, interval_hours: float) -> pd.DataFrame:
    grouped = df.groupby("Month")
    monthly = grouped.agg(
        Actual_Mean_MW=("Power_actual", "mean"),
        Theoretical_Mean_MW=("P_theo", "mean"),
        Atmospheric_Mean_MW=("P_theo_atmospheric", "mean"),
        Actual_Energy_MWh=("Power_actual", lambda value: value.sum() * interval_hours),
        Theoretical_Energy_MWh=("P_theo", lambda value: value.sum() * interval_hours),
    )
    monthly["Utilization"] = monthly["Actual_Mean_MW"] / monthly["Theoretical_Mean_MW"]
    monthly["Atmospheric_Utilization"] = (
        monthly["Actual_Mean_MW"] / monthly["Atmospheric_Mean_MW"]
    )
    monthly = monthly.replace([np.inf, -np.inf], np.nan).reset_index()
    return monthly


def add_error_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["Error_MW"] = result["P_theo"] - result["Power_actual"]
    result["Atmospheric_Error_MW"] = result["P_theo_atmospheric"] - result["Power_actual"]
    result["Rel_Error"] = np.where(
        result["P_theo"] > 0,
        result["Error_MW"] / result["P_theo"],
        np.nan,
    )
    result["Atmospheric_Rel_Error"] = np.where(
        result["P_theo_atmospheric"] > 0,
        result["Atmospheric_Error_MW"] / result["P_theo_atmospheric"],
        np.nan,
    )
    return result


def choose_typical_day(
    df: pd.DataFrame,
    preferred_date: str,
    interval_hours: float,
) -> tuple[pd.Timestamp.date, str]:
    requested = pd.to_datetime(preferred_date, errors="coerce")
    if pd.notna(requested):
        requested_date = requested.date()
        if requested_date in set(df["Date"]):
            return requested_date, "requested"

    daily = (
        df.groupby("Date")
        .agg(Samples=("Time", "size"), Energy_MWh=("Power_actual", lambda s: s.sum() * interval_hours))
        .reset_index()
    )
    valid = daily[(daily["Samples"] >= 80) & (daily["Energy_MWh"] > 0)]
    if valid.empty:
        return df["Date"].iloc[0], "fallback_first_available_date"

    target_energy = valid["Energy_MWh"].quantile(0.75)
    selected_idx = (valid["Energy_MWh"] - target_energy).abs().idxmin()
    return valid.loc[selected_idx, "Date"], "fallback_75th_percentile_energy_day"


def plot_monthly_power(monthly: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(monthly["Month"], monthly["Actual_Mean_MW"], marker="o", label="实测功率")
    ax.plot(monthly["Month"], monthly["Theoretical_Mean_MW"], marker="s", label="理论功率")
    ax.plot(
        monthly["Month"],
        monthly["Atmospheric_Mean_MW"],
        marker="^",
        linestyle="--",
        label="原大气修正口径",
    )
    ax.set_title("月平均功率对比")
    ax.set_xlabel("月份")
    ax.set_ylabel("功率 / MW")
    ax.set_xticks(range(1, 13))
    ax.legend()
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    return fig


def plot_monthly_efficiency(monthly: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(monthly["Month"], monthly["Utilization"], marker="o", label="实测/理论")
    ax.plot(
        monthly["Month"],
        monthly["Atmospheric_Utilization"],
        marker="^",
        linestyle="--",
        label="实测/原大气修正口径",
    )
    ax.axhline(1.0, color="0.35", linestyle=":", linewidth=1.5)
    ax.set_title("月平均利用效率")
    ax.set_xlabel("月份")
    ax.set_ylabel("比值")
    ax.set_xticks(range(1, 13))
    ax.legend()
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    return fig


def plot_typical_day(df: pd.DataFrame, selected_date) -> plt.Figure:
    typical = df[df["Date"] == selected_date]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(typical["Time"], typical["Power_actual"], label="实测功率")
    ax.plot(typical["Time"], typical["P_theo"], label="理论功率")
    ax.plot(
        typical["Time"],
        typical["P_theo_atmospheric"],
        linestyle="--",
        alpha=0.8,
        label="原大气修正口径",
    )
    ax.set_title(f"{selected_date} 日内功率变化")
    ax.set_xlabel("时间")
    ax.set_ylabel("功率 / MW")
    ax.legend()
    ax.grid(True, alpha=0.35)
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return fig


def plot_relative_error(df: pd.DataFrame, daylight_threshold: float) -> plt.Figure:
    daylight = df[df["P_theo"] > daylight_threshold].copy()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    sns.histplot(daylight["Rel_Error"].dropna(), bins=60, kde=True, color="#d55e00", ax=ax)
    mean_error = daylight["Rel_Error"].mean()
    median_error = daylight["Rel_Error"].median()
    ax.axvline(mean_error, color="#0072b2", linestyle="--", label=f"均值 {mean_error:.3f}")
    ax.axvline(median_error, color="#009e73", linestyle=":", label=f"中位数 {median_error:.3f}")
    ax.set_title("白昼时段相对偏差分布")
    ax.set_xlabel("相对误差 ε = (P_theo - P_actual) / P_theo")
    ax.set_ylabel("频数")
    ax.legend()
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    return fig


def plot_daily_mean_curve(df: pd.DataFrame) -> plt.Figure:
    daily = (
        df.set_index("Time")[["Power_actual", "P_theo", "P_theo_atmospheric"]]
        .resample("D")
        .mean()
        .dropna(how="all")
    )
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(daily.index, daily["Power_actual"], label="实测功率")
    ax.plot(daily.index, daily["P_theo"], label="理论功率")
    ax.plot(daily.index, daily["P_theo_atmospheric"], linestyle="--", label="原大气修正口径")
    ax.set_title("全时段日均功率对比")
    ax.set_xlabel("日期")
    ax.set_ylabel("日均功率 / MW")
    ax.legend()
    ax.grid(True, alpha=0.35)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig


def plot_actual_vs_theoretical(df: pd.DataFrame, daylight_threshold: float) -> plt.Figure:
    daylight = df[df["P_theo"] > daylight_threshold]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(
        daylight["Power_actual"],
        daylight["P_theo"],
        s=8,
        alpha=0.25,
        edgecolors="none",
        label="15 min 样本",
    )
    upper = float(np.nanmax([daylight["Power_actual"].max(), daylight["P_theo"].max()]))
    ax.plot([0, upper], [0, upper], color="0.25", linestyle="--", linewidth=1.5, label="1:1 参考线")
    ax.set_xlim(0, upper * 1.03)
    ax.set_ylim(0, upper * 1.03)
    ax.set_title("实测功率与理论功率散点诊断")
    ax.set_xlabel("实测功率 / MW")
    ax.set_ylabel("理论功率 / MW")
    ax.legend()
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    return fig


def save_figures(
    artifacts: ExperimentArtifacts,
    df: pd.DataFrame,
    monthly: pd.DataFrame,
    selected_date,
    daylight_threshold: float,
    show: bool,
) -> None:
    figures = [
        ("problem1_monthly_power_comparison.png", plot_monthly_power(monthly)),
        ("problem1_monthly_efficiency.png", plot_monthly_efficiency(monthly)),
        ("problem1_typical_day_power_comparison.png", plot_typical_day(df, selected_date)),
        ("problem1_daylight_relative_error_distribution.png", plot_relative_error(df, daylight_threshold)),
        ("problem1_daily_mean_power_comparison.png", plot_daily_mean_curve(df)),
        ("problem1_actual_vs_theoretical_scatter.png", plot_actual_vs_theoretical(df, daylight_threshold)),
    ]
    for filename, fig in figures:
        artifacts.save_figure(filename, fig=fig, show=show, close=not show)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    params = PhysicalParams()
    font_name = configure_matplotlib()

    input_path = args.input if args.input else resolve_input(INPUT_FILENAME, __file__)
    artifacts = ExperimentArtifacts(__file__)

    df, dropped_rows = load_station_data(input_path)
    interval_hours = infer_interval_hours(df["Time"])
    df = add_theoretical_power(df, params)
    df = add_error_columns(df)

    selected_date, selected_date_reason = choose_typical_day(df, args.date, interval_hours)
    monthly = build_monthly_stats(df, interval_hours)
    metrics = pd.DataFrame(
        [
            compute_model_metrics(df, "P_theo", "Measured-irradiance theoretical power", params, DAYLIGHT_THRESHOLD_MW),
            compute_model_metrics(
                df,
                "P_theo_atmospheric",
                "Legacy atmospheric-transmission variant",
                params,
                DAYLIGHT_THRESHOLD_MW,
            ),
        ]
    )
    relative_error_stats = (
        df.loc[df["P_theo"] > DAYLIGHT_THRESHOLD_MW, ["Rel_Error", "Atmospheric_Rel_Error"]]
        .describe()
        .T.reset_index()
        .rename(columns={"index": "Metric"})
    )

    result_columns = [
        "Time",
        "Power",
        "Power_actual",
        "P_theo",
        "P_theo_uncapped",
        "P_theo_atmospheric",
        "Error_MW",
        "Rel_Error",
        "Atmospheric_Error_MW",
        "Atmospheric_Rel_Error",
        "GHI",
        "DNI",
        "DHI",
        "Geff",
        "eta",
        "theta_z",
        "phi_s",
        "cos_theta_i",
        "air_mass",
        "transmission",
    ]
    artifacts.write_csv(
        "predictions",
        "problem1_theoretical_power_timeseries.csv",
        df[result_columns],
        index=False,
    )
    artifacts.write_csv("metrics", "problem1_monthly_power_stats.csv", monthly, index=False)
    artifacts.write_csv("metrics", "problem1_daylight_error_metrics.csv", metrics, index=False)
    artifacts.write_csv(
        "metrics",
        "problem1_relative_error_statistics.csv",
        relative_error_stats,
        index=False,
    )
    save_figures(artifacts, df, monthly, selected_date, DAYLIGHT_THRESHOLD_MW, args.show)

    metadata = {
        "input_file": str(input_path),
        "rows": int(len(df)),
        "dropped_rows": int(dropped_rows),
        "time_start": df["Time"].min(),
        "time_end": df["Time"].max(),
        "interval_hours": interval_hours,
        "font": font_name,
        "typical_day": str(selected_date),
        "typical_day_selection": selected_date_reason,
        "daylight_threshold_mw": DAYLIGHT_THRESHOLD_MW,
        "nominal_capacity_mw": params.nominal_capacity_mw,
        "model_note": (
            "P_theo uses measured DNI/GHI after plane-of-array transposition, "
            "temperature correction, nonnegative clipping, and nominal-capacity cap. "
            "P_theo_atmospheric keeps the previous extra atmospheric-transmission "
            "attenuation for comparison."
        ),
        "metrics": metrics.to_dict(orient="records"),
    }
    artifacts.write_summary(metadata)

    primary = metrics.iloc[0]
    legacy = metrics.iloc[1]
    print("理论功率诊断完成")
    print(f"输入数据: {input_path}")
    print(f"样本范围: {df['Time'].min()} 至 {df['Time'].max()}，共 {len(df)} 行")
    print(f"典型日: {selected_date} ({selected_date_reason})")
    print(
        "推荐口径: "
        f"RMSE={primary['RMSE_MW']:.3f} MW, "
        f"MAE={primary['MAE_MW']:.3f} MW, "
        f"相关系数={primary['Correlation']:.3f}"
    )
    print(
        "原大气修正口径: "
        f"RMSE={legacy['RMSE_MW']:.3f} MW, "
        f"MAE={legacy['MAE_MW']:.3f} MW, "
        f"相关系数={legacy['Correlation']:.3f}"
    )
    print(f"输出目录: {artifacts.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
