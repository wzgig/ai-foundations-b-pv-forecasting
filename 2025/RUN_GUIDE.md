# 2025 项目运行与结果查看指南

本文档用于实际运行本项目代码，说明推荐运行顺序、模型保存复用逻辑、输出文件位置，以及运行后如何查看和使用结果。

## 1. 总体原则

推荐把 `2025/02_problem_solutions/` 作为正式运行入口，把 `2025/01_modeling_workspace/pvod_full_experiment/` 作为历史建模工作区和实验副本。

优先运行正式入口：

```text
2025/02_problem_solutions/problem1_data_analysis/
2025/02_problem_solutions/problem2_baseline_forecasting/
2025/02_problem_solutions/problem3_scenario_analysis/
2025/02_problem_solutions/problem4_feature_ablation/
```

`01_modeling_workspace/pvod_full_experiment/` 中的历史功率基线、气象预报融合和局地校正融合同名脚本已经和正式入口同步，可以作为备用入口；其他编号脚本多为阶段性实验快照，不建议作为第一次完整复现的主线。

## 2. 运行前准备

从项目根目录打开 PowerShell：

```powershell
cd "d:\Qiuhua Wang\个人资料\电气\人工智能基础B\电气工程及其自动化+2307+202310080241+王子成+标题"
```

安装依赖：

```powershell
pip install -r 2025\requirements.txt
```

`requirements.txt` 是固定版本运行依赖。若要重跑早期工作区中的 SHAP、EMD 或 Optuna 实验，再额外安装：

```powershell
pip install -r 2025\requirements-optional.txt
```

先运行静态检查和轻量测试：

```powershell
python 2025\tools\project_health_check.py
python -m unittest discover -s tests -q
```

这两个命令不会训练模型。它们用于确认 Python 文件可解析、输入文件能找到、核心输出管理约束没有被破坏。

## 3. 本地交互展示入口

本项目新增了面向工程交付演示的 Streamlit 预测工作台。该界面默认读取已有 `outputs/`，展示工程链路结果、指标表、图像产物、本地代码入口和运行解读，不会自动触发长时间训练。为了避免演示时先出现黑色终端窗口，当前还提供了一个 Windows 桌面启动器。

Windows 演示推荐入口：

```powershell
2025\start_software.vbs
```

该脚本会通过 `pythonw` 打开 `software_launcher.py` 桌面窗口，由启动器在后台启动 Streamlit 服务并打开浏览器界面。启动器还能运行健康检查、重新打开浏览器和停止后台服务。

命令行调试入口：

```powershell
2025\run.bat
```

命令行启动：

```powershell
python -m streamlit run 2025\app.py
```

界面功能：

- 工作台：展示历史功率基线、气象预报融合和局地校正融合的最优模型、附件指标和软件入口状态。
- 运行结果：集中查看各链路 CSV 指标、PNG 图和 Plotly HTML 交互图。
- 交付引用：索引业务目标、评价附件、交付报告、运行摘要、指标表、核心代码入口和维护日志。
- 代码与命令：查看核心脚本/文档，执行 `--list`、`--show`、`--dry-run` 等安全命令，并可把当前代码片段加入运行解读上下文。
- 运行解读：默认读取本机 Codex 配置和密钥，支持 Responses API；无可用 API 时使用离线规则兜底。
- 运行控制：默认查看已有结果或 dry-run 预演；真正运行任务前必须勾选确认框。

不要直接运行 `python 2025\app.py`。该命令现在只输出正确启动提示，避免 Streamlit bare mode 下的 `missing ScriptRunContext` 警告刷屏。

运行解读接口配置优先级：

1. 若未显式设置 `PV_LLM_PROVIDER`，软件会自动读取本机 `~\.codex\config.toml` 和 `~\.codex\auth.json`。
2. 若设置 `PV_LLM_*` 环境变量，则优先使用环境变量。
3. 若远程调用失败，界面会自动使用离线规则兜底，保证演示不断。

当前 Codex 配置使用 Responses API 时，无需把密钥写入项目文件。可选远程或本地覆盖配置：

```powershell
$env:PV_LLM_PROVIDER="compatible-http"
$env:PV_LLM_WIRE_API="chat"
$env:PV_LLM_MODEL="your-model-name"
$env:PV_LLM_API_KEY="your-api-key"
$env:PV_LLM_BASE_URL="https://your-compatible-endpoint/v1/chat/completions"
python -m streamlit run 2025\app.py
```

