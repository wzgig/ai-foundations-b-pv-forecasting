# 2025 课程大作业目录说明

本目录按工作流重新组织，目标是让后续修改、复现实验、查找结果和维护论文材料都有稳定入口。

## 目录总览

```text
2025/
├── 00_course_materials/
│   ├── A题：光伏电站发电功率日前预测问题.pdf
│   └── 附件1.pdf
├── 01_modeling_workspace/
│   └── pvod_full_experiment/
├── 02_problem_solutions/
│   ├── problem1_data_analysis/
│   ├── problem2_baseline_forecasting/
│   ├── problem3_scenario_analysis/
│   └── problem4_feature_ablation/
├── 03_figures/
│   ├── exploratory_analysis/
│   ├── paper_assets/
│   └── scenario_comparisons/
└── 04_paper/
    └── final_submission/
```

## 目录职责

### `00_course_materials/`

存放题面和课程附件。这里的文件只作为需求和背景资料，不放实验输出。

### `01_modeling_workspace/pvod_full_experiment/`

完整 PVOD 建模工作区，保留了多站点数据、McClear 数据、模型脚本、预测结果、模型权重和若干过程文档。

这个目录保持自包含：脚本通常按当前工作目录读取 `station00.csv`、`metadata.csv`、预测结果表等文件。复现实验时建议先进入该目录再运行脚本：

```powershell
cd 2025\01_modeling_workspace\pvod_full_experiment
python .\7添加绘图与输出三个指标的对比表格.py
python .\9问题3初步.py
python .\10问题4.py
```

### `02_problem_solutions/`

按题目拆分的交付材料。每个子目录保留对应问题的代码、输入数据、结果表、图表和简要文档。

- `problem1_data_analysis/`：问题 1 的数据读取、统计分析、MATLAB/Python 探索脚本和单站点数据。
- `problem2_baseline_forecasting/`：问题 2 的三模型预测、预测结果表、白昼指标和模型对比图。
- `problem3_scenario_analysis/`：问题 3 的场景划分、特征重要性、提升来源分析和补充绘图。
- `problem4_feature_ablation/`：问题 4 的不同输入特征组合对比、雷达图、热力图和指标图。

这些目录也按“自包含运行”处理。若要重跑某一问题，先进入对应问题目录，再运行其中的脚本。

### `03_figures/`

集中存放跨问题复用或论文展示用的图像素材。

- `exploratory_analysis/`：早期数据探索图和对应 MATLAB 绘图脚本。
- `paper_assets/`：论文或汇报中使用的流程图、LSTM 图和手工整理图像。
- `scenario_comparisons/`：典型优/弱场景对比图。

### `04_paper/final_submission/`

最终论文文件，包含 PDF 和可编辑 Word 文档。后续若继续改论文，应优先从这里开始。

## 维护约定

- 新的代码或结果优先放到对应问题目录；跨问题的完整实验放到 `01_modeling_workspace/`。
- 不再提交重复压缩包、临时转换文档、IDE 配置、缓存文件或只用于个人归档的文件。
- 若移动脚本旁边的数据文件，需要同步检查脚本中的相对路径。
- 重要结构调整应同步更新根目录 `PROJECT_LOG.md`。
