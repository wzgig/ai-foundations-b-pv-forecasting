# -*- coding: utf-8 -*-
"""
Created on 2025/5/25 20:56

@author: Prince
"""
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = next(
    parent / "_shared" for parent in (SCRIPT_DIR, *SCRIPT_DIR.parents)
    if (parent / "_shared").exists()
)
sys.path.insert(0, str(SHARED_DIR))

from pv_project import configure_matplotlib, resolve_input, set_working_directory  # noqa: E402

set_working_directory(__file__)
configure_matplotlib(dpi=300)

df = pd.read_csv(resolve_input("问题3三模型预测结果对比表.csv", __file__))
df['起报时间'] = pd.to_datetime(df['起报时间'])
df['预报时间'] = pd.to_datetime(df['预报时间'])
target_date = pd.Timestamp("2019-02-22")
mask = df['起报时间'].dt.normalize() == target_date
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
plt.savefig(SCRIPT_DIR / "三模型绘图.png", bbox_inches='tight', pad_inches=0.0, dpi=300)
plt.close()
