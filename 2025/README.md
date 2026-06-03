# 2025 课程大作业目录说明

本目录按工作流组织 2025 年《人工智能基础B》A 题材料，目标是让后续复现实验、继续改代码、查找结果和维护论文都有稳定入口。

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
├── 04_paper/
│   └── final_submission/
├── llm/
├── _shared/
│   ├── pv_project.py
│   └── matlab/
├── tools/
│   └── project_health_check.py
├── app.py
├── run.bat
├── CODE_AUDIT.md
├── CODE_INDEX.md
├── README.md
├── requirements.txt
└── requirements-optional.txt
```

## 目录职责

### `00_course_materials/`

存放题面和课程附件，只作为需求和背景资料，不放实验输出。

### `01_modeling_workspace/pvod_full_experiment/`

完整 PVOD 建模工作区，保留多站点数据、McClear 数据、模型脚本、预测结果、模型权重和过程文档。这里适合作为继续大规模实验的入口。

### `02_problem_solutions/`

按题目拆分的交付材料。

- `problem1_data_analysis/`：理论功率建模、物理量分析、MATLAB/Python 探索脚本、单站点 Excel 数据和 Python 诊断输出。
- `problem2_baseline_forecasting/`：三模型日前预测、白昼指标、统一预测表和可视化图。
- `problem3_scenario_analysis/`：气象场景划分、特征重要性、提升来源分析和典型场景图。
- `problem4_feature_ablation/`：不同输入特征组合的严格日前预测对比、雷达图、热力图、指标图和运行摘要。

### `03_figures/`

集中保存跨问题复用或论文展示用的图像素材。

### `04_paper/final_submission/`

最终论文 PDF 和可编辑 Word 文档。

### `llm/`

课程大作业的大模型辅助解读模块。默认不依赖外部 API，会根据现有 `outputs/` 指标和运行摘要生成离线解释；配置 `PV_LLM_PROVIDER`、`PV_LLM_API_KEY`、`PV_LLM_MODEL` 和 `PV_LLM_BASE_URL` 后，可切换到远程大模型接口。

### `_shared/`

公共工程工具：

- `pv_project.py`：Python 路径解析、中文期刊绘图配置、随机种子、训练集归一化、分箱、指标、CSV/JSON 写出、实验产物管理和 PyTorch checkpoint 工具。
- `matlab/resolve_project_input.m`：MATLAB 脚本的数据文件定位工具。
- `matlab/configure_journal_plot.m`、`matlab/project_output_path.m`、`matlab/save_project_figure.m`：MATLAB 期刊绘图和统一输出保存工具。

### `tools/`

`project_health_check.py` 会静态检查 Python 语法、重复代码快照和相对输入文件是否能在项目内找到。该脚本不会执行训练。

## 复现建议

完整运行顺序、保存逻辑和结果查看方式见 `RUN_GUIDE.md`。每个代码文件的现用名称和用途见 `CODE_INDEX.md`。

安装依赖：

```powershell
pip install -r 2025\requirements.txt
```

可选实验依赖仅在重跑 SHAP、EMD 或 Optuna 相关早期实验时安装：

```powershell
pip install -r 2025\requirements-optional.txt
```

运行健康检查：

```powershell
python 2025\tools\project_health_check.py
```

按开关方式运行或查看某一问：

```powershell
python 2025\run_project.py --list
python 2025\run_project.py --run main --parallel
python 2025\run_project.py --show 1,4
```

启动交互展示界面：

```powershell
.\2025\run.bat
```

或：

```powershell
python -m streamlit run 2025\app.py
```

运行单个问题脚本时，可以直接进入问题目录：

```powershell
cd 2025\02_problem_solutions\problem3_scenario_analysis
python .\problem3_scenario_ieee_analysis.py
```

模型训练脚本会在对应目录下的 `models/` 文件夹保存 checkpoint。问题 2-4 的主脚本会先检查已有 checkpoint；只有训练签名匹配时才直接加载。若想重新训练，在调用 `train_model` 时传入 `force_retrain=True`，问题 2-4 也支持通过 `PV_FORCE_RETRAIN=1` 临时强制重训。

问题 1 的理论功率脚本、问题 2-4 的主脚本和问题 3 二次分析脚本会把运行产物统一保存到当前脚本目录的 `outputs/` 下：`predictions/` 保存预测或理论功率明细，`metrics/` 保存指标表，`figures/` 保存静态 PNG 和交互式 HTML 图，`reports/` 保存运行摘要。问题 3 主训练脚本保留 `run_summary.json`，二次分析脚本写入各自独立的 `problem3_*_summary.json`。这些脚本默认不弹出图窗，适合长时间运行后自动保留所有结果。

问题 4 主脚本默认运行 `FusionModel` 的 `nwp`、`lmd`、`mixed` 三种输入消融。可用 `PV_Q4_MODES` 选择输入模式、`PV_Q4_MODELS` 选择模型、`PV_Q4_SAVE_RUN_DIAGNOSTICS=0` 临时跳过逐运行诊断图刷新。

`run_project.py` 是项目级总控入口：问题 1、2、3 主训练和问题 4 可并行运行；`3-analysis` 会读取问题 2 与问题 3 的预测结果，因此只有在依赖输出存在或同次运行了问题 2、3 后才会执行。

## 维护约定

- 新代码优先放到对应问题目录；跨问题复用逻辑放到 `_shared/`。
- 不再提交重复压缩包、IDE 配置、缓存文件和临时转换文档。
- 移动数据文件后，要同步运行 `python 2025\tools\project_health_check.py`。
- 重要结构调整或代码优化要继续追加到根目录 `PROJECT_LOG.md`。
