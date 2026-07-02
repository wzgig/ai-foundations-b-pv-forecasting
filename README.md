# 光伏电站日前功率预测与运行工作台

这是一个面向光伏电站日前发电计划的运行型预测仓库，围绕站点历史功率、数值天气预报和局地气象数据组织数据契约、模型训练、指标评估、运行档案和本地工作台。

## 项目概览

项目基于光伏电站历史功率、数值天气预报和相关气象数据，完成从站点机理诊断、日前预测建模、天气场景归因到多源气象输入评估的完整工程链路。系统默认读取已有运行产物，支持在本地工作台中查看指标、图表、代码入口、质量门禁和受控训练状态。

工程化运行画像见 `2025/ENGINEERING_PROFILE.md`。原始需求约束、报告归档、测试记录和演示脚本保留在 `2025/05_delivery/`，作为可追溯材料，不作为公开页和工作台的主叙事。

主要工程链路包括：

- 站点机理诊断：分析理论功率、发电特性和可视化诊断图。
- 历史功率基线：基于历史功率序列进行日前预测和三模型对比。
- 气象预报融合：引入 NWP 气象变量，分析天气场景和误差来源。
- 局地校正融合：比较 NWP、LMD 与 mixed 输入组合的预测收益。

## 目录结构

```text
.
├── AGENTS.md                     项目级代理协作规则
├── 2025/
│   ├── 00_course_materials/       需求原件和评价附件
│   ├── 01_modeling_workspace/     完整 PVOD 建模实验工作区
│   ├── 02_problem_solutions/      各条工程链路的代码、数据、结果和图表
│   ├── 03_figures/                探索图、论文素材图和场景对比图
│   ├── 04_paper/                  历史论文素材
│   ├── 05_delivery/               归档报告、测试记录和演示脚本
│   ├── llm/                       运行解读模块与可选语言接口
│   ├── _shared/                   Python 与 MATLAB 公共工具
│   ├── tools/                     健康检查、报告导出等维护脚本
│   ├── ENGINEERING_PROFILE.md     工程化运行画像
│   ├── app.py                     Streamlit 预测工作台
│   ├── software_launcher.py       Windows 桌面启动器
│   ├── start_software.vbs         无终端双击启动入口
│   ├── run.bat                    Windows 一键启动脚本
│   ├── CODE_AUDIT.md              代码审计与优化记录
│   ├── ASSIGNMENT_REQUIREMENTS_ANALYSIS.md  原始需求约束分析
│   ├── README.md                  2025 目录说明
│   ├── requirements.txt           Python 运行依赖清单
│   └── requirements-optional.txt  可选实验依赖清单
├── .streamlit/                    项目级 Streamlit 主题配置
├── docs/                          GitHub Pages 静态展示页
├── tests/                         轻量级回归检查
└── PROJECT_LOG.md                 项目工作日志
```

## 技术栈

- Python：`numpy`、`pandas`、`matplotlib`、`seaborn`、`scikit-learn`、`scipy`、`torch`、`plotly`、`streamlit`
- MATLAB：理论功率建模和探索性绘图
- Office 文档：技术报告、链路说明和归档材料

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

使用总控入口选择运行或查看某条链路：

```powershell
python 2025\run_project.py --list
python 2025\run_project.py --run 2,3,4 --parallel
python 2025\run_project.py --show 4
```

启动本地预测软件控制台。演示时优先双击无终端桌面启动器：

```powershell
2025\start_software.vbs
```

需要查看详细命令行输出或排查依赖时，再运行：

```powershell
2025\run.bat
```

也可以直接运行：

```powershell
python -m streamlit run 2025\app.py
```

不要直接运行 `python 2025\app.py`；该命令只会输出正确启动提示。界面包含工作台、运行结果、工程档案、代码与命令、运行解读和训练控制页面。训练控制页支持后台运行、Epoch 进度日志、停止进程树和基于 checkpoint 的继续运行。运行解读模块默认离线可用，也可读取本机 Codex 配置文件 `~\.codex\config.toml` 与 `~\.codex\auth.json`，或通过 `PV_LLM_*` 环境变量覆盖；密钥不会写入仓库。`software_launcher.py` 负责以桌面窗口方式启动/打开控制台、运行健康检查和停止后台服务。

