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
print(f"分析数据已保存为：{path}")

# ---------- 10. 提升来源建模分析（线性回归 + 特征重要性） ----------
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score

# 选择特征列与目标列
features = [
    "avg_globalirrad", "std_globalirrad", "amp_globalirrad",
    "mean_temperature", "mean_humidity", "mean_windspeed", "cloud_factor"
]
target = "提升值_RMSE"

# 特征标准化
X = df[features].copy()
y = df[target].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------- 线性回归 ----------
linreg = LinearRegression()
linreg.fit(X_scaled, y)
coef_df = pd.DataFrame({
    "特征": features,
    "系数": linreg.coef_
}).sort_values(by="系数", key=abs, ascending=False)

# ---------- 随机森林 ----------
rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X, y)
rf_importance = pd.DataFrame({
    "特征": features,
    "重要性": rf.feature_importances_
}).sort_values(by="重要性", ascending=False)

# ---------- 可视化：特征影响图 ----------
fig, axs = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

# 线性回归系数图
sns.barplot(x="系数", y="特征", hue="特征", data=coef_df, palette=PALETTE[: len(coef_df)], ax=axs[0], legend=False, edgecolor="#222222")
axs[0].set_title("线性回归：提升值影响系数")
axs[0].axvline(0, color="#222222", linewidth=0.8)
axs[0].set_xlabel("标准化回归系数")
axs[0].set_ylabel("")
apply_journal_axes(axs[0])

# 随机森林特征重要性图
sns.barplot(x="重要性", y="特征", hue="特征", data=rf_importance, palette=PALETTE[: len(rf_importance)], ax=axs[1], legend=False, edgecolor="#222222")
axs[1].set_title("随机森林：特征重要性")
axs[1].set_xlabel("重要性")
axs[1].set_ylabel("")
apply_journal_axes(axs[1])

plt.tight_layout()
path = ARTIFACTS.save_figure("特征重要性分析.png", fig=fig)
print(f"图像保存为：{path}")

# ---------- 保存分析数据 ----------
ARTIFACTS.write_csv("metrics", "线性回归_提升来源分析.csv", coef_df, index=False)
ARTIFACTS.write_csv("metrics", "随机森林_特征重要性.csv", rf_importance, index=False)
print("回归分析结果保存完毕")


# ---------- 11. SHAP解释性分析 ----------
try:
    import shap
except ImportError:
    print("未安装 shap，已跳过 SHAP 解释性分析；如需生成解释图，请安装 requirements.txt 中的可选依赖。")
else:
    explainer = shap.Explainer(rf, X)
    shap_values = explainer(X)
    shap_dir = ARTIFACTS.directory("figures") / "shap_images"
    shap_dir.mkdir(exist_ok=True)

    plt.figure()
    shap.summary_plot(shap_values, features=X, feature_names=features, plot_type="bar", show=False)
    plt.tight_layout()
    ARTIFACTS.save_figure(Path("shap_images") / "shap_summary_bar.png")
    print("SHAP柱状图保存为：shap_images/shap_summary_bar.png")

    plt.figure()
    shap.summary_plot(shap_values, features=X, feature_names=features, show=False)
    plt.tight_layout()
    ARTIFACTS.save_figure(Path("shap_images") / "shap_summary_beeswarm.png")
    print("SHAP蜜蜂图保存为：shap_images/shap_summary_beeswarm.png")

    for i, feat in enumerate(features):
        plt.figure()
        shap.plots.scatter(shap_values[:, i], color=shap_values, show=False)
        plt.title(f"SHAP值 vs 特征: {feat}")
        plt.tight_layout()
        ARTIFACTS.save_figure(Path("shap_images") / f"shap_dependence_{feat}.png")
    print("SHAP依赖图已保存")

    shap_df = pd.DataFrame(shap_values.values, columns=features)
    shap_df["目标日期"] = df["目标日期"].values
    shap_df["起报时间"] = df["起报时间"].values
    ARTIFACTS.write_csv("metrics", "shap_每列贡献值.csv", shap_df, index=False)
    print("SHAP数值已保存为：shap_每列贡献值.csv")


# ---------- 12. 典型场景案例提取与验证图示 ----------

# 选出提升值最大的和最小的两天
top_case = df.sort_values("提升值_RMSE", ascending=False).iloc[0]
worst_case = df.sort_values("提升值_RMSE", ascending=True).iloc[0]

# 获取对应目标日期
top_date = top_case["目标日期"]
worst_date = worst_case["目标日期"]

# 打印场景标签信息
print(f"\n【典型优场景】{top_date}：")
print(f"天气类型={top_case['天气类型']}，光照波动性={top_case['光照波动性']}，季节={top_case['季节']}，提升值={top_case['提升值_RMSE']:.3f}")

print(f"\n【典型弱场景】{worst_date}：")
print(f"天气类型={worst_case['天气类型']}，光照波动性={worst_case['光照波动性']}，季节={worst_case['季节']}，提升值={worst_case['提升值_RMSE']:.3f}")

# 提取当天预测数据
def extract_day_curve(date):
    target_date = pd.to_datetime(date).normalize()
    df_day_q2 = df_q2[df_q2["预报时间"].dt.normalize() == target_date].copy()
    df_day_q3 = df_q3[df_q3["预报时间"].dt.normalize() == target_date].copy()
    df_day = pd.merge(
        df_day_q2[["预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "q2"}),
        df_day_q3[["预报时间", "FusionModel"]].rename(columns={"FusionModel": "q3"}),
        on="预报时间"
    )
    return df_day.sort_values("预报时间")

# 绘制时序图
def plot_day_curve(df_day, title, save_path):
    fig, ax = plt.subplots(figsize=(9.2, 4.2), dpi=300)
    ax.plot(df_day["预报时间"], df_day["actual"], label="实测功率", color="#222222", linewidth=2.0)
    ax.plot(df_day["预报时间"], df_day["q2"], label="问题2 FusionModel", linestyle="--", color=PALETTE[1], linewidth=1.8)
    ax.plot(df_day["预报时间"], df_day["q3"], label="问题3 FusionModel", linestyle="-.", color=PALETTE[2], linewidth=1.8)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    ax.set_xlabel("时间")
    ax.set_ylabel("功率/MW")
    ax.set_title(title, fontsize=12)
    ax.tick_params(axis="x", rotation=25)
    apply_journal_axes(ax)
    fig.tight_layout()
    path = ARTIFACTS.save_figure(save_path, fig=fig)
    print(f"图像保存为：{path}")

# 绘图
plot_day_curve(
    extract_day_curve(top_date),
    title=f"典型优场景（{top_date.date()}）",
    save_path="典型优场景对比图.png"
)

plot_day_curve(
    extract_day_curve(worst_date),
    title=f"典型弱场景（{worst_date.date()}）",
    save_path="典型弱场景对比图.png"
)
ARTIFACTS.write_summary(
    {
        "rows": int(len(df)),
        "group_fields": group_fields,
        "features": features,
        "top_case": str(top_date),
        "worst_case": str(worst_date),
        "figure_style": "Chinese journal",
    },
    filename="problem3_scenario_ieee_analysis_summary.json",
)
print("典型场景案例图示完成")
