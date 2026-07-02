# 2025 光伏日前预测工程目录说明

本目录按工程工作流组织光伏电站日前预测材料，目标是让后续复现实验、继续改代码、查找结果和维护交付报告都有稳定入口。

## 目录总览

```text
2025/
├── 00_course_materials/
│   ├── 人工智能基础B_期末大作业布置通知.pdf
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
├── 05_delivery/
├── llm/
├── _shared/
│   ├── pv_project.py
│   └── matlab/
├── tools/
│   ├── project_health_check.py
│   ├── generate_csust_report.py
│   └── export_csust_report.ps1
├── app.py
├── software_launcher.py
├── start_software.vbs
├── run.bat
├── CODE_AUDIT.md
├── CODE_INDEX.md
├── README.md
├── requirements.txt
└── requirements-optional.txt
```

## 目录职责

### `00_course_materials/`

存放课程通知、原始业务目标和评价附件，只作为需求和背景资料，不放实验输出。

### `01_modeling_workspace/pvod_full_experiment/`

完整 PVOD 建模工作区，保留多站点数据、McClear 数据、模型脚本、预测结果、模型权重和过程文档。这里适合作为继续大规模实验的入口。

### `02_problem_solutions/`

按工程链路拆分的交付材料。

- `problem1_data_analysis/`：站点机理诊断、理论功率建模、物理量分析、MATLAB/Python 探索脚本、单站点 Excel 数据和 Python 诊断输出。
- `problem2_baseline_forecasting/`：历史功率基线预测、白昼指标、统一预测表和可视化图。
- `problem3_scenario_analysis/`：气象预报融合、运行场景归因、特征重要性、提升来源分析和典型场景图。
- `problem4_feature_ablation/`：局地校正融合，不同输入特征组合的严格日前预测对比、雷达图、热力图、指标图和运行摘要。

### `03_figures/`

集中保存跨链路复用或报告展示用的图像素材。

### `04_paper/final_submission/`

存放早期论文/竞赛论文素材，当前课程最终报告以 `05_delivery/项目主报告_终稿.*` 为准。

### `05_delivery/`

面向《人工智能基础B》最终提交的材料归档目录，包含作业要求提取、完成度复盘、课程主报告草稿、团队分工模板、功能性能稳定性测试表、演示视频脚本、网站使用指南和最终提交包清单。该目录保留为提交证据，不再作为网页中的独立展示页面。

### `llm/`

运行解读模块。默认会优先读取本机 Codex 配置文件 `~\.codex\config.toml` 与 `~\.codex\auth.json`，支持 Codex 当前的 Responses API 接入；若没有可用配置，则使用离线规则根据现有 `outputs/` 指标和运行摘要整理解释。配置 `PV_LLM_PROVIDER`、`PV_LLM_WIRE_API`、`PV_LLM_API_KEY`、`PV_LLM_MODEL` 和 `PV_LLM_BASE_URL` 后，可覆盖为其他远程或本地兼容 HTTP 接口。密钥只从本机配置或环境变量读取，不写入仓库。

### `_shared/`

公共工程工具：

- `pv_project.py`：Python 路径解析、中文期刊绘图配置、随机种子、训练集归一化、分箱、指标、CSV/JSON 写出、实验产物管理和 PyTorch checkpoint 工具。
- `matlab/resolve_project_input.m`：MATLAB 脚本的数据文件定位工具。
- `matlab/configure_journal_plot.m`、`matlab/project_output_path.m`、`matlab/save_project_figure.m`：MATLAB 期刊绘图和统一输出保存工具。

### `tools/`

维护脚本目录：

- `project_health_check.py`：静态检查 Python 语法、重复代码快照和相对输入文件是否能在项目内找到；不会执行训练。
- `generate_csust_report.py`：按长沙理工大学样张从终稿 Markdown 生成 Word 报告。
- `export_csust_report.ps1`：更新 Word 目录和页码、导出 PDF，并在可用时渲染检查页。

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

按开关方式运行或查看某条链路：

```powershell
python 2025\run_project.py --list
python 2025\run_project.py --run main --parallel
python 2025\run_project.py --show 1,4
```

启动交互展示界面。演示时优先双击无终端桌面启动器：

```powershell
.\2025\start_software.vbs
```

需要查看依赖安装或 Streamlit 详细输出时，再运行：

```powershell
.\2025\run.bat
```

或：

```powershell
python -m streamlit run 2025\app.py
```

不要直接运行 `python 2025\app.py`；该命令现在只会输出正确启动提示，避免 Streamlit bare mode 的 `missing ScriptRunContext` 警告刷屏。`software_launcher.py` 提供桌面窗口，可启动/打开浏览器软件界面、运行健康检查并停止后台服务。

展示界面包含工作台、运行结果、交付引用、代码与命令、运行解读和训练控制六个页面。交付引用页集中索引业务目标、评价附件、报告、运行摘要、指标表和核心脚本；训练控制页默认只查看已有输出或执行 dry-run，真正启动训练前需要显式勾选确认框，并提供后台日志、Epoch 进度、停止进程树和基于 checkpoint 的继续运行。根目录 `docs/index.html` 是 GitHub Pages 静态展示页，只展示项目摘要和核心结果；完整交互功能仍需本地运行 Streamlit 工作台。

运行单条链路脚本时，可以直接进入对应目录：

```powershell
cd 2025\02_problem_solutions\problem3_scenario_analysis
python .\problem3_scenario_ieee_analysis.py
```

模型训练脚本会在对应目录下的 `models/` 文件夹保存 checkpoint。核心预测链路会先检查已有 checkpoint；只有训练签名匹配时才直接加载。若想重新训练，在调用 `train_model` 时传入 `force_retrain=True`，也支持通过 `PV_FORCE_RETRAIN=1` 临时强制重训。

站点机理诊断脚本、核心预测脚本和运行场景归因脚本会把运行产物统一保存到当前脚本目录的 `outputs/` 下：`predictions/` 保存预测或理论功率明细，`metrics/` 保存指标表，`figures/` 保存静态 PNG 和交互式 HTML 图，`reports/` 保存运行摘要。气象预报融合主训练脚本保留 `run_summary.json`，二次分析脚本写入各自独立的 `problem3_*_summary.json`。这些脚本默认不弹出图窗，适合长时间运行后自动保留所有结果。

局地校正融合主脚本默认运行 `FusionModel` 的 `nwp`、`lmd`、`mixed` 三种输入评估。可用 `PV_Q4_MODES` 选择输入模式、`PV_Q4_MODELS` 选择模型、`PV_Q4_SAVE_RUN_DIAGNOSTICS=0` 临时跳过逐运行诊断图刷新。

`run_project.py` 是项目级总控入口：站点机理诊断、历史功率基线、气象预报融合和局地校正融合可并行运行；`3-analysis` 会读取历史功率基线与气象预报融合的预测结果，因此只有在依赖输出存在或同次运行了这两条链路后才会执行。

## 维护约定

- 新代码优先放到对应链路目录；跨链路复用逻辑放到 `_shared/`。
- 不再提交重复压缩包、IDE 配置、缓存文件和临时转换文档。
- 移动数据文件后，要同步运行 `python 2025\tools\project_health_check.py`。
- 重要结构调整或代码优化要继续追加到根目录 `PROJECT_LOG.md`。