若本地模型服务暴露兼容 `chat/completions` 的 HTTP 接口，可以改为：

```powershell
$env:PV_LLM_PROVIDER="local-codex"
$env:PV_LLM_WIRE_API="chat"
$env:PV_LLM_MODEL="your-local-model"
$env:PV_LLM_BASE_URL="http://127.0.0.1:8000/v1/chat/completions"
python -m streamlit run 2025\app.py
```

若使用 Responses API，则把 `PV_LLM_WIRE_API` 改为 `responses`，并将 `PV_LLM_BASE_URL` 指向 `/v1` 或 `/v1/responses`。不要把真实密钥写入 README、代码或 Git 跟踪文件。

GitHub Pages 静态展示页位于根目录 `docs/index.html`。Pages 只发布项目摘要、核心指标、静态图和本地运行命令；它不能运行 Streamlit，也不能替代本地预测工作台。

## 4. 总控入口与并行关系

如果只想用一个开关式入口运行或查看结果，可以使用：

```powershell
python 2025\run_project.py --list
python 2025\run_project.py --run 1
python 2025\run_project.py --run 2,3,4 --parallel
python 2025\run_project.py --show 4
```

任务关系如下：

| 任务 | 是否依赖其他任务 | 说明 |
| --- | --- | --- |
| `1` | 否 | 运行站点机理诊断的理论功率 Python 脚本。 |
| `2` | 否 | 运行历史功率基线三模型日前预测。 |
| `3` | 否 | 运行气象预报融合主脚本。 |
| `4` | 否 | 运行局地校正融合主脚本。 |
| `3-analysis` | 依赖 `2` 和 `3` 的预测表 | 执行运行场景归因、提升来源和典型曲线分析。 |

因此，`1`、`2`、`3`、`4` 可以同时运行；`3-analysis` 会在 `2` 和 `3` 完成后再运行。`main` 等价于 `1,2,3,4`，`all` 等价于 `1,2,3,4,3-analysis`。

常用控制参数：

```powershell
python 2025\run_project.py --run all --parallel --dry-run
python 2025\run_project.py --run 4 --q4-modes mixed --q4-fast
python 2025\run_project.py --run 2,3 --force-retrain --epochs 20
python 2025\run_project.py --show all --open-output
```

`--show` 只读取 `outputs/` 下已有摘要、指标和预测表路径，不触发训练。`--dry-run` 只打印运行计划，适合在正式长时间运行前确认依赖和并行批次。

## 5. 推荐完整运行顺序

### 步骤 1：站点机理诊断

站点机理诊断主要是数据理解、理论功率建模和探索性绘图。Python 脚本入口在：

```powershell
cd 2025\02_problem_solutions\problem1_data_analysis
python .\theoretical_power_baseline.py
python .\theoretical_power_calculation.py
python .\theoretical_power_diagnostics.py
```

三个 Python 脚本默认采用保存结果的批处理模式，不再弹出图窗阻塞运行。它们会把理论功率时序、指标、图像和运行摘要写入当前目录的 `outputs/`。其中 `theoretical_power_diagnostics.py` 的核心产物包括：

```text
outputs/predictions/problem1_theoretical_power_timeseries.csv
outputs/metrics/problem1_monthly_power_stats.csv
outputs/metrics/problem1_daylight_error_metrics.csv
outputs/metrics/problem1_relative_error_statistics.csv
outputs/figures/problem1_*.png
outputs/reports/run_summary.json
```

其中 `P_theo` 是推荐的实测辐照度理论功率口径；`P_theo_atmospheric` 保留原大气透射率修正口径，用于解释旧模型的系统性偏差。若要临时查看交互图窗，可运行：

```powershell
python .\theoretical_power_diagnostics.py --show
```

MATLAB 脚本如 `matlab_theoretical_power_solarposition.m`、`matlab_theoretical_power_manual_angles.m`、`matlab_theoretical_power_cleaned_plots.m`、`matlab_physical_model_residual_analysis.m` 等是同一链路下的物理建模和绘图补充。如果只复现 Python 深度学习主线，可以先跳过 MATLAB。

