# 代码文件索引

本文档记录 `2025` 目录下代码文件的现用名称和主要用途。脚本已统一从早期的数字编号、临时中文名改为按工程链路和功能命名，便于后续运行、检索和维护。

## 命名规则

- `problemN_...`：正式运行目录中的历史脚本前缀，当前按工程链路解释其职责。
- `workspace_...`：`01_modeling_workspace` 中的历史实验快照或探索副本。
- `theoretical_power_...`：站点机理诊断中的 Python 理论功率计算与诊断脚本。
- `matlab_...`：站点机理诊断或探索图中的 MATLAB 分析脚本。
- `_shared/` 和 `tools/`：跨脚本复用的工程工具和检查工具。

## 公共工具

| 文件 | 用途 |
| --- | --- |
| `_shared/pv_project.py` | Python 公共工具，提供路径解析、中文期刊绘图配置、随机种子、训练集归一化、指标计算、输出产物管理和 PyTorch checkpoint 保存/复用。 |
| `_shared/matlab/resolve_project_input.m` | MATLAB 输入文件定位工具，减少脚本对当前工作目录的依赖。 |
| `_shared/matlab/configure_journal_plot.m` | MATLAB 中文期刊绘图默认值配置工具。 |
| `_shared/matlab/project_output_path.m` | MATLAB `outputs/` 输出路径生成工具。 |
| `_shared/matlab/save_project_figure.m` | MATLAB 期刊风格图像保存工具，默认写入 `outputs/figures/`。 |
| `tools/project_health_check.py` | 静态健康检查脚本，检查 Python 语法、重复代码快照、相对输入文件和正式链路脚本输出约束。 |
| `ENGINEERING_PROFILE.md` | 工程化运行画像，说明系统定位、数据契约、模型链路、质量门禁、运行档案和扩展边界。 |
| `tools/generate_csust_report.py` | 归档报告 Word 生成脚本，按长沙理工大学样张设置页眉页脚、摘要、目录、正文标题、图表编号和表格样式。 |
| `tools/export_csust_report.ps1` | 报告导出脚本，更新 Word 目录和页码，导出 PDF，并渲染检查页。 |
| `run_project.py` | 项目总控入口，支持用 `--run` 选择工程链路、用 `--parallel` 并行运行互不依赖主任务、用 `--show` 查看已有输出，并显式处理运行场景归因对历史功率基线/气象预报融合预测表的依赖。 |
| `app.py` | Streamlit 预测工作台，读取已有 `outputs/`，提供工作台、运行结果、工程档案、代码与命令、运行解读和训练控制；训练控制支持后台日志、Epoch 进度、停止和基于 checkpoint 的继续运行；直接用 `python app.py` 运行时只输出正确启动提示。 |
| `software_launcher.py` | Windows 桌面启动器，通过 Tkinter 提供启动/打开软件、运行健康检查和停止后台 Streamlit 服务的可视化入口。 |
| `start_software.vbs` | 无终端双击入口，优先通过 `pythonw` 启动 `software_launcher.py`，适合演示视频和教师复现时使用。 |
| `run.bat` | Windows 命令行调试启动脚本，会检查 Python/Streamlit 并启动 `app.py`，适合查看依赖安装和 Streamlit 输出。 |
| `llm/result_context.py` | 从各条链路的 `run_summary.json` 和指标 CSV 中读取结果，整理为运行解读上下文。 |
| `llm/assistant.py` | 运行解读入口，默认读取本机 Codex config/auth 并支持 Responses API；环境变量可覆盖为兼容 HTTP、本地或远程接口，失败时离线规则兜底。 |
| `llm/prompts.py` | 项目运行解读与运行说明整理的提示词模板。 |

## 正式链路代码

