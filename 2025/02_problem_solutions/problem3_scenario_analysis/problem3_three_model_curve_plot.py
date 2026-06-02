# -*- coding: utf-8 -*-
"""
Created on 2025/5/25 20:56

@author: Prince
"""
import sys
from pathlib import Path

import pandas as pd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import mean_squared_error

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared" for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
    if (parent / "_shared").exists()
)
sys.path.insert(0, str(SHARED_DIR))

from pv_project import (  # noqa: E402
    ExperimentArtifacts,
    apply_journal_axes,
    configure_matplotlib,
    journal_palette,
    resolve_input,
    set_working_directory,
)

set_working_directory(__file__)
configure_matplotlib(dpi=300)
ARTIFACTS = ExperimentArtifacts(__file__)
PALETTE = journal_palette(6)


standardized_prediction = SCRIPT_DIR / "outputs" / "predictions" / "3三模型预测结果对比表.csv"
if standardized_prediction.exists():
    df = pd.read_csv(standardized_prediction)
else:
    df = pd.read_csv(resolve_input("问题3三模型预测结果对比表.csv", __file__))

df['起报时间'] = pd.to_datetime(df['起报时间'])
df['预报时间'] = pd.to_datetime(df['预报时间'])
target_date = pd.Timestamp("2019-02-22")
df.columns = [col.replace(" (MW)", "").strip() for col in df.columns]
mask = df['预报时间'].dt.normalize() == target_date
filtered_df = df[mask]
filtered_day = filtered_df.sort_values("预报时间").copy()
if filtered_day.empty:
    raise ValueError(f"未找到目标日 {target_date.date()} 的问题3三模型预测记录。")

model_columns = ["PureLSTM预测功率", "FusionModel预测功率", "BiFusionModel预测功率"]
missing_columns = [column for column in ["实际功率", *model_columns] if column not in filtered_day.columns]
if missing_columns:
    raise ValueError(f"预测对比表缺少必要列：{missing_columns}")

daylight_mask = filtered_day["实际功率"] > 0.05
if not daylight_mask.any():
    raise ValueError(f"目标日 {target_date.date()} 白昼样本为空，无法计算白昼 RMSE。")

metric_lines = []
rmse_by_model = {}
for column in model_columns:
    rmse = np.sqrt(
        mean_squared_error(
            filtered_day.loc[daylight_mask, "实际功率"],
            filtered_day.loc[daylight_mask, column],
        )
    )
    model_name = column.replace("预测功率", "")
    rmse_by_model[model_name] = float(rmse)
    metric_lines.append(f"{model_name}: {rmse:.2f} MW")

fig, ax = plt.subplots(figsize=(9.6, 4.8))
for idx, column in enumerate(model_columns):
    ax.plot(
        filtered_day["预报时间"],
        filtered_day[column],
        label=column.replace("预测功率", "预测"),
        color=PALETTE[idx + 1],
        linewidth=1.9,
    )
ax.plot(
    filtered_day["预报时间"],
    filtered_day["实际功率"],
    label="实测功率",
    linestyle="--",
    linewidth=2.2,
    color="#222222",
)
ax.text(
    0.02,
    0.95,
    "白昼RMSE\n" + "\n".join(metric_lines),
    transform=ax.transAxes,
    va="top",
    fontsize=9,
    bbox=dict(facecolor="white", edgecolor="#bdbdbd", linewidth=0.6, alpha=0.92),
)
ax.set_title("问题3三模型每日预测对比（目标日：2019-02-22）")
ax.set_xlabel("日内时刻")
ax.set_ylabel("功率/MW")
ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
ax.set_xlim(filtered_day["预报时间"].iloc[0], filtered_day["预报时间"].iloc[-1])
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4)
apply_journal_axes(ax)
fig.tight_layout()
ARTIFACTS.save_figure("三模型绘图.png", fig=fig)
ARTIFACTS.write_csv("predictions", "problem3_three_model_curve_2019-02-22.csv", filtered_day, index=False)
ARTIFACTS.write_summary(
    {
        "target_date": str(target_date.date()),
        "rows": int(len(filtered_day)),
        "daylight_points": int(daylight_mask.sum()),
        "daylight_rmse_mw": rmse_by_model,
        "figure_style": "Chinese journal",
    },
    filename="problem3_three_model_curve_plot_summary.json",
)
