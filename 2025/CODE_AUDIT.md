# 代码审计与优化记录

更新时间：2026-06-01

## 审计范围

本次阅读并检查了 `2025` 目录下的程序文件：

- Python：23 个文件，包括 21 个原始课程脚本和 2 个新增工程工具。
- MATLAB：12 个文件，包括 11 个原始分析/绘图脚本和 1 个新增输入解析函数。

## 代码在做什么

### 问题 1：数据分析与理论功率建模

位置：`02_problem_solutions/problem1_data_analysis/`

- Python 脚本 `1.py`、`2.py`、`3.py` 读取单站点 Excel 数据，计算太阳角、等效辐照度、大气透射率和理论功率，并与实际功率对比。
- MATLAB 脚本 `a.m`、`b.m`、`c.m`、`e.m`、`f.m`、`g.m`、`k.m`、`z.m` 负责类似的物理建模、统计分析和绘图。

### 问题 2：基础日前预测

位置：`02_problem_solutions/problem2_baseline_forecasting/`

- 核心脚本 `7添加绘图与输出三个指标的对比表格.py` 使用 PureLSTM、FusionModel、BiFusionModel 三类模型进行日前预测。
- 输出单模型预测 CSV、三模型统一预测对比表、白昼指标表和日曲线/热力图。

### 问题 3：气象场景与模型改进

位置：`02_problem_solutions/problem3_scenario_analysis/`

- `9问题3初步.py` 在问题 2 的模型基础上加入多维气象输入。
- `问题3_场景划分分析_IEEE风格.py`、`问题3_整合分析脚本.py`、`问题3延伸.py` 对比问题 2 和问题 3 的 FusionModel 结果，按光照、温度、湿度、风速和季节做场景划分，并分析 RMSE 提升来源。
- `三模型绘图.py` 从问题 3 预测结果表提取典型日曲线并输出对比图。

### 问题 4：输入特征消融

位置：`02_problem_solutions/problem4_feature_ablation/`

- `10问题4.py` 比较 NWP、LMD、混合输入三种配置下的模型表现，输出白昼误差、附件指标和特征维度相关图。

### 完整建模工作区

位置：`01_modeling_workspace/pvod_full_experiment/`

该目录保留了从早期实验到最终对比的脚本快照。部分文件是课程实验过程中的阶段版本，例如：

- `2第二问基础.py` 与 `4第二问模型加入数据预处理以及超参数优化.py` 当前内容完全一致。
- `9问题3初步.py` 与问题 3 交付目录中的同名脚本保持一致。
- `10问题4.py` 与问题 4 交付目录中的同名脚本保持一致。

## 本轮已完成的优化

- 新增 `_shared/pv_project.py`，集中处理 Python 路径解析、中文绘图配置、随机种子、训练集归一化、稳健分箱和 CSV 写出。
- 新增 `_shared/matlab/resolve_project_input.m`，让 MATLAB 脚本可以从脚本目录和项目内候选目录寻找数据。
- 新增 `tools/project_health_check.py`，静态检查 Python 语法、重复代码快照和相对输入文件。
- 新增 `tests/test_project_health.py`，用标准库 `unittest` 验证健康检查和共享路径解析。
- 修复根目录 `README.md` 和 `2025/README.md` 的可读性与结构说明。
- 问题 1 Python 脚本改为使用脚本所在目录读取 Excel 数据，减少运行目录依赖。
- 问题 1 与探索性 MATLAB 脚本改为通过公共 helper 定位输入文件；缺失的 site 4 Excel 会回退到项目中现存的 site 5 Excel。
- 问题 2、问题 3、问题 4 的主要 Python 脚本改为使用项目路径解析和统一随机种子。
- 问题 3、问题 4 的归一化逻辑改为只在训练集拟合，再变换全量数据，避免测试集信息泄漏。
- 问题 3 场景分析中的 `pd.groupby(...).apply(..., include_groups=False)` 改为显式循环，兼容更多 pandas 版本。
- 问题 3 的 SHAP 分析改为可选依赖，未安装 `shap` 时会跳过解释性图，不影响前面的场景分析输出。
- `三模型绘图.py` 改为读取实际存在的 `问题3三模型预测结果对比表.csv`，并输出到脚本目录下的 `三模型绘图.png`。

## 2026-06-02 模型训练缓存专项检查

### 发现的问题

代码中已经有保存模型的意识，但实现方式不完整：

- 多数训练函数只在训练过程中保存 `models/best_model.pth`，再次运行时仍然从头训练。
- 多模型循环共用同一个 `best_model.pth`，PureLSTM、FusionModel、BiFusionModel 会互相覆盖。
- 检查点没有记录训练配置，后续很难判断某个 `.pth` 是否对应当前模型、输入维度、训练轮数和超参数。

### 已完成的改进

- 新增 `pv_project.py` 中的 checkpoint helper：构建训练签名、生成安全文件名、保存/加载带元数据的 PyTorch checkpoint。
- 问题 2、问题 3、问题 4 的主脚本和对应建模工作区副本已支持：
  - 按实验和模型独立保存，例如 `problem2_FusionModel.pth`、`problem4_BiFusionModel_mixed.pth`。
  - 训练前先检查同名 checkpoint。
  - 只有训练签名匹配时才复用，避免加载旧结构或旧超参数模型。
  - 需要重新训练时可在函数参数中设置 `force_retrain=True`。
- 早期建模工作区脚本已从共享 `best_model.pth` 改为按模型类名保存，并在训练前优先复用已有权重。
- 回归测试新增检查：Python 脚本中不再硬编码 `best_model.pth`。

## 当前检查结果

运行命令：

```powershell
python 2025\tools\project_health_check.py
python -m unittest discover -s tests -q
```

结果：

- Python 语法检查：通过。
- 相对输入文件检查：通过，当前未发现找不到的相对输入。
- 单元检查：4 个测试通过。

## 后续建议

- 把重复的 PyTorch 模型类、训练循环、评估函数抽取到一个正式模块，例如 `_shared/forecasting_models.py`。
- 将 `01_modeling_workspace` 中的阶段性脚本标注为实验快照，交付目录脚本作为主入口。
- 为模型训练增加命令行参数，例如 `--epochs`、`--no-show`、`--output-dir`，方便快速试运行和批量实验。
- 如果继续压缩仓库体积，可考虑把大型预测 CSV 和模型权重迁移到 GitHub Release 或外部数据存储。
