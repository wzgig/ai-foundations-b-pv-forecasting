# 项目工作日志

本文件用于记录本仓库每一次较重要的整理、修改、提交和推送。后续改动建议继续按时间倒序追加。

## 2026-06-02 输出模块整理与中文期刊绘图规范

### 调整目标

- 查看并梳理当前项目代码文件的输出方式，减少 CSV、PNG 和报告散落在脚本目录中的情况。
- 将正式问题脚本统一纳入 `outputs/predictions/`、`outputs/metrics/`、`outputs/figures/`、`outputs/reports/`。
- 将绘图默认值提升为适合中文高水平期刊排版的样式：中文字体兜底、600 dpi 保存、白底、黑色坐标轴、弱网格、统一配色和紧凑图例。

### 主要改动

- 增强 `2025/_shared/pv_project.py`：
  - `configure_matplotlib()` 改为中文期刊风格配置，并自动选择本机可用中文字体。
  - 新增共享配色和图形后处理函数，所有经 `ExperimentArtifacts.save_figure()` 保存的图会统一整理坐标轴和网格。
  - `run_summary.json` 的 artifacts 现在会包含自身的 reports 记录。
- 整理问题 1 Python 脚本：
  - `theoretical_power_baseline.py` 和 `theoretical_power_calculation.py` 改为输出表格、指标、图像和运行摘要。
  - `theoretical_power_diagnostics.py` 改为复用共享期刊绘图配置。
- 整理问题 3 二次分析脚本：
  - `problem3_scenario_ieee_analysis.py`、`problem3_integrated_scenario_analysis.py`、`problem3_extended_scenario_analysis.py`、`problem3_three_model_curve_plot.py` 的图和表统一写入 `outputs/`。
  - 修复 `problem3_integrated_scenario_analysis.py` 中用 `plot_tree` 绘制随机森林的原有错误，改为真正的决策树分类器。
  - 修复 seaborn 新版本的 `palette` 弃用警告。
- 增加 MATLAB 输出与绘图公共工具：
  - `configure_journal_plot.m`
  - `project_output_path.m`
  - `save_project_figure.m`
  - `exploratory_station01_export_figures.m` 改为通过共享保存函数写入 `outputs/figures/`。
- 扩展 `project_health_check.py`：正式问题脚本现在都会检查是否使用输出管理器、是否写入 run summary、是否出现裸 `plt.show()`、`fig.show()`、`.savefig()` 或 `.to_csv()`。

### 验证结果

- `python -m py_compile`：关键 Python 文件通过。
- `python 2025\02_problem_solutions\problem1_data_analysis\theoretical_power_baseline.py`：通过。
- `python 2025\02_problem_solutions\problem1_data_analysis\theoretical_power_calculation.py`：通过。
- `python 2025\02_problem_solutions\problem1_data_analysis\theoretical_power_diagnostics.py`：通过。
- `python 2025\02_problem_solutions\problem3_scenario_analysis\problem3_extended_scenario_analysis.py`：通过。
- `python 2025\02_problem_solutions\problem3_scenario_analysis\problem3_integrated_scenario_analysis.py`：通过。
- `python 2025\02_problem_solutions\problem3_scenario_analysis\problem3_three_model_curve_plot.py`：通过。
- `python 2025\02_problem_solutions\problem3_scenario_analysis\problem3_scenario_ieee_analysis.py`：通过，当前环境未安装 `shap`，SHAP 分支按脚本逻辑跳过。

## 2026-06-02 问题 1 理论功率诊断脚本优化

### 问题判断

- `theoretical_power_diagnostics.py` 连续使用 `plt.show()`，在批处理或非交互运行时容易阻塞，且图像不会自动保存。
- 默认典型日 `2023-06-15` 不在当前数据范围 `2019-01-01` 至 `2020-12-31` 内，会生成空的日内曲线图。
- 原脚本在使用实测 `DNI/GHI` 得到等效辐照度后，又额外乘以大气透射率，导致理论功率被重复衰减，和实测功率存在系统性偏低。

### 主要改动