MATLAB 绘图脚本可复用 `_shared/matlab/` 下的 `configure_journal_plot.m`、`project_output_path.m` 和 `save_project_figure.m`。已整理的探索性导出脚本会把图像写到自身目录的 `outputs/figures/`。

### 步骤 2：历史功率基线

历史功率基线使用历史功率序列训练并比较 `PureLSTM`、`FusionModel`、`BiFusionModel` 三类模型。

```powershell
cd ..\problem2_baseline_forecasting
python .\problem2_baseline_three_model_forecast.py
```

首次运行会训练模型，耗时较长。后续运行会优先复用签名匹配的 checkpoint。预测表采用严格日前口径：`起报时间` 为输入日 00:00，`预报时间` 覆盖目标测试日 96 个 15 分钟点，`实际功率` 与模型预测使用同一目标日对齐。

如需临时缩短训练或强制重训，可在 PowerShell 中设置环境变量后运行：

```powershell
$env:PV_FORECAST_EPOCHS="10"
$env:PV_FORECAST_PATIENCE="3"
$env:PV_FORCE_RETRAIN="1"
python .\problem2_baseline_three_model_forecast.py
```

正式结果建议使用默认训练参数；只改绘图、表格或报告逻辑时不要设置 `PV_FORCE_RETRAIN`，这样会直接复用 checkpoint。

主要输出：

```text
models/
outputs/predictions/prediction_PureLSTM.csv
outputs/predictions/prediction_FusionModel.csv
outputs/predictions/prediction_BiFusionModel.csv
outputs/predictions/三模型预测结果对比表.csv
outputs/metrics/三模型白昼指标对比.csv
outputs/figures/*.png
outputs/figures/*.html
outputs/reports/run_summary.json
```

### 步骤 3：气象预报融合

气象预报融合在历史功率基线的建模框架上加入 NWP 等多维气象输入，用于比较气象变量对预测效果的提升。当前正式脚本采用严格日前口径：模型输入由“前一日实测功率曲线 + 目标日 NWP 气象序列”构成，预测输出为目标测试日 96 个 15 分钟功率点。

```powershell
cd ..\problem3_scenario_analysis
python .\problem3_weather_feature_forecast.py
```

气象预报融合主脚本也支持 `PV_FORECAST_EPOCHS`、`PV_FORECAST_PATIENCE`、`PV_FORECAST_BATCH_SIZE`、`PV_FORCE_RETRAIN` 等环境变量。默认训练参数为 `epochs=20`、`batch_size=128`、`patience=4`；后续复现会优先复用 `models/problem3_*.pth`。

主要输出：

```text
models/
outputs/predictions/3prediction_PureLSTM.csv
outputs/predictions/3prediction_FusionModel.csv
outputs/predictions/3prediction_BiFusionModel.csv
outputs/predictions/3三模型预测结果对比表.csv
outputs/metrics/三模型白昼指标对比.csv
outputs/figures/*.png
outputs/figures/*.html
outputs/reports/run_summary.json
outputs/reports/problem3_*_summary.json
```

其中 `run_summary.json` 由主训练脚本写入；场景划分、综合分析、IEEE 风格解释和典型日曲线脚本会写入独立的 `problem3_*_summary.json`，避免覆盖主训练摘要。

### 步骤 4：运行场景归因

这一步使用历史功率基线和气象预报融合的预测结果做二次分析，解释在不同气象场景下误差改善来自哪里。

推荐在确认历史功率基线、气象预报融合的预测结果已经生成后再运行：

```powershell
python .\problem3_scenario_ieee_analysis.py
python .\problem3_integrated_scenario_analysis.py
python .\problem3_extended_scenario_analysis.py
python .\problem3_three_model_curve_plot.py
```

注意：这些二次分析脚本是早期交付脚本，当前目录中保留了历史结果 CSV，因此即使没有重新训练也能运行。如果你要让它们严格使用刚刚重新训练得到的新结果，应先核对或同步下面两类表：

```text
历史功率基线新结果：
2025/02_problem_solutions/problem2_baseline_forecasting/outputs/predictions/三模型预测结果对比表.csv

气象预报融合新结果：
2025/02_problem_solutions/problem3_scenario_analysis/outputs/predictions/3三模型预测结果对比表.csv
```

