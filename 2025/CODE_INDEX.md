# 代码文件索引

本文档记录 `2025` 目录下代码文件的现用名称和主要用途。脚本已统一从早期的数字编号、临时中文名改为按问题和功能命名，便于后续运行、检索和维护。

## 命名规则

- `problemN_...`：正式交付目录中的问题主线代码。
- `workspace_...`：`01_modeling_workspace` 中的历史实验快照或探索副本。
- `theoretical_power_...`：问题 1 的 Python 理论功率计算与诊断脚本。
- `matlab_...`：问题 1 或探索图中的 MATLAB 分析脚本。
- `_shared/` 和 `tools/`：跨脚本复用的工程工具和检查工具。

## 公共工具

| 文件 | 用途 |
| --- | --- |
| `_shared/pv_project.py` | Python 公共工具，提供路径解析、中文绘图配置、随机种子、训练集归一化、指标计算、输出产物管理和 PyTorch checkpoint 保存/复用。 |
| `_shared/matlab/resolve_project_input.m` | MATLAB 输入文件定位工具，减少脚本对当前工作目录的依赖。 |
| `tools/project_health_check.py` | 静态健康检查脚本，检查 Python 语法、重复代码快照、相对输入文件和受管理训练脚本输出约束。 |

## 正式问题代码

### 问题 1：数据分析与理论功率建模

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem1_data_analysis/theoretical_power_baseline.py` | 问题 1 的基础理论功率计算入口，读取单站点 Excel 并进行初步建模与对比。 |
| `02_problem_solutions/problem1_data_analysis/theoretical_power_calculation.py` | 问题 1 的理论功率计算版本，侧重太阳角、等效辐照度、大气透射率等物理量计算。 |
| `02_problem_solutions/problem1_data_analysis/theoretical_power_diagnostics.py` | 问题 1 的诊断与可视化版本，用于检查理论功率和实际功率差异，并生成 `outputs/` 下的时序表、指标表、诊断图和运行摘要。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_solarposition.m` | MATLAB 太阳位置法理论功率建模脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_manual_angles.m` | MATLAB 手动太阳角计算版本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_cleaned_plots.m` | MATLAB 清理版理论功率绘图脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_basic_plots.m` | MATLAB 基础理论功率绘图脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_theoretical_power_documented_model.m` | MATLAB 带较完整注释的理论功率建模脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_physical_model_residual_analysis.m` | MATLAB 物理模型残差分析脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_physical_model_compact_diagnostics.m` | MATLAB 精简诊断图与物理模型对比脚本。 |
| `02_problem_solutions/problem1_data_analysis/matlab_physical_model_station_csv_diagnostics.m` | MATLAB 基于站点 CSV 的物理模型诊断脚本。 |

### 问题 2：基础日前预测

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem2_baseline_forecasting/problem2_baseline_three_model_forecast.py` | 问题 2 主入口，使用历史功率序列训练/复用 PureLSTM、FusionModel、BiFusionModel，并输出预测表、指标表和图像。 |

### 问题 3：气象场景与模型改进

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem3_scenario_analysis/problem3_weather_feature_forecast.py` | 问题 3 主训练入口，在问题 2 模型基础上加入多维气象输入。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_scenario_ieee_analysis.py` | IEEE 风格场景划分分析脚本，比较问题 2 与问题 3 结果在不同气象场景下的差异。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_integrated_scenario_analysis.py` | 问题 3 综合分析脚本，整合场景划分、特征重要性和提升来源分析。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_extended_scenario_analysis.py` | 问题 3 扩展分析脚本，用于补充更细的场景解释和结果输出。 |
| `02_problem_solutions/problem3_scenario_analysis/problem3_three_model_curve_plot.py` | 从问题 3 预测结果中提取三模型典型日曲线并绘图。 |

### 问题 4：输入特征消融

| 文件 | 用途 |
| --- | --- |
| `02_problem_solutions/problem4_feature_ablation/problem4_feature_ablation_forecast.py` | 问题 4 主入口，比较 NWP、LMD、mixed 三类输入配置下的预测效果。 |

## 建模工作区代码

`01_modeling_workspace/pvod_full_experiment/` 保留历史建模过程和实验快照。正式复现优先使用 `02_problem_solutions/`，工作区脚本适合继续探索、对照旧实验或扩展训练流程。

| 文件 | 用途 |
| --- | --- |
| `problem2_baseline_three_model_forecast.py` | 问题 2 主脚本在建模工作区中的同步副本。 |
| `problem3_weather_feature_forecast.py` | 问题 3 主训练脚本在建模工作区中的同步副本。 |
| `problem4_feature_ablation_forecast.py` | 问题 4 主脚本在建模工作区中的同步副本。 |
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
