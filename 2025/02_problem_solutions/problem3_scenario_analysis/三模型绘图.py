# -*- coding: utf-8 -*-
"""
Created on 2025/5/25 20:56

@author: Prince
"""
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文支持字体
plt.rcParams['axes.unicode_minus'] = False   # 修复负号显示问题

df = pd.read_csv("三模型预测结果对比表.csv")
df['预报时间'] = pd.to_datetime(df['预报时间'])
mask = df['起报时间'] == "2019/2/22"
filtered_df = df[mask]
daytime_mask = (filtered_df['预报时间'].dt.hour >= 0) & (filtered_df['预报时间'].dt.hour < 24)
filtered_day = filtered_df[daytime_mask]

plt.figure(figsize=(12, 6))
plt.plot(filtered_day['预报时间'], filtered_day['PureLSTM预测功率 (MW)'], label='PureLSTM预测')
plt.plot(filtered_day['预报时间'], filtered_day['FusionModel预测功率 (MW)'], label='FusionModel预测')
plt.plot(filtered_day['预报时间'], filtered_day['BiFusionModel预测功率 (MW)'], label='BiFusionModel预测')
plt.plot(filtered_day['预报时间'], filtered_day['实际功率 (MW)'], label='真实功率', linestyle='--', linewidth=2, color='black')

# 设置坐标轴边框颜色为灰色
ax = plt.gca()
for spine in ax.spines.values():
    spine.set_color('lightgray')

plt.title("每日预测对比图（白昼） | 起报时间：2019-02-22")
plt.xlabel("时间")
plt.ylabel("功率 (MW)")
plt.legend()
plt.grid(True, color='lightgray')  # 可选：设置网格线颜色以匹配
plt.tight_layout()
plt.savefig("output.png", bbox_inches='tight', pad_inches=0.0, dpi=300)
plt.show()
