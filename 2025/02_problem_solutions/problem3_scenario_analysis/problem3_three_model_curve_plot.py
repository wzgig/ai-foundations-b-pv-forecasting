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

from pv_project import ExperimentArtifacts, configure_matplotlib, resolve_input, set_working_directory  # noqa: E402

set_working_directory(__file__)
configure_matplotlib(dpi=300)
ARTIFACTS = ExperimentArtifacts(__file__)

df = pd.read_csv(resolve_input("问题3三模型预测结果对比表.csv", __file__))
df['起报时间'] = pd.to_datetime(df['起报时间'])
df['预报时间'] = pd.to_datetime(df['预报时间'])
target_date = pd.Timestamp("2019-02-22")
mask = df['起报时间'].dt.normalize() == target_date
filtered_df = df[mask]
daytime_mask = (filtered_df['预报时间'].dt.hour >= 0) & (filtered_df['预报时间'].dt.hour < 24)
filtered_day = filtered_df[daytime_mask]

fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(filtered_day['预报时间'], filtered_day['PureLSTM预测功率 (MW)'], label='PureLSTM预测')
ax.plot(filtered_day['预报时间'], filtered_day['FusionModel预测功率 (MW)'], label='FusionModel预测')
ax.plot(filtered_day['预报时间'], filtered_day['BiFusionModel预测功率 (MW)'], label='BiFusionModel预测')
ax.plot(filtered_day['预报时间'], filtered_day['实际功率 (MW)'], label='真实功率', linestyle='--', linewidth=2.0, color='#222222')
ax.set_title("三模型每日预测对比（起报时间：2019-02-22）")
ax.set_xlabel("时间")
ax.set_ylabel("功率 / MW")
ax.legend(ncol=2)
fig.autofmt_xdate(rotation=25)
fig.tight_layout()
ARTIFACTS.save_figure("三模型绘图.png", fig=fig)
ARTIFACTS.write_csv("predictions", "problem3_three_model_curve_2019-02-22.csv", filtered_day, index=False)
ARTIFACTS.write_summary(
    {
        "target_date": str(target_date.date()),
        "rows": int(len(filtered_day)),
        "figure_style": "Chinese journal",
    }
)
