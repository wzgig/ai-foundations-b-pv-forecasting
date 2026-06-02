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

`01_modeling_workspace/pvod_full_experiment/` 中的问题 2、3、4 同名脚本已经和正式入口同步，可以作为备用入口；其他编号脚本多为阶段性实验快照，不建议作为第一次完整复现的主线。

## 2. 运行前准备

从项目根目录打开 PowerShell：

```powershell
cd "d:\Qiuhua Wang\个人资料\电气\人工智能基础B\电气工程及其自动化+2307+202310080241+王子成+标题"
```

安装依赖：

```powershell
pip install -r 2025\requirements.txt
```

先运行静态检查和轻量测试：

```powershell
python 2025\tools\project_health_check.py
python -m unittest discover -s tests -q
```

这两个命令不会训练模型。它们用于确认 Python 文件可解析、输入文件能找到、核心输出管理约束没有被破坏。

## 3. 推荐完整运行顺序

### 步骤 1：问题 1 数据分析

问题 1 主要是数据理解、理论功率建模和探索性绘图。Python 脚本入口在：

```powershell
cd 2025\02_problem_solutions\problem1_data_analysis
python .\theoretical_power_baseline.py
python .\theoretical_power_calculation.py
python .\theoretical_power_diagnostics.py
```

MATLAB 脚本如 `matlab_theoretical_power_solarposition.m`、`matlab_theoretical_power_manual_angles.m`、`matlab_theoretical_power_cleaned_plots.m`、`matlab_physical_model_residual_analysis.m` 等是同一问题下的物理建模和绘图补充。如果只复现 Python 深度学习主线，可以先跳过 MATLAB。

### 步骤 2：问题 2 基准日前预测

问题 2 使用历史功率序列训练并比较 `PureLSTM`、`FusionModel`、`BiFusionModel` 三类模型。

```powershell
cd ..\problem2_baseline_forecasting
python .\problem2_baseline_three_model_forecast.py
```

首次运行会训练模型，耗时较长。后续运行会优先复用签名匹配的 checkpoint。

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

### 步骤 3：问题 3 引入气象变量后的预测

问题 3 在问题 2 的建模框架上加入 NWP 等多维气象输入，用于比较气象变量对预测效果的提升。

```powershell
cd ..\problem3_scenario_analysis
python .\problem3_weather_feature_forecast.py
```

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
```

### 步骤 4：问题 3 场景划分与提升来源分析

这一步使用问题 2 和问题 3 的预测结果做二次分析，解释在不同气象场景下误差改善来自哪里。

推荐在确认问题 2、问题 3 的预测结果已经生成后再运行：

```powershell
python .\problem3_scenario_ieee_analysis.py
python .\problem3_integrated_scenario_analysis.py
python .\problem3_extended_scenario_analysis.py
python .\problem3_three_model_curve_plot.py
```

注意：这些二次分析脚本是早期交付脚本，当前目录中保留了历史结果 CSV，因此即使没有重新训练也能运行。如果你要让它们严格使用刚刚重新训练得到的新结果，应先核对或同步下面两类表：

```text
问题 2 新结果：
2025/02_problem_solutions/problem2_baseline_forecasting/outputs/predictions/三模型预测结果对比表.csv

问题 3 新结果：
2025/02_problem_solutions/problem3_scenario_analysis/outputs/predictions/3三模型预测结果对比表.csv
```

如果只是查看本仓库已保存的交付结果，可以直接运行这些二次分析脚本；如果你要做新的严格实验记录，建议以 `outputs/` 下的新表为准。

### 步骤 5：问题 4 输入特征消融

问题 4 比较 `nwp`、`lmd`、`mixed` 三种输入配置下的模型表现。

```powershell
cd ..\problem4_feature_ablation
python .\problem4_feature_ablation_forecast.py
```

当前脚本默认只运行 `FusionModel`。如需同时运行 `PureLSTM` 或 `BiFusionModel`，需要在脚本底部的 `model_dict` 中取消对应注释。

主要输出：

```text
models/
outputs/predictions/Q4_pred_FusionModel_nwp.csv
outputs/predictions/Q4_pred_FusionModel_lmd.csv
outputs/predictions/Q4_pred_FusionModel_mixed.csv
outputs/metrics/Q4_模型输入对比结果.csv
outputs/figures/Q4_模型输入对比结果热力图.png
outputs/figures/三输入_多模型空间降尺度预测指标热力图.png
outputs/figures/*_输入对比雷达图.png
outputs/figures/*_指标对比_不同输入模式.png
outputs/figures/*_vs_输入特征维度.png
outputs/reports/run_summary.json
```

## 4. 模型保存与复用逻辑

问题 2、问题 3、问题 4 的主训练脚本都使用相同的 checkpoint 逻辑：

1. 训练前先根据模型类、输入形状、训练集形状、训练轮数、学习率、早停参数等生成训练签名。
2. 在当前脚本目录的 `models/` 下查找对应 checkpoint。
3. 如果 checkpoint 存在且训练签名完全匹配，直接加载模型，跳过训练。
4. 如果 checkpoint 不存在或签名不匹配，重新训练并保存新的 checkpoint。
5. 如果想强制重训，在对应脚本的 `train_model(...)` 调用中加入或改为 `force_retrain=True`。

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

## 5. 输出保存逻辑

问题 2、问题 3、问题 4 的主脚本使用统一输出结构：

```text
outputs/
  predictions/   预测明细和统一预测对比表
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

## 6. 结果查看顺序

每个问题运行结束后，建议按下面顺序查看结果。

### 先看运行摘要

```text
outputs/reports/run_summary.json
```

重点看：

- `script`：本次运行的脚本。
- `metadata`：模型列表、样本规模、耗时。
- `artifacts`：所有输出文件清单。

### 再看指标表

问题 2、问题 3：

```text
outputs/metrics/三模型白昼指标对比.csv
```

问题 4：

```text
outputs/metrics/Q4_模型输入对比结果.csv
```

核心指标含义：

- `RMSE`、`MAE`、`MAPE`：常规误差指标，越小越好。
- `E_rmse`、`E_mae`、`E_me`：按装机容量归一化后的附件指标。
- `r`：相关系数，越接近 1 越好。
- `C_R`、`Q_R`：课程附件中的考核指标，通常越高越好。

### 再看预测明细

问题 2：

```text
outputs/predictions/三模型预测结果对比表.csv
```

问题 3：

```text
outputs/predictions/3三模型预测结果对比表.csv
```

问题 4：

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

## 7. 快速查看命令

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

## 8. 推荐复现实验记录方式

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

## 9. 常见问题

### 运行很慢怎么办？

第一次训练慢是正常的。后续只要 checkpoint 签名匹配，会直接加载模型。可以先运行问题 2，确认输出结构没问题，再继续问题 3 和问题 4。

### 我改了绘图代码，会重新训练吗？

一般不会。训练是否复用只看模型、输入和训练参数签名。只改绘图或输出逻辑通常会复用已有 checkpoint。

### 我想重新训练怎么办？

两种方式：

1. 在脚本调用 `train_model(...)` 时设置 `force_retrain=True`。
2. 删除对应 `models/*.pth` 后重新运行脚本。

推荐第一种，记录更清楚。

### 应该运行 `01_modeling_workspace` 还是 `02_problem_solutions`？

正式复现优先运行 `02_problem_solutions`。`01_modeling_workspace` 保留了更完整的建模过程和阶段性脚本，适合做实验探索，不适合作为第一次运行的主线。