- 重构 `2025/02_problem_solutions/problem1_data_analysis/theoretical_power_diagnostics.py`：
  - 改为函数化入口和向量化太阳角、入射角、等效辐照度计算。
  - 默认保存图像和表格，不再弹窗阻塞；需要交互查看时可显式传入 `--show`。
  - 将主结果 `P_theo` 调整为实测辐照度经倾斜面换算、温度修正、非负裁剪和 110 MW 装机容量上限后的理论功率。
  - 保留原大气透射率口径为 `P_theo_atmospheric`，用于解释旧模型的系统性低估。
  - 自动写出逐时序结果、月统计、白昼误差指标、相对误差统计、6 张 PNG 图和 `outputs/reports/run_summary.json`。
- 同步更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md` 和 `2025/CODE_INDEX.md` 中的问题 1 运行与输出说明。

### 验证结果

- `python 2025\02_problem_solutions\problem1_data_analysis\theoretical_power_diagnostics.py`：通过，生成 11 个标准输出产物。
- 推荐口径白昼指标：RMSE 约 `7.077 MW`，MAE 约 `4.002 MW`，相关系数约 `0.965`。
- 原大气修正口径白昼指标：RMSE 约 `17.989 MW`，MAE 约 `13.987 MW`，相关系数约 `0.958`。
- `python 2025\tools\project_health_check.py`：通过。
- `python -m unittest discover -s tests -q`：通过，6 个测试成功。

## 2026-06-02 代码文件语义化命名

### 调整目标

- 将早期数字编号、临时中文名脚本改为按问题和功能命名，方便后续运行、检索和维护。
- 同步更新运行指南、代码审计、README、健康检查脚本和测试中的脚本入口引用。
- 新增代码索引，说明每个现用代码文件的职责。

### 主要改动

- 问题 1 脚本改为 `theoretical_power_baseline.py`、`theoretical_power_calculation.py`、`theoretical_power_diagnostics.py`，MATLAB 脚本改为 `matlab_...` 功能名。
- 问题 2-4 主入口改为 `problem2_baseline_three_model_forecast.py`、`problem3_weather_feature_forecast.py`、`problem4_feature_ablation_forecast.py`。
- 问题 3 场景与绘图脚本改为 `problem3_scenario_ieee_analysis.py`、`problem3_integrated_scenario_analysis.py`、`problem3_extended_scenario_analysis.py`、`problem3_three_model_curve_plot.py`。
- `01_modeling_workspace/pvod_full_experiment/` 下历史实验脚本统一使用 `workspace_...` 前缀。
- 新增 `2025/CODE_INDEX.md` 记录所有代码文件的现用名称和用途。
- 更新 `2025/RUN_GUIDE.md`、`2025/CODE_AUDIT.md`、`2025/README.md`、根目录 `README.md`、`2025/tools/project_health_check.py` 和 `tests/test_project_health.py`。

### 验证结果

- `python 2025\tools\project_health_check.py`：通过。
- `python -m unittest discover -s tests -q`：通过，6 个测试成功。

## 2026-06-02 运行顺序与结果查看文档

### 调整目标

- 为后续实际运行代码提供一份可直接照着执行的手册。
- 说明问题 1-4 的推荐运行顺序、模型 checkpoint 复用逻辑、`outputs/` 目录结构和结果查看流程。
- 明确正式运行入口优先使用 `02_problem_solutions/`，`01_modeling_workspace/` 作为历史工作区和备用副本。

### 主要改动

- 新增 `2025/RUN_GUIDE.md`，覆盖环境准备、完整运行顺序、模型保存复用、输出保存逻辑、指标/预测表/图像查看方式和常见问题。
- 在根目录 `README.md` 与 `2025/README.md` 中补充运行手册入口。

## 2026-06-02 输出产物标准化与绘图保存优化

### 问题判断

- 问题 2、问题 3、问题 4 的主训练脚本已经能保存模型 checkpoint，但大量图像仍只通过 `plt.show()` 或 `fig.show()` 展示，训练结束后容易丢失。
- 预测表、指标表直接写在脚本目录，和源代码、旧实验结果混在一起，不利于多轮实验对比。
- 缺少统一运行摘要，后续很难快速确认一次运行到底生成了哪些 CSV、PNG、HTML 和报告。

### 主要改动

- 在 `2025/_shared/pv_project.py` 中新增 `ExperimentArtifacts` 输出管理器，以及 `save_figure`、`save_plotly_html`、`write_json`、`output_dir`、`output_path` 等工具。
- 优化问题 2、问题 3、问题 4 的主脚本和 `01_modeling_workspace` 中对应副本：
  - 预测明细统一写入 `outputs/predictions/`。
  - 指标表统一写入 `outputs/metrics/`。
  - Matplotlib 图统一保存为 `outputs/figures/*.png`。
  - Plotly 交互图统一保存为 `outputs/figures/*.html`。
  - 每次完整运行写入 `outputs/reports/run_summary.json`，记录模型、样本规模、耗时和产物清单。
- 默认关闭弹窗式绘图展示，避免长训练流程被图窗阻塞；需要人工查看时可从 `outputs/figures/` 打开结果。
- `project_health_check.py` 新增受管理训练脚本检查，防止这些主入口重新出现裸 `plt.show()`、`fig.show()`、直接 `.to_csv()` 或直接 `.savefig()`。
- 单元测试新增输出管理器测试和训练脚本输出约束测试。

### 验证结果

- `python 2025\tools\project_health_check.py`：通过。
- `python -m unittest discover -s tests -q`：通过，6 个测试成功。

## 2026-06-02 模型训练缓存专项优化

### 问题判断

- 代码中并非完全没有保存模型：多个训练函数会在早停时保存权重。
- 但保存方式存在基础工程问题：大量脚本共用 `models/best_model.pth`，多模型训练会互相覆盖；再次运行时也不会先检查已有模型，仍会重新训练。

### 主要改动

- 在 `2025/_shared/pv_project.py` 中新增 PyTorch checkpoint 工具：
  - 生成安全 checkpoint 文件名。
  - 构建包含模型类、输入形状、训练轮数、学习率、早停参数等信息的训练签名。
  - 保存包含 `state_dict`、`max_power`、训练签名和最佳验证损失的 checkpoint。
  - 训练前只复用签名匹配的 checkpoint。
- 优化问题 2、问题 3、问题 4 的主训练脚本和 `01_modeling_workspace` 中对应副本：
  - 每个实验和模型使用独立 checkpoint 名称。
  - 已有匹配模型时直接加载，跳过训练。
  - 保留 `force_retrain=True` 入口用于强制重训。
- 早期建模工作区脚本从共享 `best_model.pth` 改为按模型类名保存并优先复用。
- 更新 `README.md`、`2025/README.md`、`2025/CODE_AUDIT.md`，说明模型缓存机制。
- 回归测试新增检查，防止 Python 脚本重新硬编码共享 `best_model.pth`。

### 验证结果

- `python 2025\tools\project_health_check.py`：通过。
- `python -m unittest discover -s tests -q`：通过，4 个测试成功。
- Python 源码语法解析：通过。

## 2026-06-01 代码审计与第一轮工程化优化

### 调整目标

- 阅读并分类 `2025` 目录内的 Python 和 MATLAB 程序，识别路径依赖、重复代码、数据泄漏和可维护性问题。
- 在不改变课程实验算法目标的前提下，优先修复会影响后续复现的问题。
- 增加静态检查和轻量级回归检查，后续改动可快速发现路径和语法回归。

### 主要改动

- 新增 `2025/_shared/pv_project.py`：集中提供 Python 路径解析、中文绘图、随机种子、训练集归一化、稳健分箱、白昼指标和 CSV 写出工具。
- 新增 `2025/_shared/matlab/resolve_project_input.m`：让 MATLAB 脚本能从项目候选目录中寻找数据文件。
- 新增 `2025/tools/project_health_check.py`：检查 Python 语法、重复代码快照和相对输入文件。
- 新增 `tests/test_project_health.py`：使用 `unittest` 验证项目健康检查和共享路径解析。
- 新增 `2025/CODE_AUDIT.md`：记录各脚本职责、本次优化内容和后续重构建议。
- 修复根目录 `README.md` 和 `2025/README.md` 的中文可读性，并补充新的复现/检查入口。
- 优化问题 1-4 的关键 Python 脚本：改为稳定路径解析，设置随机种子；问题 3/4 的归一化改为只在训练集拟合，避免测试集信息泄漏。
- 优化问题 1 和探索性 MATLAB 脚本：通过公共 helper 定位数据，缺失的 site 4 Excel 可回退到现存 site 5 Excel。
- 问题 3 场景分析脚本兼容更多 pandas 版本，SHAP 解释分析改为可选依赖。

### 验证结果

- `python 2025\tools\project_health_check.py`：通过，未发现 Python 语法错误或不可解析的相对输入文件。
- `python -m unittest discover -s tests -q`：通过，2 个测试成功。

## 2026-06-01 仓库初始化与公开上传

- 初始化本地 Git 仓库，创建 `main` 分支。
- 新增根目录 `README.md`、`.gitignore`、`.gitattributes`。
- 创建 GitHub 公开仓库 `wzgig/ai-foundations-b-pv-forecasting` 并推送首次提交。
- 首次提交：`53f39a4 chore: add AI foundations course project archive`

## 2026-06-01 项目文件审计与清理

### 判断标准

- 保留：课程题面、核心 PVOD 数据集、问题 1-4 的代码/结果/图表、最终论文、论文中使用的图像素材。
- 删除：重复压缩包、已解压且可由目录内容替代的归档包、外部下载的参考论文原文、外部示例数据仓库、论文转换中间稿、竞赛成绩/证书类个人归档、IDE 本地配置。

### 保留的核心材料

- `2025/01_modeling_workspace/pvod_full_experiment/`：主要光伏数据、模型脚本、预测结果和模型文件。
- `2025/02_problem_solutions/`：按题目拆分的代码、结果表、图表和说明文档。
- `2025/04_paper/final_submission/003158 A.pdf` 与 `2025/04_paper/final_submission/003158 A.docx`：最终论文文件。
- `2025/03_figures/`：保留可直接用于论文展示的图像和绘图结果。
- `2025/00_course_materials/`：课程/题目资料。

### 删除的主要类别

- 重复压缩包：`问题1.zip`、`问题2.zip`、`问题3*.zip`、`问题4*.zip`、`PVODdatasets_v1.0.zip`、`支撑材料.zip`、`数据分析绘图.zip` 及 `2025/支撑材料/`。
- 外部参考与下载包：`Renewable-energy-generation-input-feature-variables-analysis-main/`、`20230108agRmGPd2/`、`中文论文复现/` 及若干参考论文 PDF。
- 过程与个人归档：`003158/`、`003158.zip`、竞赛成绩/获奖名单文件、网页归档 `1258_142765994.html`。
- 论文中间稿：`ConvertedDoc*.docx`、`摘要.docx`、`问题1改完.docx`、`问题3补充.docx`、`代码.docx`。
- 绘图源文件：`*.pptx`、`*.eddx`，保留对应 PNG 图像素材。

### 清理结果

- `2025` 目录从约 `511MB / 269` 个文件精简到约 `144MB / 170` 个文件。
- 仓库结构改为围绕“数据集 + 问题代码 + 结果图表 + 最终论文”维护。

## 2026-06-01 `2025` 目录架构重组

### 调整目标

- 按后续工作流组织文件，而不是按原始堆放位置组织文件。
- 保留问题目录和建模工作区的自包含性，避免脚本因同目录数据被拆散而失效。
- 给 `2025` 目录增加单独说明，降低后续查找文件和继续实验的成本。

### 新结构

- `2025/00_course_materials/`：题面 PDF 和课程附件。
- `2025/01_modeling_workspace/pvod_full_experiment/`：完整 PVOD 建模工作区，包含主数据、模型脚本、预测结果和模型权重。
- `2025/02_problem_solutions/`：按问题拆分的交付材料。
  - `problem1_data_analysis/`
  - `problem2_baseline_forecasting/`
  - `problem3_scenario_analysis/`
  - `problem4_feature_ablation/`
- `2025/03_figures/`：探索图、论文素材图和典型场景对比图。
- `2025/04_paper/final_submission/`：最终论文 PDF 和 Word 文档。

### 文档更新

- 更新根目录 `README.md` 的路径说明和复现实验入口。
- 新增 `2025/README.md`，说明每个目录的职责、运行入口和维护约定。
