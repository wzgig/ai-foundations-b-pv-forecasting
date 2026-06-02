# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
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
    safe_qcut,
    set_working_directory,
)

set_working_directory(__file__)
configure_matplotlib(dpi=300)
ARTIFACTS = ExperimentArtifacts(__file__)
PALETTE = journal_palette(8)


def prediction_input_path(problem: str) -> Path:
    if problem == "problem2":
        standardized = (
            SCRIPT_DIR.parent
            / "problem2_baseline_forecasting"
            / "outputs"
            / "predictions"
            / "三模型预测结果对比表.csv"
        )
        legacy_name = "问题2三模型预测结果对比表.csv"
    elif problem == "problem3":
        standardized = SCRIPT_DIR / "outputs" / "predictions" / "3三模型预测结果对比表.csv"
        legacy_name = "问题3三模型预测结果对比表.csv"
    else:
        raise ValueError(f"unknown problem: {problem}")

    if standardized.exists():
        return standardized
    return resolve_input(legacy_name, __file__)


def clean_prediction_columns(cols):
    return [col.replace(" (MW)", "").replace("预测功率", "").strip() for col in cols]


# ---------- 1. 数据读取 ----------
df_station = pd.read_csv(resolve_input("station00.csv", __file__), parse_dates=["date_time"])
df_q2 = pd.read_csv(prediction_input_path("problem2"), parse_dates=["起报时间", "预报时间"])
df_q3 = pd.read_csv(prediction_input_path("problem3"), parse_dates=["起报时间", "预报时间"])

# ---------- 2. 清洗与合并 ----------
# 清理列名
df_q2.columns = clean_prediction_columns(df_q2.columns)
df_q3.columns = clean_prediction_columns(df_q3.columns)
df_q2.rename(columns={"实际功率": "actual"}, inplace=True)
df_q3.rename(columns={"实际功率": "actual"}, inplace=True)