### 站点机理诊断

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem1_data_analysis/theoretical_power_baseline.py` | 基础理论功率计算入口，读取单站点 Excel 并输出基线时序、指标、日均对比图和运行摘要。 |
| `02_problem_solutions/problem1_data_analysis/theoretical_power_calculation.py` | 理论功率计算版本，侧重太阳角、等效辐照度、大气透射率等物理量计算，并输出计算部件表、指标和期刊风格图。 |
| `02_problem_solutions/problem1_data_analysis/theoretical_power_diagnostics.py` | 诊断与可视化版本，用于检查理论功率和实际功率差异，并生成 `outputs/` 下的时序表、指标表、诊断图和运行摘要。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_solarposition.m` | MATLAB 太阳位置法理论功率建模脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_manual_angles.m` | MATLAB 手动太阳角计算版本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_cleaned_plots.m` | MATLAB 清理版理论功率绘图脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_basic_plots.m` | MATLAB 基础理论功率绘图脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_documented_model.m` | MATLAB 带较完整注释的理论功率建模脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_physical_model_residual_analysis.m` | MATLAB 物理模型残差分析脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_physical_model_compact_diagnostics.m` | MATLAB 精简诊断图与物理模型对比脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_physical_model_station_csv_diagnostics.m` | MATLAB 基于站点 CSV 的物理模型诊断脚本。 |

### 历史功率基线

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem2_baseline_forecasting/problem2_baseline_three_model_forecast.py` | 历史功率基线入口，使用历史功率序列训练/复用 PureLSTM、FusionModel、BiFusionModel；预测表按“输入日前一日、目标测试日 96 点”对齐，并输出指标表、期刊风格 PNG、交互 HTML、模型 checkpoint 和运行摘要。 |

### 气象预报融合与运行场景归因

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem3_scenario_analysis/problem3_weather_feature_forecast.py` | 气象预报融合主训练入口，使用“前一日实测功率 + 目标日 NWP 气象序列”预测目标日 96 点功率，并输出 checkpoint、预测表、指标表、期刊风格图和主运行摘要。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_scenario_ieee_analysis.py` | 中文期刊风格场景划分分析脚本，读取标准 `outputs/predictions/` 预测表，按目标日天气比较历史功率基线与气象预报融合的差异，并输出图、表和独立摘要。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_integrated_scenario_analysis.py` | 运行场景归因综合分析脚本，整合场景划分、特征重要性和决策树策略解释，并输出到 `outputs/` 和独立摘要。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_extended_scenario_analysis.py` | 运行场景归因扩展分析脚本，用于补充更细的目标日场景解释和结果输出，并保存独立摘要。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_three_model_curve_plot.py` | 从气象预报融合标准预测表中按目标日提取三模型典型日曲线，并保存期刊风格图、曲线表和独立摘要。 |

### 局地校正融合

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem4_feature_ablation/problem4_feature_ablation_forecast.py` | 局地校正融合主入口，以前一日实测功率和目标日天气序列构造严格日前样本，比较 NWP、LMD、mixed 三类输入配置下的预测效果，并输出 checkpoint、预测表、指标、期刊风格图和运行摘要。 |

## 建模工作区代码

`01_modeling_workspace/pvod_full_experiment/` 保留历史建模过程和实验快照。正式复现优先使用 `02_problem_solutions/`，工作区脚本适合继续探索、对照旧实验或扩展训练流程。

| 文件 | 用途 |
| --- | --- |
| `problem2_baseline_three_model_forecast.py` | 历史功率基线脚本在建模工作区中的同步副本。 |
| `problem3_weather_feature_forecast.py` | 气象预报融合主训练脚本在建模工作区中的同步副本。 |
| `problem4_feature_ablation_forecast.py` | 局地校正融合主脚本在建模工作区中的同步副本，保持与正式入口一致的严格日前输入和输出逻辑。 |
| `workspace_fusion_baseline_forecast.py` | 早期 FusionModel 基线日前预测实验。 |
| `workspace_fusion_visual_diagnostics.py` | FusionModel 预测结果可视化与诊断实验。 |
| `workspace_object_oriented_fusion_pipeline.py` | 面向对象方式组织的数据处理、训练和预测流程实验。 |
| `workspace_ceemdan_lda_fusion_baseline.py` | 引入 CEEMDAN、FFT、LDA 特征处理思路的 FusionModel 实验快照。 |
| `workspace_ceemdan_lda_fusion_preprocessing.py` | CEEMDAN/LDA 特征预处理方向的实验快照。 |
| `workspace_optuna_fusion_tuning.py` | 使用 Optuna、Dropout、AdamW 和学习率调度器的超参数调优实验。 |
| `workspace_parallel_three_model_training.py` | 使用多进程并行运行三模型训练的实验脚本。 |
| `workspace_three_model_comparison.py` | 三模型训练、预测和指标对比的历史工作区脚本。 |

## 探索图 MATLAB 脚本

| 文件 | 用途 |
| --- | --- |
| `03_figures/exploratory_analysis/exploratory_station01_export_figures.m` | 导出站点 01 探索性分析图。 |
| `03_figures/exploratory_analysis/exploratory_station5_basic_plots.m` | 站点 5 基础探索性绘图。 |
| `03_figures/exploratory_analysis/exploratory_station5_enhanced_plots.m` | 站点 5 增强版探索性绘图。 |
