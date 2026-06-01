# 光伏电站发电功率日前预测

这是《人工智能基础B》课程大作业仓库，围绕 2025 年 A 题“光伏电站发电功率日前预测问题”整理代码、数据分析、模型实验、论文终稿、结果图表和必要数据。

## 项目概览

本项目以光伏电站历史功率和数值天气预报数据为基础，完成从数据理解、特征分析、模型预测到结果评估的完整课程作业流程。仓库内容覆盖四个主要问题：

- 问题 1：光伏电站数据分析、指标统计与可视化。
- 问题 2：基于历史功率序列的日前功率预测建模与评估。
- 问题 3：结合气象因素的场景划分、误差来源分析与模型改进。
- 问题 4：比较不同输入特征组合下的预测效果，并输出多模型指标对比。

## 目录结构

```text
.
├── 《人工智能基础B》期末大作业布置通知.pdf
└── 2025/
    ├── 00_course_materials/             # 题面和课程附件
    ├── 01_modeling_workspace/           # 完整 PVOD 建模工作区
    ├── 02_problem_solutions/            # 问题 1-4 的分问题代码、数据和结果
    ├── 03_figures/                      # 探索图、论文图和场景对比图
    ├── 04_paper/                        # 最终论文 PDF 与可编辑文档
    └── README.md                        # 2025 目录内的结构说明
```

## 技术栈

- Python：`pandas`、`numpy`、`matplotlib`、`seaborn`、`scikit-learn`、`PyTorch`
- MATLAB：数据分析、基础绘图和部分指标计算
- Office 文档：论文终稿、分问题说明和补充记录

## 主要产物

- 完整建模工作区：见 `2025/01_modeling_workspace/pvod_full_experiment/`
- 分问题材料：见 `2025/02_problem_solutions/`
- 可视化图表：见 `2025/03_figures/` 和各问题目录中的绘图结果
- 论文材料：见 `2025/04_paper/final_submission/`
- 工作记录：见根目录 `PROJECT_LOG.md`

## 复现实验

1. 进入对应问题目录，例如：

   ```powershell
   cd 2025\01_modeling_workspace\pvod_full_experiment
   ```

2. 安装常用依赖：

   ```powershell
   pip install numpy pandas matplotlib seaborn scikit-learn torch plotly openpyxl
   ```

3. 根据脚本中的相对路径运行对应问题代码，例如：

   ```powershell
   python .\7添加绘图与输出三个指标的对比表格.py
   python .\9问题3初步.py
   python .\10问题4.py
   ```

> [!NOTE]
> 部分脚本来自课程实验过程，文件编码、字体和本地路径可能需要按运行环境调整。中文图表建议安装 `SimHei` 或其他可用中文字体。

## 说明

本仓库用于课程学习、实验复现和作业材料归档。目录中保留了核心数据、可运行脚本、结果图表和最终论文；重复压缩包、外部参考资料原文、转换中间稿和个人归档文件已清理，方便后续维护和公开展示。
