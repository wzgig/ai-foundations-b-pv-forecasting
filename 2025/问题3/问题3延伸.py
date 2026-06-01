# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_squared_error

# ---------- 1. 数据读取 ----------
df_station = pd.read_csv("station00.csv", parse_dates=["date_time"])
df_q2 = pd.read_csv("问题2三模型预测结果对比表.csv", parse_dates=["起报时间", "预报时间"])
df_q3 = pd.read_csv("问题3三模型预测结果对比表.csv", parse_dates=["起报时间", "预报时间"])

# ---------- 2. 清洗与合并 ----------
# 清理列名
clean_columns = lambda cols: [col.replace(" (MW)", "").replace("预测功率", "").strip() for col in cols]
df_q2.columns = clean_columns(df_q2.columns)
df_q3.columns = clean_columns(df_q3.columns)
df_q2.rename(columns={"实际功率": "actual"}, inplace=True)
df_q3.rename(columns={"实际功率": "actual"}, inplace=True)

# 只保留FusionModel预测结果
df_q2_fusion = df_q2[["起报时间", "预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "fusion_q2"})
df_q3_fusion = df_q3[["起报时间", "预报时间", "actual", "FusionModel"]].rename(columns={"FusionModel": "fusion_q3"})

# 去重后合并
df_q2_fusion = df_q2_fusion.drop_duplicates(subset=["起报时间", "预报时间"])
df_q3_fusion = df_q3_fusion.drop_duplicates(subset=["起报时间", "预报时间"])
df_fusion_compare = pd.merge(df_q2_fusion, df_q3_fusion, on=["起报时间", "预报时间"], suffixes=("_q2", "_q3"))

# ---------- 3. 每日RMSE计算 ----------
daily_rmse = (
    df_fusion_compare.groupby("起报时间", observed=True)
    .apply(lambda x: pd.Series({
        "RMSE_Fusion_q2": np.sqrt(mean_squared_error(x["actual_q2"], x["fusion_q2"])),
        "RMSE_Fusion_q3": np.sqrt(mean_squared_error(x["actual_q3"], x["fusion_q3"]))
    }), include_groups=False)
).reset_index()
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
df = pd.merge(daily_rmse, daily_weather, left_on="起报时间", right_on="date", how="inner")

# ---------- 6. 构造分组标签 ----------
def create_bins(data, col, q, labels):
    return pd.qcut(data[col], q=q, labels=labels, duplicates='drop')

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

# ---------- 8. 绘图（IEEE论文风格） ----------
plt.rcParams.update({
    'font.sans-serif': ['SimHei', 'Noto Sans CJK SC'],
    'axes.unicode_minus': False,
    'axes.edgecolor': 'black',
    'axes.linewidth': 1.2,
    'font.size': 10
})

fig, axs = plt.subplots(2, 3, figsize=(14, 8), dpi=600)
axs = axs.flatten()

for idx, (field, gdf) in enumerate(group_results.items()):
    ax = axs[idx]
    x = gdf[field].astype(str)
    y = gdf["提升值均值"]
    yerr = gdf["标准差"]

    sns.barplot(x=x, y=y, hue=x, ax=ax, palette="Blues", edgecolor="black", errorbar=None, legend=False)
    ax.errorbar(range(len(x)), y, yerr=yerr, fmt='none', ecolor='black', capsize=5)

    for i, (_, row) in enumerate(gdf.iterrows()):
        ax.text(i, row["提升值均值"] + 0.01, f'n={row["样本数"]}', ha='center', va='bottom', fontsize=8)

    ax.set_title(field, fontsize=10, fontweight='bold')
    ax.set_xlabel("")
    ax.set_ylabel("RMSE提升值" if idx % 3 == 0 else "")
    ax.tick_params(axis='x', rotation=45)

fig.suptitle("不同气象场景对预测精度提升的影响", fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig("六类分组_IEEE风格.png", bbox_inches='tight')
plt.close()
print("图像保存为：六类分组_IEEE风格.png")

# ---------- 9. 结果保存 ----------
df.to_csv("场景划分提升分析结果.csv", index=False, encoding="utf_8_sig")
print("分析数据已保存为：场景划分提升分析结果.csv")
