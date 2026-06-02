# 光伏电站发电功率日前预测

这是《人工智能基础B》课程大作业仓库，围绕 2025 年 A 题“光伏电站发电功率日前预测问题”整理代码、数据分析、模型实验、结果图表和最终论文。

## 项目概览

项目基于光伏电站历史功率、数值天气预报和相关气象数据，完成从数据理解、理论功率分析、日前预测建模、场景划分到输入特征消融的完整课程作业流程。

主要问题包括：

- 问题 1：光伏电站数据分析、理论功率建模和可视化。
- 问题 2：基于历史功率序列的日前功率预测和三模型对比。
- 问题 3：引入气象变量后的场景划分、误差来源分析和模型改进。
- 问题 4：比较不同输入特征组合下的预测效果。

## 目录结构

```text
.
├── 2025/
│   ├── 00_course_materials/       题面和课程附件
│   ├── 01_modeling_workspace/     完整 PVOD 建模实验工作区
│   ├── 02_problem_solutions/      问题 1-4 的代码、数据、结果和图表
│   ├── 03_figures/                探索图、论文素材图和场景对比图
│   ├── 04_paper/                  最终论文 PDF 与 Word 文件
│   ├── _shared/                   Python 与 MATLAB 公共工具
│   ├── tools/                     项目健康检查脚本
│   ├── CODE_AUDIT.md              代码审计与优化记录
│   ├── README.md                  2025 目录说明
│   └── requirements.txt           Python 依赖清单
├── tests/                         轻量级回归检查
└── PROJECT_LOG.md                 项目工作日志
```

## 技术栈

- Python：`numpy`、`pandas`、`matplotlib`、`seaborn`、`scikit-learn`、`scipy`、`torch`、`plotly`
- MATLAB：问题 1 理论功率建模和探索性绘图
- Office 文档：论文终稿、分问题说明和补充材料

## 复现与检查

安装 Python 依赖：

```powershell
pip install -r 2025\requirements.txt
```

运行项目健康检查：

```powershell
python 2025\tools\project_health_check.py
```

运行轻量级回归检查：

```powershell
python -m unittest discover -s tests -q
```

完整运行顺序、模型复用逻辑、输出目录和结果查看方式见 `2025/RUN_GUIDE.md`。每个代码文件的现用名称和用途见 `2025/CODE_INDEX.md`。

运行某个实验时，优先进入对应目录，例如：

```powershell
cd 2025\02_problem_solutions\problem2_baseline_forecasting
python .\problem2_baseline_three_model_forecast.py
```

## 代码维护说明

2026-06-01 已完成第一轮代码工程化优化：新增公共路径解析、中文绘图配置、随机种子设置、训练集归一化工具、MATLAB 数据定位函数和项目健康检查。

2026-06-02 已完成模型训练缓存专项优化：问题 2-4 的主训练脚本会按实验/模型保存独立 PyTorch checkpoint，并在训练前复用签名匹配的已有模型，避免每次修改绘图或分析代码都重新训练。需要强制重新训练时，可在 `train_model(..., force_retrain=True)` 中开启。

2026-06-02 已完成输出产物标准化：问题 2-4 的主训练脚本和 `01_modeling_workspace` 对应副本会把预测表、指标表、图片和运行摘要统一写入脚本目录下的 `outputs/predictions/`、`outputs/metrics/`、`outputs/figures/`、`outputs/reports/`，不再只弹出绘图窗口或把 CSV 散落在脚本目录。

2026-06-02 已完成问题 1 理论功率诊断优化：`theoretical_power_diagnostics.py` 会把理论功率时序、月统计、白昼误差指标、诊断图和运行摘要统一写入 `problem1_data_analysis/outputs/`，并保留原大气修正口径作为对照。

2026-06-02 已完成脚本语义化命名：将早期的数字编号、临时中文名脚本统一改为按问题和功能命名，例如 `problem2_baseline_three_model_forecast.py`、`problem3_weather_feature_forecast.py`、`problem4_feature_ablation_forecast.py` 和 `theoretical_power_diagnostics.py`。

后续如果继续重构，建议优先把重复的 PyTorch 模型定义和训练循环抽取为统一模块。
