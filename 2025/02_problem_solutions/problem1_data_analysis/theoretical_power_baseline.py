# -*- coding: utf-8 -*-
"""Problem 1 baseline theoretical-power calculation.

This is the compact baseline model kept for comparison with the fuller
diagnostics script.  It now writes reproducible tables, metrics, figures, and a
run summary under ``outputs/`` instead of relying on an interactive plot window.
"""

from __future__ import annotations

import sys
from math import cos, radians, sin
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared" for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
    if (parent / "_shared").exists()
)
sys.path.insert(0, str(SHARED_DIR))

from pv_project import (  # noqa: E402
    ExperimentArtifacts,
    configure_matplotlib,
    resolve_input,
    set_working_directory,
)


INPUT_FILENAME = "Solar station site 5 (Nominal capacity-110MW).xlsx"
DAYLIGHT_THRESHOLD_MW = 0.5


def compute_zenith_angle(dt: pd.Timestamp, lat: float) -> float:
    """Estimate solar zenith angle with the original simplified baseline."""

    day_of_year = dt.timetuple().tm_yday
    hour_angle = 15 * ((dt.hour + dt.minute / 60) - 12)
    decl = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
    elevation = np.arcsin(
        np.sin(np.radians(lat)) * np.sin(np.radians(decl))
        + np.cos(np.radians(lat)) * np.cos(np.radians(decl)) * np.cos(np.radians(hour_angle))
    )
    return float(np.clip(np.degrees(np.pi / 2 - elevation), 0, 90))


def compute_incidence_factor(zenith_deg: float, beta_deg: float, phi_sun_deg: float, phi_p_deg: float) -> float:
    z = radians(zenith_deg)
    b = radians(beta_deg)
    az_diff = radians(phi_sun_deg - phi_p_deg)
    return max(cos(z) * cos(b) + sin(z) * sin(b) * cos(az_diff), 0)


def compute_transmission_factor(row: pd.Series, zenith: float, tau_a: float, ozone_column: float) -> float:
    m = 1 / (cos(np.radians(zenith)) + 0.50572 * (96.07995 - zenith) ** -1.6364)
    tr = np.exp(-0.0903 * (row["Pressure"] / 1013.25) ** 0.84 * (1 + cos(np.radians(zenith))) ** -1.01)
    ta = np.exp(-tau_a * (0.6777 + 0.1464 * tau_a - 0.00626 * tau_a**2) * m)
    to = 1 - 0.011 * (ozone_column * m) / (1 + 0.006 * (ozone_column * m) ** 1.5)
    uw = 0.1 * row["RH"] * np.exp(0.07 * row["Temp"])
    tw = 1 - 0.077 * (uw * m) ** 0.3
    tg = np.exp(-0.0117 * m**0.3139)
    return float(np.clip(tr * ta * to * tw * tg, 0, 1))


def load_data() -> pd.DataFrame:
    df = pd.read_excel(resolve_input(INPUT_FILENAME, __file__))
    df = df.iloc[:, :8].copy()
    df.columns = ["Time", "Total", "DNI", "GHI", "Temp", "Pressure", "RH", "Power"]
    df["Time"] = pd.to_datetime(df["Time"])
    for column in ["Total", "DNI", "GHI", "Temp", "Pressure", "RH", "Power"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["Time", "DNI", "GHI", "Temp", "Pressure", "RH", "Power"])


def add_baseline_power(df: pd.DataFrame) -> pd.DataFrame:
    lat = 31.1708218
    beta = 31.17
    phi_p = 180
    area = 611111.11
    eta_ref = 0.18
    gamma = 0.0045
    kappa = 0.03
    ground_albedo = 0.2
    tau_a = 0.15
    ozone_column = 0.3

    result = df.copy()
    power_values: list[float] = []
    for _, row in result.iterrows():
        zenith = compute_zenith_angle(row["Time"], lat)
        if zenith >= 90:
            power_values.append(0.0)
            continue

        cos_theta_i = compute_incidence_factor(zenith, beta, 180, phi_p)
        dhi = max(row["GHI"] - row["DNI"] * cos(np.radians(zenith)), 0)
        geff = (
            row["DNI"] * cos_theta_i
            + dhi * (1 + cos(np.radians(beta))) / 2
            + ground_albedo * row["GHI"] * (1 - cos(np.radians(beta))) / 2
        )
        eta = eta_ref * (1 - gamma * (row["Temp"] + kappa * row["GHI"] - 25))
        transmission = compute_transmission_factor(row, zenith, tau_a, ozone_column)
        power_values.append(max(eta * transmission * geff * area / 1e6, 0))

    result["Power_actual"] = result["Power"].clip(lower=0)
    result["P_theo_baseline"] = power_values
    result["Error_MW"] = result["P_theo_baseline"] - result["Power_actual"]
    return result


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    daylight = df[df["P_theo_baseline"] > DAYLIGHT_THRESHOLD_MW]
    err = daylight["Error_MW"].to_numpy(dtype=float)
    actual = daylight["Power_actual"].to_numpy(dtype=float)
    pred = daylight["P_theo_baseline"].to_numpy(dtype=float)
    return pd.DataFrame(
        [
            {
                "Model": "simplified_atmospheric_baseline",
                "Samples": int(len(daylight)),
                "RMSE_MW": float(np.sqrt(np.mean(err**2))),
                "MAE_MW": float(np.mean(np.abs(err))),
                "ME_MW": float(np.mean(err)),
                "Mean_Relative_Error": float(np.mean(err / pred)),
                "Correlation": float(np.corrcoef(actual, pred)[0, 1]),
            }
        ]
    )


def plot_power_comparison(df: pd.DataFrame) -> plt.Figure:
    daily = df.set_index("Time")[["Power_actual", "P_theo_baseline"]].resample("D").mean()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(daily.index, daily["Power_actual"], label="实测功率")
    ax.plot(daily.index, daily["P_theo_baseline"], label="基线理论功率", linestyle="--")
    ax.set_title("基线理论功率与实测功率对比（日均）")
    ax.set_xlabel("日期")
    ax.set_ylabel("功率 / MW")
    ax.legend()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig


def main() -> int:
    set_working_directory(__file__)
    font = configure_matplotlib()
    artifacts = ExperimentArtifacts(__file__)

    result = add_baseline_power(load_data())
    metrics = compute_metrics(result)
    artifacts.write_csv(
        "predictions",
        "problem1_baseline_theoretical_power_timeseries.csv",
        result[["Time", "Power", "Power_actual", "P_theo_baseline", "Error_MW"]],
        index=False,
    )
    artifacts.write_csv("metrics", "problem1_baseline_error_metrics.csv", metrics, index=False)
    artifacts.save_figure("problem1_baseline_daily_power_comparison.png", plot_power_comparison(result))
    artifacts.write_summary(
        {
            "rows": int(len(result)),
            "font": font,
            "daylight_threshold_mw": DAYLIGHT_THRESHOLD_MW,
            "metrics": metrics.to_dict(orient="records"),
        }
    )

    row = metrics.iloc[0]
    print("问题1基线理论功率计算完成")
    print(f"RMSE={row['RMSE_MW']:.3f} MW, MAE={row['MAE_MW']:.3f} MW, 相关系数={row['Correlation']:.3f}")
    print(f"输出目录: {artifacts.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
