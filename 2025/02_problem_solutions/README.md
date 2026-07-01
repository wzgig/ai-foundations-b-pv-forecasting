# 02 正式工程链路

本目录是项目的正式可复现代码区，按工程链路拆分为四个子模块。课程报告、工作台和测试主要引用这里的输出。

| 子目录 | 作用 |
| --- | --- |
| `problem1_data_analysis/` | 站点机理诊断、理论功率计算、月度/典型日/误差分布分析。 |
| `problem2_baseline_forecasting/` | 仅基于历史功率的日前预测基线和三模型对比。 |
| `problem3_scenario_analysis/` | 融合目标日 NWP 的日前预测、天气场景归因和提升来源分析。 |
| `problem4_feature_ablation/` | 比较 NWP、LMD 与 mixed 输入，评估局地校正融合价值。 |

每个正式链路优先把结果写入本链路下的 `outputs/`：

- `outputs/predictions/`：预测表。
- `outputs/metrics/`：指标表。
- `outputs/figures/`：报告和工作台引用图。
- `outputs/reports/`：运行摘要 JSON。
- `models/`：模型权重或 checkpoint。

统一入口见 `../run_project.py`，完整命令见 `../RUN_GUIDE.md`。
