# 项目工作日志

本文件用于记录本仓库每一次较重要的整理、修改、提交和推送。后续改动建议继续按时间倒序追加。

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