这些二次分析脚本也统一写入 `problem3_scenario_analysis/outputs/`，包括场景分组图、特征重要性图、典型场景对比图、场景提升表和各自独立的 `problem3_*_summary.json`。如果只是查看本仓库已保存的交付结果，可以直接运行这些二次分析脚本；如果你要做新的严格实验记录，建议以 `outputs/` 下的新表为准。

### 步骤 5：局地校正融合

局地校正融合比较 `nwp`、`lmd`、`mixed` 三种输入配置下的模型表现。当前正式脚本采用严格日前口径：前一日实测 `power_scaled` 与目标日天气特征序列共同作为输入，预测目标日 96 个 15 分钟功率点；预测表中 `起报时间` 为目标日前一日 00:00，`预报时间` 覆盖目标日 00:00-23:45。

```powershell
cd ..\problem4_feature_ablation
python .\problem4_feature_ablation_forecast.py
```

当前脚本默认运行 `FusionModel`，并依次比较 `nwp`、`lmd`、`mixed`。如需临时筛选输入模式、模型或跳过逐运行诊断图刷新，可使用环境变量：

```powershell
$env:PV_Q4_MODES="nwp,lmd,mixed"
$env:PV_Q4_MODELS="FusionModel"
$env:PV_Q4_SAVE_RUN_DIAGNOSTICS="0"
python .\problem4_feature_ablation_forecast.py
```

`PV_Q4_MODES` 支持 `nwp`、`lmd`、`mixed` 或 `all`；`PV_Q4_MODELS` 支持 `PureLSTM`、`FusionModel`、`BiFusionModel` 或 `all`。局地校正融合同样支持 `PV_FORECAST_EPOCHS`、`PV_FORECAST_PATIENCE`、`PV_FORECAST_BATCH_SIZE`、`PV_FORECAST_HIDDEN_DIM` 和 `PV_FORCE_RETRAIN`。

主要输出：

```text
models/
outputs/predictions/Q4_pred_FusionModel_nwp.csv
outputs/predictions/Q4_pred_FusionModel_lmd.csv
outputs/predictions/Q4_pred_FusionModel_mixed.csv
outputs/metrics/Q4_模型输入对比结果.csv
outputs/figures/Q4_模型输入对比结果热力图.png
outputs/figures/*_输入对比雷达图.png
outputs/figures/*_指标对比_不同输入模式.png
outputs/figures/*_vs_输入特征维度.png
outputs/figures/*_daylight_forecast_curve.png
outputs/figures/*_error_analysis_matrix.png
outputs/figures/*_interactive_forecast_sample0.html
outputs/reports/run_summary.json
```

当前默认结果中，`FusionModel_mixed` 的综合表现最好：`E_rmse=0.0465`、`C_R=95.35%`、`Q_R=99.84%`。完整指标以 `outputs/metrics/Q4_模型输入对比结果.csv` 为准。

## 6. 模型保存与复用逻辑

历史功率基线、气象预报融合和局地校正融合的主训练脚本都使用相同的 checkpoint 逻辑：

1. 训练前先根据模型类、输入形状、训练集形状、训练轮数、学习率、早停参数等生成训练签名。
2. 在当前脚本目录的 `models/` 下查找对应 checkpoint。
3. 如果 checkpoint 存在且训练签名完全匹配，直接加载模型，跳过训练。
4. 如果 checkpoint 不存在或签名不匹配，重新训练并保存新的 checkpoint。
5. 如果想强制重训，可在对应脚本的 `train_model(...)` 调用中加入或改为 `force_retrain=True`；核心预测链路也支持通过环境变量 `PV_FORCE_RETRAIN=1` 临时强制重训。

这意味着：只改绘图、输出、结果分析代码时，正常情况下不会重新训练；只要模型结构、输入维度和训练参数不变，就会复用已保存模型。

常见 checkpoint 文件名示例：

```text
problem2_PureLSTM.pth
problem2_FusionModel.pth
problem2_BiFusionModel.pth
problem3_PureLSTM.pth
problem3_FusionModel.pth
problem3_BiFusionModel.pth
problem4_FusionModel_nwp.pth
problem4_FusionModel_lmd.pth
problem4_FusionModel_mixed.pth
```

## 7. 输出保存逻辑

正式链路脚本使用统一输出结构：

```text
outputs/
  predictions/   理论功率/预测明细和统一预测对比表
  metrics/       指标汇总表
  figures/       PNG 静态图和 HTML 交互图
  reports/       run_summary.json
```