GitHub Pages 静态展示页位于 `docs/index.html`。Pages 只展示项目摘要、核心指标、图表和本地运行方式；完整 Streamlit 工作台需要本地运行。

完整运行顺序、模型复用逻辑、输出目录和结果查看方式见 `2025/RUN_GUIDE.md`。每个代码文件的现用名称和用途见 `2025/CODE_INDEX.md`。

项目级协作规则见 `AGENTS.md`；后续重要改动应同步写入 `PROJECT_LOG.md`，推送 GitHub 前运行轻量验证并在提交备注中说明结果。

运行某个实验时，优先进入对应目录，例如：

```powershell
cd 2025\02_problem_solutions\problem2_baseline_forecasting
python .\problem2_baseline_three_model_forecast.py
```

## 代码维护说明

2026-06-01 已完成第一轮代码工程化优化：新增公共路径解析、中文绘图配置、随机种子设置、训练集归一化工具、MATLAB 数据定位函数和项目健康检查。

2026-06-02 已完成模型训练缓存专项优化：核心预测链路会按实验/模型保存独立 PyTorch checkpoint，并在训练前复用签名匹配的已有模型，避免每次修改绘图或分析代码都重新训练。需要强制重新训练时，可在 `train_model(..., force_retrain=True)` 中开启。

2026-06-02 已完成输出产物标准化：核心预测脚本和 `01_modeling_workspace` 对应副本会把预测表、指标表、图片和运行摘要统一写入脚本目录下的 `outputs/predictions/`、`outputs/metrics/`、`outputs/figures/`、`outputs/reports/`，不再只弹出绘图窗口或把 CSV 散落在脚本目录。

2026-06-02 已完成站点理论功率诊断优化：`theoretical_power_diagnostics.py` 会把理论功率时序、月统计、白昼误差指标、诊断图和运行摘要统一写入 `problem1_data_analysis/outputs/`，并保留原大气修正口径作为对照。

2026-06-02 已完成气象预报融合链路优化：`problem3_weather_feature_forecast.py` 改为以前一日实测功率和目标日 NWP 气象序列预测目标日 96 点功率，修正预测表时间对齐、PyTorch DLL 运行库兜底、checkpoint 复用、中文期刊风格图和二次分析脚本的目标日场景合并。

2026-06-02 已完成局地校正融合链路优化：`problem4_feature_ablation_forecast.py` 改为严格日前口径，比较 NWP、LMD 与 NWP+LMD 三类输入，支持 `PV_Q4_MODES`、`PV_Q4_MODELS` 和 `PV_Q4_SAVE_RUN_DIAGNOSTICS`，当前默认结果中 `FusionModel_mixed` 综合表现最好。

2026-06-03 已新增项目总控入口：`2025/run_project.py` 支持用 `--run` 选择工程链路、用 `--parallel` 并行运行互不依赖主任务、用 `--show` 查看已有输出；运行场景归因会显式检查历史功率基线和气象预报融合预测表依赖。

2026-06-03 已新增工程展示层：`2025/app.py` 提供 Streamlit 预测工作台，后续已升级为带真实预测图首屏、结果摘要、工程档案索引和受控运行页的软件界面；`2025/llm/` 提供离线优先且支持本机 Codex 配置、Responses API 与兼容 HTTP 接口的运行解读能力，`2025/start_software.vbs` 和 `2025/software_launcher.py` 提供无终端桌面启动入口，`2025/run.bat` 保留为命令行调试启动脚本，`requirements.txt` 改为固定版本运行依赖。

2026-06-02 已完成输出模块和中文期刊绘图规范整理：正式链路脚本统一使用 `outputs/` 目录和 `run_summary.json`，共享绘图配置改为中文字体兜底、600 dpi 保存、弱网格、统一配色和期刊式坐标轴；MATLAB 增加对应的输出与绘图 helper。

2026-06-02 已完成脚本语义化命名：将早期的数字编号、临时中文名脚本统一改为按功能命名，例如 `problem2_baseline_three_model_forecast.py`、`problem3_weather_feature_forecast.py`、`problem4_feature_ablation_forecast.py` 和 `theoretical_power_diagnostics.py`。

后续如果继续重构，建议优先把重复的 PyTorch 模型定义和训练循环抽取为统一模块。
