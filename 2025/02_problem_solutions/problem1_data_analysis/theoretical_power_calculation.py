# -*- coding: utf-8 -*-
"""Problem 1 full theoretical-power calculation.

This script is the calculation-focused companion to
``theoretical_power_diagnostics.py``.  It reuses the same physical model,
exports the full computed physical quantities, and creates compact journal-style
calculation figures under ``outputs/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared" for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
    if (parent / "_shared").exists()
)
sys.path.insert(0, str(SHARED_DIR))

from pv_project import ExperimentArtifacts, configure_matplotlib, resolve_input, set_working_directory  # noqa: E402
from theoretical_power_diagnostics import (  # noqa: E402
    DAYLIGHT_THRESHOLD_MW,
    INPUT_FILENAME,
    PhysicalParams,
    add_error_columns,
    add_theoretical_power,
    compute_model_metrics,
    load_station_data,
)


def plot_physical_components(df: pd.DataFrame) -> plt.Figure:
    daily = (
        df.set_index("Time")[["Geff", "transmission", "eta", "P_theo"]]
        .resample("D")
        .mean()
        .dropna()
    )
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), constrained_layout=True)
    axes = axes.ravel()

    axes[0].plot(daily.index, daily["Geff"], color="#1f77b4")
    axes[0].set_title("等效辐照度")
    axes[0].set_ylabel("W/m²")

    axes[1].plot(daily.index, daily["transmission"], color="#2ca02c")
    axes[1].set_title("大气透射率对照量")
    axes[1].set_ylabel("比值")

    axes[2].plot(daily.index, daily["eta"], color="#ff7f0e")
    axes[2].set_title("组件效率")
    axes[2].set_ylabel("效率")
    axes[2].set_xlabel("日期")

    axes[3].plot(daily.index, daily["P_theo"], color="#d62728")
    axes[3].set_title("理论功率")
    axes[3].set_ylabel("MW")
    axes[3].set_xlabel("日期")
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.tick_params(axis="x", rotation=25)
    return fig


def plot_calculation_scatter(df: pd.DataFrame) -> plt.Figure:
    daylight = df[df["P_theo"] > DAYLIGHT_THRESHOLD_MW]
    fig, ax = plt.subplots(figsize=(5.8, 5.8))
    ax.scatter(daylight["Power_actual"], daylight["P_theo"], s=8, alpha=0.22, edgecolors="none")
    limit = max(float(daylight["Power_actual"].max()), float(daylight["P_theo"].max()))
    ax.plot([0, limit], [0, limit], linestyle="--", color="#333333", label="1:1 参考线")
    ax.set_xlim(0, limit * 1.03)
    ax.set_ylim(0, limit * 1.03)
    ax.set_title("理论功率计算值与实测值")
    ax.set_xlabel("实测功率 / MW")
    ax.set_ylabel("理论功率 / MW")
    ax.legend()
    fig.tight_layout()
    return fig


def main() -> int:
    set_working_directory(__file__)
    font = configure_matplotlib()
    params = PhysicalParams()
    artifacts = ExperimentArtifacts(__file__)

    input_path = resolve_input(INPUT_FILENAME, __file__)
    df, dropped_rows = load_station_data(input_path)
    result = add_error_columns(add_theoretical_power(df, params))
    metrics = pd.DataFrame(
        [
            compute_model_metrics(
                result,
                "P_theo",
                "Measured-irradiance theoretical power",
                params,
                DAYLIGHT_THRESHOLD_MW,
            ),
            compute_model_metrics(
                result,
                "P_theo_atmospheric",
                "Legacy atmospheric-transmission variant",
                params,
                DAYLIGHT_THRESHOLD_MW,
            ),
        ]
    )

    output_columns = [
        "Time",
        "Power",
        "Power_actual",
        "P_theo",
        "P_theo_atmospheric",
        "Error_MW",
        "Rel_Error",
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
        "problem1_calculation_theoretical_power_components.csv",
        result[output_columns],
        index=False,
    )
    artifacts.write_csv("metrics", "problem1_calculation_error_metrics.csv", metrics, index=False)
    artifacts.save_figure("problem1_calculation_physical_components.png", plot_physical_components(result))
    artifacts.save_figure("problem1_calculation_actual_vs_theoretical.png", plot_calculation_scatter(result))
    artifacts.write_summary(
        {
            "input_file": str(input_path),
            "rows": int(len(result)),
            "dropped_rows": int(dropped_rows),
            "font": font,
            "daylight_threshold_mw": DAYLIGHT_THRESHOLD_MW,
            "metrics": metrics.to_dict(orient="records"),
        }
    )

    primary = metrics.iloc[0]
    print("问题1完整理论功率计算完成")
    print(
        f"RMSE={primary['RMSE_MW']:.3f} MW, "
        f"MAE={primary['MAE_MW']:.3f} MW, "
        f"相关系数={primary['Correlation']:.3f}"
    )
    print(f"输出目录: {artifacts.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