`run_summary.json` 是每次运行结束后的产物索引。建议每次运行完先打开它，确认本次生成了哪些文件。

查看方式：

```powershell
Get-Content .\outputs\reports\run_summary.json
```

或列出所有输出：

```powershell
Get-ChildItem .\outputs -Recurse
```

## 8. 结果查看顺序

每条链路运行结束后，建议按下面顺序查看结果。

### 先看运行摘要

```text
outputs/reports/run_summary.json
```

重点看：

- `script`：本次运行的脚本。
- `metadata`：模型列表、样本规模、耗时。
- `artifacts`：所有输出文件清单。

### 再看指标表

站点机理诊断：

```text
outputs/metrics/problem1_daylight_error_metrics.csv
outputs/metrics/problem1_monthly_power_stats.csv
outputs/metrics/problem1_baseline_error_metrics.csv
outputs/metrics/problem1_calculation_error_metrics.csv
```

历史功率基线、气象预报融合：

```text
outputs/metrics/三模型白昼指标对比.csv
```

局地校正融合：

```text
outputs/metrics/Q4_模型输入对比结果.csv
```

核心指标含义：

- `RMSE`、`MAE`、`MAPE`：常规误差指标，越小越好。
- `E_rmse`、`E_mae`、`E_me`：按装机容量归一化后的附件指标。
- `r`：相关系数，越接近 1 越好。
- `C_R`、`Q_R`：评价附件中的考核指标，通常越高越好。

### 再看预测明细

站点机理诊断：

```text
outputs/predictions/problem1_theoretical_power_timeseries.csv
outputs/predictions/problem1_baseline_theoretical_power_timeseries.csv
outputs/predictions/problem1_calculation_theoretical_power_components.csv
```

历史功率基线：

```text
outputs/predictions/三模型预测结果对比表.csv
```

气象预报融合：

```text
outputs/predictions/3三模型预测结果对比表.csv
```

局地校正融合：

```text
outputs/predictions/Q4_pred_FusionModel_nwp.csv
outputs/predictions/Q4_pred_FusionModel_lmd.csv
outputs/predictions/Q4_pred_FusionModel_mixed.csv
```

这些表适合用 Excel 打开，检查某一天、某个 15 分钟时刻的实际功率和预测功率。

### 最后看图

静态图：

```text
outputs/figures/*.png
```

交互图：

```text
outputs/figures/*.html
```

HTML 图可以直接用浏览器打开，适合放大查看某一天的预测曲线。

## 9. 快速查看命令

查看某个问题所有输出：

```powershell
Get-ChildItem .\outputs -Recurse | Select-Object FullName
```

快速预览指标 CSV：

```powershell
Import-Csv ".\outputs\metrics\三模型白昼指标对比.csv" | Format-Table
```

打开输出目录：

```powershell
explorer .\outputs
```

打开图像目录：

```powershell
explorer .\outputs\figures
```

## 10. 推荐复现实验记录方式

每次正式运行后，建议记录：

```text
运行日期：
运行脚本：
是否复用 checkpoint：
关键指标表路径：
关键预测表路径：
关键图像路径：
备注：
```

本项目根目录已有 `PROJECT_LOG.md`，用于记录重要结构调整和代码维护；单次训练实验记录可以另建实验日志，也可以在论文整理时从 `outputs/reports/run_summary.json` 回溯。

## 11. 常见问题

### 运行很慢怎么办？

第一次训练慢是正常的。后续只要 checkpoint 签名匹配，会直接加载模型。可以先运行历史功率基线，确认输出结构没问题，再继续气象预报融合和局地校正融合。

### 我改了绘图代码，会重新训练吗？

一般不会。训练是否复用只看模型、输入和训练参数签名。只改绘图或输出逻辑通常会复用已有 checkpoint。

### 我想重新训练怎么办？

两种方式：

1. 在脚本调用 `train_model(...)` 时设置 `force_retrain=True`。
2. 删除对应 `models/*.pth` 后重新运行脚本。

推荐第一种，记录更清楚。

### 应该运行 `01_modeling_workspace` 还是 `02_problem_solutions`？

正式复现优先运行 `02_problem_solutions`。`01_modeling_workspace` 保留了更完整的建模过程和阶段性脚本，适合做实验探索，不适合作为第一次运行的主线。