# 只保留FusionModel预测结果
df_q2_fusion = df_q2[["起报时间", "预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "fusion_q2"})
df_q3_fusion = df_q3[["起报时间", "预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "fusion_q3"})

# 去重后合并
df_q2_fusion = df_q2_fusion.drop_duplicates(subset=["起报时间", "预报时间"])
df_q3_fusion = df_q3_fusion.drop_duplicates(subset=["起报时间", "预报时间"])
df_fusion_compare = pd.merge(df_q2_fusion, df_q3_fusion, on=["起报时间", "预报时间"], suffixes=("_q2", "_q3"))
df_fusion_compare["目标日期"] = df_fusion_compare["预报时间"].dt.normalize()

# ---------- 3. 每日RMSE计算 ----------
daily_rows = []
for target_date, group in df_fusion_compare.groupby("目标日期", observed=True):
    daily_rows.append({
        "目标日期": target_date,
        "起报时间": group["起报时间"].min(),
        "RMSE_Fusion_q2": np.sqrt(mean_squared_error(group["actual_q2"], group["fusion_q2"])),
        "RMSE_Fusion_q3": np.sqrt(mean_squared_error(group["actual_q3"], group["fusion_q3"])),
    })
daily_rmse = pd.DataFrame(daily_rows)
daily_rmse["提升值_RMSE"] = daily_rmse["RMSE_Fusion_q2"] - daily_rmse["RMSE_Fusion_q3"]

# ---------- 4. 每日天气指标构建 ----------
df_station["date"] = df_station["date_time"].dt.date
daily_weather = df_station.groupby("date", observed=True).agg({
    "nwp_globalirrad": ["mean", "std", lambda x: x.max() - x.min()],
    "nwp_temperature": "mean",
    "nwp_humidity": "mean",
    "nwp_windspeed": "mean"
})
daily_weather.columns = [
    "avg_globalirrad", "std_globalirrad", "amp_globalirrad",
    "mean_temperature", "mean_humidity", "mean_windspeed"
]
daily_weather = daily_weather.reset_index()
daily_weather["date"] = pd.to_datetime(daily_weather["date"])
daily_weather["season"] = daily_weather["date"].dt.month.map(
    lambda m: ("spring", "summer", "autumn", "winter")[(m // 3) % 4]
)
daily_weather["cloud_factor"] = daily_weather["std_globalirrad"] / (daily_weather["avg_globalirrad"] + 1e-6)

# ---------- 5. 合并数据集 ----------
df = pd.merge(daily_rmse, daily_weather, left_on="目标日期", right_on="date", how="inner")

# ---------- 6. 构造分组标签 ----------
def create_bins(data, col, q, labels):
    return safe_qcut(data[col], q=q, labels=labels)

df["天气类型"] = create_bins(df, "avg_globalirrad", 3, ["阴天", "多云", "晴天"])
df["光照波动性"] = create_bins(df, "std_globalirrad", 2, ["稳定", "不稳定"])
df["气温"] = create_bins(df, "mean_temperature", 2, ["低温", "高温"])
df["湿度"] = create_bins(df, "mean_humidity", 2, ["低湿", "高湿"])
df["风速"] = create_bins(df, "mean_windspeed", 2, ["低风", "高风"])
df["季节"] = df["season"]

# ---------- 7. 分组统计 ----------
group_fields = ["天气类型", "光照波动性", "气温", "湿度", "风速", "季节"]
group_results = {}
for field in group_fields:
    gdf = df.groupby(field, observed=True)["提升值_RMSE"].agg(["mean", "std", "count"]).reset_index()
    gdf.columns = [field, "提升值均值", "标准差", "样本数"]
    group_results[field] = gdf

# ---------- 8. 绘图（中文期刊风格） ----------
fig, axs = plt.subplots(2, 3, figsize=(14, 8), dpi=600)
axs = axs.flatten()

for idx, (field, gdf) in enumerate(group_results.items()):
    ax = axs[idx]
    x = gdf[field].astype(str)
    y = gdf["提升值均值"]
    yerr = gdf["标准差"]

    sns.barplot(x=x, y=y, hue=x, ax=ax, palette=PALETTE[: len(x)], edgecolor="#222222", errorbar=None, legend=False)
    ax.errorbar(range(len(x)), y, yerr=yerr, fmt='none', ecolor="#222222", capsize=4, linewidth=1.0)
    ax.axhline(0, color="#222222", linewidth=0.8)

    for i, (_, row) in enumerate(gdf.iterrows()):
        label_y = row["提升值均值"] + 0.01 if row["提升值均值"] >= 0 else row["提升值均值"] - 0.01
        label_va = "bottom" if row["提升值均值"] >= 0 else "top"
        ax.text(i, label_y, f'n={row["样本数"]}', ha='center', va=label_va, fontsize=8)

    ax.set_title(field, fontsize=10, fontweight='bold')
    ax.set_xlabel("")
    ax.set_ylabel("RMSE提升值" if idx % 3 == 0 else "")
    ax.tick_params(axis='x', rotation=45)
    apply_journal_axes(ax)

fig.suptitle("不同气象场景对预测精度提升的影响", fontsize=12, fontweight='bold')
plt.tight_layout()
path = ARTIFACTS.save_figure("六类分组_IEEE风格.png", fig=fig)
print(f"图像保存为：{path}")

# ---------- 9. 结果保存 ----------
path = ARTIFACTS.write_csv("metrics", "场景划分提升分析结果.csv", df, index=False)
ARTIFACTS.write_summary(
    {
        "rows": int(len(df)),
        "group_fields": group_fields,
        "figure_style": "Chinese journal",
        "outputs_note": "Scenario grouping figure and RMSE improvement table are written under outputs/.",
    },
    filename="problem3_extended_scenario_analysis_summary.json",
)
print(f"分析数据已保存为：{path}")
