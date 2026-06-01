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

运行某个实验时，优先进入对应目录，例如：

```powershell
cd 2025\02_problem_solutions\problem2_baseline_forecasting
python .\7添加绘图与输出三个指标的对比表格.py
```

## 代码维护说明

2026-06-01 已完成第一轮代码工程化优化：新增公共路径解析、中文绘图配置、随机种子设置、训练集归一化工具、MATLAB 数据定位函数和项目健康检查。后续如果继续重构，建议优先把重复的 PyTorch 模型定义和训练循环抽取为统一模块。
