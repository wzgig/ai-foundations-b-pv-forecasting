
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import plot_tree

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
    safe_qcut,
    set_working_directory,
)

# 设置中文字体（替代Arial，防止缺字）
set_working_directory(__file__)
configure_matplotlib(dpi=300)
ARTIFACTS = ExperimentArtifacts(__file__)

# ---------- 1. 数据读取 ----------
df_station = pd.read_csv(resolve_input("station00.csv", __file__), parse_dates=["date_time"])
df_q2 = pd.read_csv(resolve_input("问题2三模型预测结果对比表.csv", __file__), parse_dates=["起报时间", "预报时间"])
df_q3 = pd.read_csv(resolve_input("问题3三模型预测结果对比表.csv", __file__), parse_dates=["起报时间", "预报时间"])

# ---------- 2. 数据清洗 ----------
clean_columns = lambda cols: [col.replace(" (MW)", "").replace("预测功率", "").strip() for col in cols]
df_q2.columns = clean_columns(df_q2.columns)
df_q3.columns = clean_columns(df_q3.columns)
df_q2.rename(columns={"实际功率": "actual"}, inplace=True)
df_q3.rename(columns={"实际功率": "actual"}, inplace=True)

# ---------- 3. 合并FusionModel结果 ----------
df_q2_fusion = df_q2[["起报时间", "预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "fusion_q2"})
df_q3_fusion = df_q3[["起报时间", "预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "fusion_q3"})
df_fusion_compare = pd.merge(df_q2_fusion, df_q3_fusion, on=["起报时间", "预报时间", "actual"])

# ---------- 4. 计算每日RMSE提升 ----------
daily_rows = []
for start_time, group in df_fusion_compare.groupby("起报时间", observed=True):
    daily_rows.append({
        "起报时间": start_time,
        "RMSE_Fusion_q2": np.sqrt(mean_squared_error(group["actual"], group["fusion_q2"])),
        "RMSE_Fusion_q3": np.sqrt(mean_squared_error(group["actual"], group["fusion_q3"])),
    })
daily_rmse = pd.DataFrame(daily_rows)
daily_rmse["提升值_RMSE"] = daily_rmse["RMSE_Fusion_q2"] - daily_rmse["RMSE_Fusion_q3"]

# ---------- 5. 提取每日气象指标 ----------
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

# ---------- 6. 合并分析数据 ----------
df = pd.merge(daily_rmse, daily_weather, left_on="起报时间", right_on="date", how="inner")
df = df.sort_values("起报时间").reset_index(drop=True)

# ---------- 7. 构建分组标签 ----------
def create_bins(data, col, q, labels):
    return safe_qcut(data[col], q=q, labels=labels)

df["天气类型"] = create_bins(df, "avg_globalirrad", 3, ["阴天", "多云", "晴天"])
df["光照波动性"] = create_bins(df, "std_globalirrad", 2, ["稳定", "不稳定"])
df["气温"] = create_bins(df, "mean_temperature", 2, ["低温", "高温"])
df["湿度"] = create_bins(df, "mean_humidity", 2, ["低湿", "高湿"])
df["风速"] = create_bins(df, "mean_windspeed", 2, ["低风", "高风"])
df["季节"] = df["season"]

# ---------- 8. 可视化：每类场景单独输出 ----------
group_fields = ["天气类型", "光照波动性", "气温", "湿度", "风速", "季节"]
for feature in group_fields:
    fig, ax = plt.subplots(figsize=(6, 4))
    stat = df.groupby(feature, observed=True)["提升值_RMSE"].agg(["mean", "std", "count"]).reset_index()
    sns.barplot(x=feature, y="mean", hue=feature, data=stat, palette="Set2", ax=ax, legend=False)
    ax.errorbar(x=range(len(stat)), y=stat["mean"], yerr=stat["std"], fmt='none', capsize=4, color='black')
    for i, row in stat.iterrows():
        ax.text(i, max(row["mean"] + row["std"] + 0.005, 0.01), f"n={row['count']}", ha='center', va='bottom', fontsize=9)
    ax.set_ylabel("RMSE提升值")
    ax.set_title(f"{feature}分组分析")
    plt.tight_layout()
    ARTIFACTS.save_figure(f"{feature}_分组分析图.png", fig=fig)

# ---------- 9. 策略推荐分类器 ----------
df["提升是否明显"] = (df["提升值_RMSE"] > 0.04).astype(int)
features = ["avg_globalirrad", "std_globalirrad", "mean_temperature", "mean_humidity", "mean_windspeed"]
X = df[features]
y = df["提升是否明显"]

clf = DecisionTreeClassifier(max_depth=3, random_state=0)
clf.fit(X, y)

# 可视化策略推荐树
plt.figure(figsize=(10, 6))
plot_tree(clf, feature_names=features, class_names=["否", "是"], filled=True)
plt.title("模型推荐策略决策树")
plt.tight_layout()
ARTIFACTS.save_figure("推荐策略_决策树.png")

# ---------- 10. 导出分析结果 ----------
ARTIFACTS.write_csv("metrics", "场景划分提升分析结果.csv", df, index=False)
ARTIFACTS.write_summary(
    {
        "rows": int(len(df)),
        "group_fields": group_fields,
        "classifier": "DecisionTreeClassifier(max_depth=3, random_state=0)",
        "figure_style": "Chinese journal",
    }
)
print("分析完成，图像和结果已导出。")
