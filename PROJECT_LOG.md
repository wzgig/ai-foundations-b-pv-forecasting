# 项目工作日志

本文件用于记录本仓库每一次较重要的整理、修改、提交和推送。后续改动建议继续按时间倒序追加。

## 2026-07-01 项目文件夹结构整理与命名优化

### 调整目标

- 按用户要求对当前项目文件夹做整体整理，减少根目录杂物，提升目录可读性和交付材料辨识度。
- 保留有复现、报告、素材和交付价值的文件；只清理本地忽略缓存、百度云上传残留配置、Word 锁文件和临时渲染目录。
- 对不清晰的文件名做低风险重命名，不改正式代码链路目录，避免破坏运行入口。

### 主要改动

- 将根目录课程通知 PDF 移入课程材料目录：
  - `2025/00_course_materials/人工智能基础B_期末大作业布置通知.pdf`
- 将旧编号论文文件重命名为更清晰的素材名：
  - `2025/04_paper/final_submission/历史论文素材_光伏日前预测.pdf`
  - `2025/04_paper/final_submission/历史论文素材_光伏日前预测.docx`
- 新增目录说明文件：
  - `2025/00_course_materials/README.md`
  - `2025/01_modeling_workspace/README.md`
  - `2025/02_problem_solutions/README.md`
  - `2025/03_figures/README.md`
  - `2025/04_paper/README.md`
  - `2025/tools/README.md`
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md`、`2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md` 和 `2025/05_delivery/作业要求提取.md`，同步新的目录职责和文件路径。
- 更新 `2025/app.py` 的交付引用，把旧论文条目标注为“论文素材”，并指向新文件名。
- 本地清理忽略文件：删除 `tmp/`、`__pycache__/`、`*.baiduyun.uploading.cfg` 和 Word `~$*.docx` 锁文件。

### 验证结果

- `python 2025\tools\project_health_check.py`：通过，无 Python 解析错误、无未解析相对输入、无受管输出问题；仍保留两组历史实验副本重复记录。
- `python -m unittest discover -s tests -q`：通过，24 个测试 OK。
- `python -m py_compile 2025\app.py 2025\run_project.py 2025\tools\project_health_check.py 2025\tools\generate_csust_report.py`：通过。
- 文件存在性抽检：课程通知、A 题题面、附件 1、历史论文 PDF/DOCX 均存在于新路径。
- `python 2025\app.py`：通过，只输出 Streamlit 正确启动提示。
- `python 2025\run_project.py --show all`：通过，五条工程链路已有输出、指标和摘要可读取。

### 后续注意事项

- `01_modeling_workspace/` 仍保留为历史建模工作区，体积较大；最终压缩包若超 200M，可按 `05_delivery/最终提交包清单.md` 的策略压缩或剔除历史副本。
- 历史日志中保留旧文件名记录，用于说明当时项目状态；当前使用新路径。

## 2026-07-01 按长沙理工大学样张重排项目主报告终稿

### 调整目标

- 阅读并对照 `长沙理工大学本科毕业设计（论文）撰写规范样张.doc` 的页面风格，对已生成的项目主报告终稿做正式论文式排版。
- 保留工程项目叙事和课程大作业内容，不改写教师模板文件，不补未确认团队成员姓名学号。
- 让 Word/PDF 终稿更接近落地项目材料：页眉页脚、摘要、英文摘要、目录、标题层级、图表编号和表格样式统一。

### 主要改动

- 更新 `2025/05_delivery/项目主报告_终稿.md`：
  - 增补英文题名、英文摘要和 Key words。
  - 将系统架构处的箭头式草稿表达改为工程链路叙述。
- 新增 `2025/tools/generate_csust_report.py`：
  - 按 A4、左 3cm/右 2cm/上 2.5cm/下 2cm、页眉校名标识、页脚页码、黑体标题、宋体正文、Times New Roman 英文等样张特征生成 DOCX。
  - 自动处理摘要、英文摘要、目录字段、正文标题、图题编号、表题编号、三线表风格和图片插入。
- 新增 `2025/03_figures/paper_assets/csust_header_logo.jpeg`，用于稳定复现样张页眉校名标识。
- 新增 `2025/tools/export_csust_report.ps1`：
  - 自动执行 DOCX 生成、Word 更新目录和页码、目录压缩、LibreOffice 导出 PDF，并在可用时渲染 PDF 页面供检查。
- 重新生成：
  - `2025/05_delivery/项目主报告_终稿.docx`
  - `2025/05_delivery/项目主报告_终稿.pdf`
- 更新 `2025/05_delivery/README.md` 和 `最终提交包清单.md`，标明终稿已按长沙理工大学样张排版，并记录导出脚本。

### 验证结果

- `.\2025\tools\export_csust_report.ps1`：通过，生成 Word/PDF，PDF 共 12 页。
- `python -m py_compile 2025\tools\generate_csust_report.py`：通过。
- `python 2025\tools\project_health_check.py`：通过，无 Python 解析错误、无未解析相对输入、无受管输出问题；仍保留两组历史实验副本重复记录。
- `python -m unittest discover -s tests -q`：通过，23 个测试 OK。
- `python 2025\run_project.py --show all`：通过，五条工程链路已有输出、指标和摘要可读取。
- `git diff --check`：通过，仅提示 Windows 下 `tests/test_project_health.py` 后续可能按 CRLF 检出。
- `pdftoppm -png -r 140 ...`：通过，已检查摘要、英文摘要、目录、正文开头、表格页、图表页和末页。
- 视觉检查结果：目录压缩为一页，目录页码与 PDF 页脚一致；一级/二级标题为黑体黑字；图题和表题已编号；页眉页脚、页码、表格和图片无明显遮挡。

### 后续注意事项

- 若继续改 `项目主报告_终稿.md`，应运行 `.\2025\tools\export_csust_report.ps1` 重新生成 DOCX/PDF，并复查渲染页。
- 真实团队成员姓名学号、演示视频 MP4 和最终平台上传仍需提交前人工确认。

## 2026-07-01 项目主报告终稿 Word/PDF 生成

### 调整目标

- 按用户要求暂不补真实团队成员姓名和学号，但先将团队分工按项目职责写实填入报告。
- 在已有课程版主报告草稿基础上，撰写一份可提交的项目主报告终稿，并导出 Word 与 PDF。
- 让报告满足课程通知中“Word/PDF、优先 PDF、不少于 2500 字、背景意义、方案设计、技术实现、实验结果、总结展望、图文并茂”的要求。

### 主要改动

- 新增 `2025/05_delivery/项目主报告_终稿.md`：
  - 保留课程封面信息和摘要。
  - 补充角色化团队分工表，不填写未确认成员姓名学号。
  - 增加系统架构、技术选型、模块划分、数据模块、模型模块、运行解读、交互模块、功能测试、结果分析和稳定性设计。
  - 引入真实项目图表，包括预测流程图、理论功率月度对比、气象预报融合预测曲线和局地校正融合雷达图。
- 生成正式交付文件：
  - `2025/05_delivery/项目主报告_终稿.docx`
  - `2025/05_delivery/项目主报告_终稿.pdf`
- 更新 `2025/05_delivery/README.md` 和 `最终提交包清单.md`，标注 Word/PDF 终稿已生成。
- 更新 `tests/test_project_health.py`，增加终稿 Markdown、DOCX 和 PDF 存在性与体积检查。

### 验证结果

- `pandoc 项目主报告_终稿.md -o 项目主报告_终稿.docx --toc ...`：通过，生成 DOCX 约 2.09MB。
- `pandoc 项目主报告_终稿.md -o 项目主报告_终稿.pdf --toc --pdf-engine=xelatex ...`：通过，生成 PDF 约 2.34MB。
- `pdftoppm -png -f 1 -l 8 -r 120 ...`：通过，PDF 共 8 页，已渲染检查封面/目录、表格页和图表页。
- Python 抽检：PDF 共 8 页；DOCX 包含 71 个正文段落、7 个表格、4 张内嵌图。

### 后续注意事项

- 终稿中“团队成员”仍按用户要求暂不填写真实姓名学号，正式提交前可按课程平台最终名单替换。
- 演示视频 MP4 和最终压缩包仍需后续人工生成。

## 2026-07-01 课程交付复盘、主报告草稿与提交材料补齐

### 调整目标

- 按用户要求重新阅读《人工智能基础B》期末大作业通知、A 题题面和附件指标，对当前仓库完成情况做课程交付级复盘。
- 在不破坏既有模型、输出路径和工程链路叙事的前提下，补齐最终提交最容易缺失的课程材料：要求提取、完成度复盘、课程主报告草稿、团队分工、测试表、演示视频脚本、网站使用指南和打包清单。
- 继续避免前台以“题号答案”方式展示项目，把工作台和 Pages 的新增入口统一表述为工程交付、课程交付和运行审查。

### 主要改动

- 新增 `2025/05_delivery/`：
  - `README.md`：课程交付工作台入口。
  - `作业要求提取.md`：提取组队、截止时间、报告、代码包、演示视频、补充材料和附件指标要求。
  - `交付完成度复盘.md`：对照当前仓库梳理已完成、待人工完成和风险项。
  - `项目主报告_课程版.md`：按课程评分表重写背景、方案、实现、测试结果、总结展望和复现命令。
  - `团队分工与项目计划.md`：提供 3 人/4 人职责模板和提交前计划。
  - `功能性能稳定性测试表.md`：整理功能测试、模型性能指标、稳定性测试和复核命令。
  - `演示视频脚本.md`：提供 3 分钟以内 MP4 的分镜、讲解路线和质量检查。
  - `网站使用指南与案例.md`：说明 Pages、Streamlit 工作台和典型使用场景。
  - `最终提交包清单.md`：列出压缩包命名、建议结构、必放材料和体积控制策略。
- 优化 `2025/app.py`：
  - 新增“课程交付”导航页，支持材料总览、Markdown 预览、下载和提交前动作清单。
  - 将课程交付材料纳入“交付引用”索引。
- 更新 `docs/index.html`：
  - 首屏增加“课程交付材料”信号。
  - 新增“课程交付”区块，并在材料入口加入 `2025/05_delivery` 链接。
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md` 和 `2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`：
  - 同步课程交付目录、新工作台页面和 2026-07-01 复盘状态。
- 更新 `tests/test_project_health.py`：
  - 增加课程交付文档存在性、关键内容、工作台入口和 Pages 链接检查。

### 验证结果

- `python -m py_compile 2025\app.py 2025\run_project.py 2025\llm\assistant.py 2025\llm\result_context.py 2025\llm\prompts.py 2025\software_launcher.py`：通过。
- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、缺失相对输入或受管输出问题；仍保留两组已知历史实验副本重复。
- `python -m unittest discover -s tests -q`：通过，22 个测试 OK。
- `python 2025\run_project.py --show all`：通过，五条工程链路已有输出可读取。
- `python 2025\app.py`：通过，只输出正确 Streamlit 启动提示。
- `npx playwright screenshot --wait-for-timeout=5000 --viewport-size=1440,1100 http://127.0.0.1:8512 ...`：通过，工作台首屏正常，侧边栏显示“课程交付”。
- `npx playwright screenshot --wait-for-timeout=1500 --viewport-size=1440,1100 file:///.../docs/index.html ...`：通过，Pages 首屏正常，已显示“课程交付材料”。

### 后续注意事项

- 本轮没有生成正式 PDF/DOCX、真实 MP4 和最终压缩包；这些需要补齐团队信息、人工录制视频和平台上传前体积审查。
- 课程通知中同时出现头歌和学习通端口，最终上传前仍需以任课教师或课程群最新说明为准。
- `05_delivery/项目主报告_课程版.md` 已是课程报告草稿，但正式提交建议导出为 PDF 和 Word，并加入团队成员信息、截图和封面。

## 2026-07-01 工程链路叙事、运行视角交互与 Pages 资产去编号

### 调整目标

- 按用户要求进一步去掉“问题二/三/四”式展示，把公开页面和本地工作台改为更贴近工程实际的光伏电站日前计划、调度复盘和模型维护项目。
- 在不破坏既有目录、脚本 key 和输出路径的前提下，将前台叙事统一为“站点机理诊断、历史功率基线、气象预报融合、运行场景归因、局地校正融合”。
- 继续降低 AI 生成/总结感，结果解读模块前台改称“运行解读”，文档中改用“交付说明、兼容 HTTP 端点、语言接口”等更工程化表达。

### 主要改动

- 优化 `2025/app.py`：
  - 新增“运行视角”分段控件，支持 `日前计划`、`调度复盘`、`模型维护`、`交付审查` 四类使用语境。
  - 新增“模型链路对比”交互表，支持用 `st.pills` 选择链路、用 `st.dataframe(..., on_select="rerun")` 点选链路并显示工程含义。
  - 将指标卡、洞察卡、精选图表、交付引用、运行解读、侧边栏和空态文案全部改为工程链路语言。
- 更新 `docs/index.html`：
  - 将 GitHub Pages 首屏改成“光伏电站日前计划与功率预测工作台”，核心结果卡改为历史功率基线、气象预报融合、局地校正融合。
  - 新增静态页“运行视角”按钮组，用少量原生 JS 切换日前计划、调度复盘、模型维护和交付审查说明。
  - 裁剪 `docs/assets/forecast-curve.png` 顶部旧图题，避免首屏背景或图表卡露出“问题3”式标题。
- 更新运行解读与总控入口：
  - `2025/llm/result_context.py` 的任务标题改为工程链路名。
  - `2025/llm/prompts.py` 和 `2025/llm/assistant.py` 改为工程交付/运行解读口吻。
  - `2025/llm/assistant.py` 新增 `compatible-http` provider 名称，支持文档中的中性配置示例。
  - `2025/run_project.py --list` 输出改为站点机理诊断、历史功率基线、气象预报融合、运行场景归因、局地校正融合。
- 更新文档与测试：
  - 同步 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md` 的公开说明。
  - 更新 `tests/test_project_health.py`，增加新链路名、运行视角和旧“问题 2/3/4”公开文案缺失检查。

### 验证结果

- `python -m py_compile 2025\app.py 2025\run_project.py 2025\llm\assistant.py 2025\llm\result_context.py 2025\llm\prompts.py 2025\software_launcher.py`：通过。
- `python 2025\app.py`：通过，只输出正确 Streamlit 启动提示。
- `python 2025\run_project.py --list`：通过，任务列表已按工程链路显示。
- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、缺失相对输入或受管输出问题；仍保留两组已知历史实验副本重复。
- `python -m unittest discover -s tests -q`：通过，21 个测试 OK。
- `python 2025\run_project.py --show all`：通过，能读取五条工程链路的已有输出。
- `npx playwright screenshot --wait-for-timeout=7000 --viewport-size=1440,1100 http://127.0.0.1:8510 tmp\pv_engineering_desktop.png`：通过，桌面工作台首屏正常。
- `npx playwright screenshot --wait-for-timeout=7000 --viewport-size=390,900 http://127.0.0.1:8511 tmp\pv_engineering_mobile.png`：通过，移动端首屏无明显遮挡。
- `npx playwright screenshot --wait-for-timeout=1500 --viewport-size=1440,1100 file:///.../docs/index.html tmp\pages_engineering.png`：通过，静态页首屏正常，旧图题不再露出。

### 后续注意事项

- 本轮不重训模型，不改变 CSV 指标与 checkpoint；展示结果仍以仓库现有 `outputs/` 为准。
- 静态 Pages 的原生 JS 视角切换已写入页面；额外 Node 点击测试因当前环境无法直接 `require('playwright')` 未执行成功，但 Playwright CLI 截图验证已通过。
- 底层文件夹和脚本名仍保留 `problemN_...` 历史前缀，避免破坏复现路径；前台和公开文档按工程链路解释这些文件。

## 2026-07-01 去 AI 味、预测工作台与 GitHub Pages 静态页优化

### 调整目标

- 按用户要求通读项目现状后，继续把展示层从“AI 生成/总结页”调整为真实可复现的光伏日前预测项目工作台。
- 降低首屏、导航、功能入口和文档中的 AI 包装感，保留课程要求中的结果解释模块，但前台以“预测、指标、图表、受控复现、交付引用”为主。
- 新增 GitHub Pages 可发布的静态项目页，明确 Pages 只展示项目摘要和核心结果，完整 Streamlit 工作台仍需本地运行。

### 主要改动

- 优化 `2025/app.py`：
  - 将页面标题、导航和功能入口改为“预测工作台 / 代码与命令 / 结果解释”等工程化表达。
  - 移除前台“AI Foundations”“大模型问答”“生成摘要”等容易显得像 AI 包装的文案。
  - 将 Streamlit 已弃用的 `use_container_width` 替换为 `width="stretch"`，并把横向 `radio` 与设置类 `checkbox` 调整为 `segmented_control` 和 `toggle`。
- 新增 `.streamlit/config.toml`：
  - 为本地工作台配置项目级主题、字体、图表颜色、侧栏和控件边界，让原生控件与页面视觉一致。
- 新增 `docs/index.html` 与 `docs/assets/`：
  - 建立 GitHub Pages 静态展示页，直接展示真实预测曲线、问题 2/3/4 最优指标、本地运行命令和仓库材料入口。
  - 复制核心图像为 ASCII 文件名，避免 Pages 路径编码问题。
- 更新 `.gitignore`：
  - 忽略 `*.baiduyun.uploading.cfg`，避免百度云同步临时文件进入提交。
- 更新文档与测试：
  - 同步 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md`、`2025/CODE_AUDIT.md`、`2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`。
  - 扩展 `tests/test_project_health.py`，检查静态 Pages、主题配置、真实资产和弃用参数回归。

### 验证结果

- `python -m py_compile 2025\app.py 2025\software_launcher.py 2025\llm\assistant.py 2025\llm\result_context.py 2025\llm\prompts.py`：通过。
- `python 2025\app.py`：通过，只输出正确 Streamlit 启动提示。
- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、缺失相对输入或受管输出问题；仍保留两组已知历史实验副本重复。
- `python -m unittest discover -s tests -q`：通过，21 个测试 OK。
- `npx playwright screenshot --wait-for-timeout=6000 --viewport-size=1440,1100 http://127.0.0.1:8510 tmp\pv_workbench_desktop.png`：通过，桌面首屏正常。
- `npx playwright screenshot --wait-for-timeout=6000 --viewport-size=390,900 http://127.0.0.1:8510 tmp\pv_workbench_mobile.png`：通过，移动端首屏无明显遮挡。
- `npx playwright screenshot --wait-for-timeout=1000 --viewport-size=1440,1100 file:///.../docs/index.html tmp\pages_desktop.png`：通过，静态 Pages 首屏正常。

### 后续注意事项

- 本轮不改训练脚本、不重训模型，结果指标仍以现有 `outputs/` 为准。
- GitHub Pages 使用 `docs/` 静态源；Pages 无法运行 Streamlit，仓库 README 和页面中已明确本地运行命令。
- 后续如更新核心指标或替换图表，应同步更新 `docs/index.html` 和 `docs/assets/`。

## 2026-06-03 软件界面、交付引用与展示框架优化

### 调整目标

- 将 `2025/app.py` 从基础 Streamlit 控制台提升为更完整的软件化展示界面。
- 用项目真实预测图、指标表、论文材料和输出摘要组织首屏、结果页和交付引用页。
- 保持默认只读取已有 `outputs/`，不触发长时间模型训练，不写入或暴露 API 密钥。

### 主要改动

- 优化 `2025/app.py`：
  - 重做视觉系统，加入浅色玻璃质感、真实预测曲线首屏、精选图表、建模链路和更清晰的状态卡。
  - 新增 `FEATURED_VISUALS`、`REFERENCE_FILES` 和 `NAVIGATION`，集中管理页面导航、精选图表和交付材料引用。
  - 新增 `交付引用` 页面，索引题面、附件、最终论文、运行说明、代码索引、维护日志、各任务 `run_summary.json` 与指标表。
  - 增加 HTML 转义、图片 data URI、文件状态、文件大小和指标提升计算 helper，降低动态内容进入页面时的展示风险。
  - 结果页增加关键洞察卡，工作台增加真实图表预览和从题面到交付的流程节点。
- 更新项目文档：
  - `README.md`
  - `2025/README.md`
  - `2025/RUN_GUIDE.md`
  - `2025/CODE_INDEX.md`
  - `2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`
- 更新 `tests/test_project_health.py`：
  - 增加 UI 外壳、精选图表和交付引用页的轻量回归检查。

### 验证结果

- `python -m py_compile 2025\app.py 2025\software_launcher.py 2025\llm\assistant.py 2025\llm\result_context.py`：通过。
- `python 2025\app.py`：通过，仍只输出正确 Streamlit 启动提示。
- `python 2025\tools\project_health_check.py`：通过，未发现解析错误、缺失相对输入或受管输出问题。
- `python -m unittest discover -s tests -q`：通过，19 个测试 OK。
- `npx playwright screenshot --wait-for-timeout=6000 --viewport-size=1440,1100 http://localhost:8510 tmp\pv_ui_desktop.png`：通过，桌面首屏渲染正常。
- `npx playwright screenshot --wait-for-timeout=6000 --viewport-size=390,900 http://localhost:8510 tmp\pv_ui_mobile.png`：通过，移动端首屏无明显遮挡。

### 后续注意事项

- 当前优化只改展示层、文档和测试，不改训练脚本、不重训模型。
- 后续如果继续拆分框架，可把 `app.py` 中的 UI 常量、引用索引和页面渲染函数分离为 `ui/` 子模块。
- 若新增提交材料或重跑输出，应同步更新 `REFERENCE_FILES` 或确认 `collect_reference_rows()` 能覆盖新文件。

## 2026-06-03 桌面启动器双击无反应修复

### 调整目标

- 排查用户双击 `2025\start_software.vbs` 后系统没有反应的问题。
- 修复启动器静默失败，让后续桌面启动入口可见、可诊断。

### 问题原因

- `2025/software_launcher.py` 在创建 Tkinter 日志区域时使用了 `Frame(..., pady=(0, 18))`。
- Tkinter 的 `Frame` 构造参数不接受元组形式的 `pady`，启动时抛出 `_tkinter.TclError: bad screen distance "0 18"`。
- `2025/start_software.vbs` 使用 `pythonw.exe` 启动，`pythonw` 没有控制台，因此异常被隐藏，表现为双击后没有任何反应。
- VBS 还把 `shell.Run` 的窗口样式设为 `0`，即隐藏窗口；即便启动器正常，也存在窗口被隐藏的风险。

### 主要改动

- 修复 `2025/software_launcher.py`：
  - 将 `Frame(..., pady=(0, 18))` 改为 `Frame(...); pack(..., pady=(0, 18))`。
  - 在主入口增加最后兜底异常捕获，将启动异常写入 `2025/launcher_error.log`，并尝试用消息框提示错误。
- 修复 `2025/start_software.vbs`：
  - 将 `shell.Run command, 0, False` 改为 `shell.Run command, 1, False`，确保 `pythonw` 启动的桌面窗口可见。
- 更新 `tests/test_project_health.py`：
  - 增加 VBS 启动样式检查，防止无终端入口再次隐藏启动器窗口。

### 验证结果

- `python -m py_compile 2025\software_launcher.py 2025\app.py 2025\llm\assistant.py`：通过。
- `python 2025\tools\project_health_check.py`：通过，未发现解析错误、缺失相对输入或受管输出问题。
- `python -m unittest discover -s tests -q`：通过，18 个测试 OK。
- `python -m pip check`：通过，未发现损坏依赖。
- `git -c core.longpaths=true diff --check`：通过，仅提示 Git 后续可能将部分 LF 转为 CRLF。
- `Start-Process python 2025\software_launcher.py`：启动器进程保持运行，测试后手动停止。
- `cscript //nologo 2025\start_software.vbs`：退出码 0，能启动 `pythonw.exe` 启动器进程，测试后手动停止。

### 后续注意事项

- 后续若双击仍失败，优先查看 `2025\launcher_error.log`，该文件会记录 GUI 启动前的 Python 异常。
- 不要再把 `2025\start_software.vbs` 的 `shell.Run` 窗口样式改回 `0`，否则桌面入口可能再次表现为无响应。

## 2026-06-03 Codex API 接入、Skills 安装与界面优化

### 调整目标

- 按用户要求查找本机 Codex API 接入配置，并将其接入课程项目软件。
- 通过全网/skills.sh 检索并安装与软件、前端、UI、Streamlit 相关的 skills。
- 在不触发模型重训的前提下，对 Streamlit 软件的框架、界面、逻辑和大模型接入体验做一轮全面提升。

### 主要改动

- 安装/确认本机 skills：
  - 已有 `developing-with-streamlit`、`frontend-design`、`web-design-guidelines`、`vercel-react-best-practices` 等技能。
  - 新安装 `streamlit`、`ui-design-system`、`ui-design-review`、`frontend-ui-ux-design`、`frontend-design-system` 到 `~\.agents\skills\`。
  - `streamlit/agent-skills` 仓库实际只暴露 `developing-with-streamlit`，本机已存在；部分 PromptScript 目标提示不支持全局安装，但 Codex 可读的 skill 目录已完成复制。
- 接入本机 Codex 配置：
  - `2025/llm/assistant.py` 现在会在未显式设置 `PV_LLM_PROVIDER` 时自动读取 `~\.codex\config.toml` 和 `~\.codex\auth.json`。
  - 支持 Codex 配置中的 Responses API，即 `/v1/responses`。
  - 密钥只从本机 auth 或环境变量读取，不写入仓库、README 或日志。
  - 保留 Chat Completions、OpenAI-compatible、本地端点和离线模板兜底。
- 优化 `2025/app.py`：
  - 工作台增加任务状态总览、项目流程带、LLM 接入状态和更清晰的指标卡。
  - 大模型配置面板显示 provider、model、wire API、endpoint 和配置来源，但不把密钥明文预填到输入框。
  - 页面视觉从简单展示页调整为更像工程控制台的软件界面。
- 更新 `.gitignore`，忽略 `.env`、`.env.*`、`2025/.env.local` 等本地密钥配置文件。
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md`、`2025/CODE_AUDIT.md` 和 `2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`，同步 Codex 自动接入、Responses API 和密钥保护说明。
- 更新 `tests/test_project_health.py`，增加临时 `CODEX_HOME` 下读取 Codex Responses 配置的回归测试。

### 验证结果

- `python -m py_compile 2025\app.py 2025\llm\assistant.py 2025\llm\result_context.py 2025\llm\prompts.py 2025\software_launcher.py`：通过。
- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、未解析相对输入或受管理输出问题。
- `python -m unittest discover -s tests -q`：18 个测试通过。
- `python -m pip check`：通过。
- Streamlit 版本检查：`streamlit==1.58.0`，支持 `st.segmented_control`。
- Codex 配置读取检查：自动识别 `codex-config`、`gpt-5.5`、`responses`、`/v1/responses`，密钥状态为已读取；未记录密钥内容。
- 远程大模型调用检查：通过 `codex-config` 成功返回中文确认。
- Streamlit HTTP 烟测：`http://127.0.0.1:8510/_stcore/health` 返回 `ok`。
- Playwright 桌面截图：`tmp\pv_dashboard_8510_wait.png`，首屏标题、任务状态和流程卡正常渲染。
- Playwright 移动端截图：`tmp\pv_dashboard_8510_mobile_auto.png`，侧栏默认收起，主内容可读。

## 2026-06-03 GitHub 推送规则固化与本轮推送

### 调整目标

- 按用户要求将本轮“软件化入口”相关修改提交并推送到 GitHub。
- 在当前项目文件夹内固化协作规则，让后续新对话也能遵守：重要修改需要详细改动备注、验证、提交和推送确认。

### 主要改动

- 新增 `AGENTS.md`：
  - 明确后续代理维护本仓库时，应优先遵守项目级协作规则。
  - 规定用户要求推送 GitHub 时，需要检查分支和远程仓库、更新 `PROJECT_LOG.md`、同步相关文档、运行轻量验证、使用清晰 Conventional Commit，并在推送后确认远程同步状态。
  - 规定课程演示入口优先使用 `2025\start_software.vbs`，`2025\run.bat` 作为调试入口。
- 更新 `README.md`：
  - 在目录结构中加入 `AGENTS.md`。
  - 补充项目级协作规则入口和后续改动记录要求。

### 验证结果

- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、未解析相对输入或受管理输出问题。
- `python -m unittest discover -s tests -q`：17 个测试通过。
- `python -m py_compile 2025\software_launcher.py 2025\app.py 2025\llm\__init__.py 2025\llm\assistant.py 2025\llm\prompts.py 2025\llm\result_context.py`：通过。
- `python -m pip check`：通过。

## 2026-06-03 无终端桌面启动器

### 调整目标

- 将课程展示入口进一步改造成“可双击打开的软件”，避免演示时只出现命令行窗口。
- 保留原 `run.bat` 作为依赖安装和命令行调试入口，同时新增更适合演示视频和教师复现的桌面启动入口。

### 主要改动

- 新增 `2025/software_launcher.py`：
  - 使用 Tkinter 提供桌面启动器窗口。
  - 可启动后台 Streamlit 服务、打开浏览器控制台、运行 `tools/project_health_check.py`、停止后台服务。
  - 启动 Streamlit 时使用隐藏窗口参数，并自动选择 8501 附近可用端口。
- 新增 `2025/start_software.vbs`：
  - 双击后优先通过 `pythonw.exe` 启动桌面启动器，避免先出现黑色终端。
  - 若 `pythonw.exe` 不可用，则回退到 `python.exe`，便于暴露错误信息。
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md` 和 `2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`，明确演示优先使用 `start_software.vbs`，调试再用 `run.bat`。
- 更新 `tests/test_project_health.py`，增加桌面启动器语法检查和 VBS 入口引用检查。

### 验证结果

- `python -m py_compile 2025\software_launcher.py 2025\app.py 2025\llm\__init__.py 2025\llm\assistant.py 2025\llm\prompts.py 2025\llm\result_context.py`：通过。
- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、未解析相对输入或受管理输出问题。
- `python -m unittest discover -s tests -q`：17 个测试通过。
- `python -m pip check`：通过。
- `python 2025\app.py`：只输出正确 Streamlit 启动提示。
- `software_launcher.py` 非 GUI 导入检查：通过，能识别 `D:\Software\Python312\python.exe` 与已安装的 Streamlit。
- `python -m streamlit run 2025\app.py --server.headless true --server.port 8506 --browser.gatherUsageStats false`：HTTP 烟测通过，`/_stcore/health` 返回 `ok`。

## 2026-06-03 Streamlit 软件控制台增强与本地 Codex 接入

### 调整目标

- 检查用户直接运行 `python app.py` 后出现的 Streamlit bare mode 日志，避免 `missing ScriptRunContext` 警告误导。
- 将展示层从简单结果页增强为课程项目软件控制台，补齐本地代码交互、结果浏览、LLM 聊天和受保护运行控制。
- 支持本地 Codex 或其他 OpenAI-compatible HTTP 接口，同时保留离线模板兜底，保证演示稳定。
- 按用户要求通过网络检索并安装适合 Streamlit 开发的官方 skill；本轮安装了 `streamlit/agent-skills@developing-with-streamlit`，Codex 重启后可自动加载。

### 主要改动

- 重构 `2025/app.py`：
  - 新增工作台、运行结果、本地代码交互、大模型问答、运行控制五个页面。
  - 直接运行 `python 2025\app.py` 时只输出正确启动命令，不再触发 Streamlit bare mode 警告。
  - 本地代码交互页支持查看项目内文本/代码文件，执行 `--list`、`--show`、`--dry-run` 等固定安全命令，并可把当前代码片段加入问答上下文。
  - 运行控制页默认只查看已有输出或 dry-run，真正运行任务前需要显式勾选确认。
- 扩展 `2025/llm/assistant.py`：
  - 支持 `local-codex`、`codex`、`local`、`openai-compatible` 等 provider。
  - 支持从 `PV_LLM_*`、`CODEX_LLM_*`、`OPENAI_*` 环境变量读取模型、API Key 和接口地址。
  - 本地兼容端点允许空 API Key；官方/远程模式仍要求密钥。
  - 支持聊天历史和额外代码上下文。
- 更新 `tests/test_project_health.py`：
  - 增加本地 Codex 端点配置测试。
  - 增加 `python 2025\app.py` 直接运行保护测试。
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md`、`2025/CODE_AUDIT.md`、`2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`，同步新软件入口和本地大模型配置说明。

### 验证结果

- `python -m py_compile 2025\app.py 2025\llm\__init__.py 2025\llm\assistant.py 2025\llm\prompts.py 2025\llm\result_context.py`：通过。
- `python 2025\tools\project_health_check.py`：通过，未发现 Python 解析错误、未解析相对输入或受管理输出问题。
- `python -m unittest discover -s tests -q`：15 个测试通过。
- `python 2025\run_project.py --show all`：通过，能读取问题 1-4 和问题 3 二次分析已有输出。
- `python -m pip check`：通过。
- `python 2025\app.py`：只输出正确 Streamlit 启动提示，不再出现 `missing ScriptRunContext`。
- `python -m streamlit run 2025\app.py --server.headless true --server.port 8504 --browser.gatherUsageStats false`：HTTP 烟测通过。

## 2026-06-03 课程交付展示层与大模型辅助模块

### 调整目标

- 补齐期末大作业通知要求中的 `llm/` 大模型模块、`app.py` 交互界面、`run.bat` 一键运行脚本和精确版本依赖。
- 在不改动现有问题 1-4 训练脚本的前提下，新增一个稳定的演示入口，默认读取已有 `outputs/`，避免课堂演示误触发长时间训练。
- 为报告和演示视频提供可直接展示的结果解读、指标说明和图表浏览界面。

### 主要改动

- 新增 `2025/llm/`：
  - `result_context.py` 读取各问题 `run_summary.json` 与指标 CSV，整理为项目上下文。
  - `assistant.py` 提供离线优先的大模型辅助解读；配置 `PV_LLM_PROVIDER`、`PV_LLM_API_KEY`、`PV_LLM_MODEL`、`PV_LLM_BASE_URL` 后可调用兼容聊天接口。
  - `prompts.py` 保存项目问答和报告摘要提示词模板。
- 新增 `2025/app.py`：Streamlit 结果控制台，包含项目总览、指标表、图表展示、大模型解读和运行控制页面。
- 新增 `2025/run.bat`：Windows 双击启动脚本，会检查 Python/Streamlit 并启动 `app.py`。
- 将 `2025/requirements.txt` 改为固定版本运行依赖，并新增 `2025/requirements-optional.txt` 保存可选实验依赖。
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md`、`2025/CODE_AUDIT.md` 和 `2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`，同步新的交付入口。
- 更新 `tests/test_project_health.py`，增加 LLM 上下文读取、离线兜底、`app.py` 语法和固定版本依赖检查。

## 2026-06-03 期末大作业要求阅读与适配分析

### 调整目标

- 阅读根目录《人工智能基础B》期末大作业布置通知.pdf，梳理提交材料、评分结构、代码包目录和演示要求。
- 结合 `2025` 当前代码、文档、输出摘要、A 题题面、附件 1 和既有最终论文，判断项目距离期末大作业交付还差哪些材料。
- 形成后续改造路线图，避免只继续优化算法而漏掉大模型、交互界面、一键脚本、视频和报告结构等评分项。

### 主要改动

- 新增 `2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`：
  - 记录截止时间、组队、提交包命名、200M 体积限制、项目主报告、代码包、演示视频和补充材料要求。
  - 将主报告 5 个评分模块逐项映射到当前项目，标出可复用内容和必须补齐的内容。
  - 分析 A 题四问、测试集划分、15 分钟预测表和附件 1 指标在当前项目中的完成度。
  - 总结当前项目优势、短板、风险点和推荐改造路线。
- 更新根目录 `README.md`，增加作业要求分析文档入口。

### 阅读结论

- 当前项目已经较好覆盖 A 题算法主线：问题 1-4、附件指标、统一输出、checkpoint 复用和总控入口基本齐备。
- 期末大作业交付层面仍需补齐：`llm/` 大模型模块、`app.py` 或等价交互界面、`run.bat` 一键启动脚本、精确版本依赖、团队分工、功能/性能/稳定性测试表、3 分钟演示视频和课程项目式主报告。
- 当前 `2025` 目录约 240.38MB，最终压缩包是否低于 200M 需要正式打包验证，必要时应精简历史工作区或大型输出。
- 既有 71 页论文可作为素材，但不是可直接提交的课程主报告；其后部代码附录和部分问题 4 指标与当前优化后的代码/结果不完全一致，后续需要统一更新。

## 2026-06-03 项目总控入口与并行运行开关

### 调整目标

- 明确问题 1-4 的实际依赖关系，避免误以为必须按 1、2、3、4 严格串行运行。
- 新增一个开关式入口，支持选择运行某一问、并行运行互不依赖的问题、查看已有结果。
- 对真正存在依赖的 `3-analysis` 做显式保护，避免缺少问题 2 或问题 3 预测表时误跑场景分析。

### 主要改动

- 新增 `2025/run_project.py`：
  - `--run 1|2|3|4|3-analysis|main|all` 选择运行任务。
  - `--parallel` 并行运行问题 1、2、3 主训练和问题 4 等互不依赖任务。
  - `--show` 读取 `outputs/` 下已有 `run_summary.json`、指标表和预测表路径，不触发训练。
  - `--dry-run` 打印拓扑批次，便于长时间运行前确认执行计划。
  - 支持 `--force-retrain`、`--epochs`、`--patience`、`--batch-size`、`--hidden-dim`、`--q4-modes`、`--q4-models`、`--q4-fast` 等运行参数。
- 更新 `tests/test_project_health.py`，增加总控入口的别名展开、依赖顺序和问题 3 场景分析依赖检查。
- 更新 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md` 和 `2025/CODE_AUDIT.md`，记录总控入口和并行运行关系。

## 2026-06-02 问题 4 输入特征消融脚本运行测试与优化

### 调整目标

- 实际运行 `problem4_feature_ablation_forecast.py`，修复旧脚本长时间训练、预测口径不严谨和输出图表分散的问题。
- 将问题 4 明确为“前一日实测功率 + 目标日天气特征序列”预测目标日 96 点功率，对比 NWP、LMD 和 NWP+LMD 三类输入。
- 同步正式入口和 `01_modeling_workspace/pvod_full_experiment/problem4_feature_ablation_forecast.py`，保证备用入口不再保留旧实现。

### 主要改动

- 重构 `problem4_feature_ablation_forecast.py`：
  - 构造严格日前样本，预测表统一为 `起报时间=目标日前一日 00:00`、`预报时间=目标日 96 个 15 分钟点`。
  - 对 NWP 与 LMD 风向分别分解为 `wind_x/wind_y`，三类输入维度分别为 `nwp=9`、`lmd=8`、`mixed=16`。
  - 修复旧版 `FusionModel` 只读取首列输入的问题，LSTM、TCN 和 MLP 分支现在使用完整多变量序列。
  - 训练目标按 `train_Y.max()` 归一化，避免误用输入最大值；checkpoint 签名纳入架构版本、输入模式、输入维度和特征列表。
  - 新增本地 MSVC runtime 目录兜底，避免 Windows 环境下 PyTorch `c10.dll` 初始化失败。
  - 新增 `PV_Q4_MODES`、`PV_Q4_MODELS`、`PV_Q4_SAVE_RUN_DIAGNOSTICS` 和通用 `PV_FORECAST_*` 环境变量入口。
  - 输出统一写入 `models/` 与 `outputs/predictions/`、`outputs/metrics/`、`outputs/figures/`、`outputs/reports/`。
- 优化结果呈现：
  - 生成输入消融热力图、误差柱状图、准确率/合格率随输入维度变化图、雷达图、逐模式预测曲线、误差分布、散点图、误差分析矩阵和交互式 HTML。
  - 热力图按“误差越小、相关/准确/合格率越高”归一化着色，保留原始指标数值标注。
  - 已清理旧版问题4遗留的重复专业曲线图和旧命名热力图。

### 验证结果

- `python 2025\02_problem_solutions\problem4_feature_ablation\problem4_feature_ablation_forecast.py`：通过，三种输入模式均复用 `models/problem4_FusionModel_*.pth` checkpoint，约 95.5 秒完成完整诊断刷新。
- 问题 4 当前默认白昼指标：
  - `FusionModel_nwp`：`E_rmse=0.0879`，`C_R=91.21%`，`Q_R=96.94%`。
  - `FusionModel_lmd`：`E_rmse=0.0584`，`C_R=94.16%`，`Q_R=99.68%`。
  - `FusionModel_mixed`：`E_rmse=0.0465`，`C_R=95.35%`，`Q_R=99.84%`，当前综合表现最好。
- 已视觉抽查 `Q4_模型输入对比结果热力图.png`、`FusionModel_mixed_daylight_forecast_curve.png`、`FusionModel_mixed_error_analysis_matrix.png` 和 `C_R_vs_输入特征维度.png`，图像非空且无明显遮挡。

## 2026-06-02 问题 3 气象特征预测脚本运行测试与优化

### 调整目标

- 实际运行 `problem3_weather_feature_forecast.py`，解决训练超时、PyTorch 运行库和输出错位问题。
- 将问题 3 建模口径明确为“前一日实测功率 + 目标日 NWP 气象序列”预测目标日功率，避免目标日功率泄漏。
- 统一问题 3 主训练和二次分析脚本的标准输出路径、目标日时间对齐和中文期刊图像质量。

### 主要改动

- 修复运行环境：
  - 发现上一轮超时后遗留的问题 2 Python 训练进程仍在后台运行并改动模型文件，已终止该遗留进程。
  - 当前系统 `MSVCP140.dll` 版本较旧，直接导入 PyTorch 会触发 `c10.dll` 初始化失败；问题 3 主脚本新增本地 MSVC runtime 目录兜底，优先使用 `sklearn/.libs` 中的新运行库。
- 重构 `problem3_weather_feature_forecast.py`：
  - 输入窗口改为前一日 `power_scaled` 与目标日 NWP 气象特征序列组合。
  - 修正训练窗口遍历边界，纳入最后一个合法训练样本，当前训练窗口数为 25253。
  - 测试集改为 2、5、8、11 月最后 7 天的严格目标日样本，共 28 天。
  - 预测表改为 `起报时间=目标日前一日 00:00`，`预报时间=目标测试日 96 个 15 分钟点`。
  - 训练目标按功率最大值归一化，输入特征保留训练集拟合的 MinMax 缩放结果。
  - 默认训练参数改为 `epochs=20`、`batch_size=128`、`patience=4`，并支持 `PV_FORECAST_*` 环境变量。
  - 输出非负功率裁剪、checkpoint 复用状态、输入特征、测试日期范围和白昼指标写入 `run_summary.json`。
  - 图像改为共享中文期刊风格；指标热力图按“误差越小、相关/准确/合格率越高”归一化着色，单日曲线严格限制在目标日 00:00-23:45。
- 修复问题 3 二次分析脚本：
  - `problem3_extended_scenario_analysis.py`、`problem3_integrated_scenario_analysis.py`、`problem3_scenario_ieee_analysis.py` 优先读取标准 `outputs/predictions/` 下的问题 2 和问题 3 预测表。
  - 场景天气特征按 `预报时间` 对应的目标日合并，不再按起报日前一日合并。
  - `problem3_three_model_curve_plot.py` 按目标日提取典型曲线。
  - 二次分析脚本写入独立 `problem3_*_summary.json`，不再覆盖主训练 `run_summary.json`。
  - 场景分组图、特征重要性图和典型场景对比图统一使用共享调色板、零基准线和期刊式坐标轴。

### 验证结果

- `python 2025\02_problem_solutions\problem3_scenario_analysis\problem3_weather_feature_forecast.py`：完整训练通过，三模型 checkpoint、预测表、指标表、静态 PNG、交互 HTML 和 `run_summary.json` 均已生成。
- 再次运行 `python 2025\02_problem_solutions\problem3_scenario_analysis\problem3_weather_feature_forecast.py`：三模型均成功复用 `models/problem3_*.pth`，约 45.7 秒完成。
- 问题 3 当前白昼指标：
  - PureLSTM：`E_rmse=0.0796`，`E_mae=0.0574`，`C_R=92.04%`，`Q_R=99.11%`。
  - FusionModel：`E_rmse=0.0699`，`E_mae=0.0509`，`C_R=93.01%`，`Q_R=99.76%`，当前综合表现最好。
  - BiFusionModel：`E_rmse=0.0844`，`E_mae=0.0610`，`C_R=91.56%`，`Q_R=98.55%`。
- `problem3_extended_scenario_analysis.py`、`problem3_integrated_scenario_analysis.py`、`problem3_scenario_ieee_analysis.py`、`problem3_three_model_curve_plot.py`：均通过；当前环境未安装可选依赖 `shap`，SHAP 分支按脚本逻辑跳过。
- 已视觉抽查 `三模型评估指标热力图_白昼时段.png`、`三模型绘图.png`、`六类分组_IEEE风格.png`、`特征重要性分析.png`，图像非空且无明显遮挡。
- `python 2025\tools\project_health_check.py`：通过。
- `python -m unittest discover -s tests -q`：通过，6 个测试全部成功。

## 2026-06-02 问题 2 基准预测脚本运行测试与优化

### 调整目标

- 实际运行 `problem2_baseline_three_model_forecast.py`，复现并解决阻塞运行的问题。
- 修正问题 2 预测明细表的时间对齐口径，避免模型预测、实际功率和预报时间错日。
- 在保持 checkpoint 复用的前提下提升输出图像、运行摘要和结果可读性。

### 主要改动

- 运行环境补齐 PyTorch：当前 Python 3.12 环境缺少 `torch`，已安装 `torch 2.12.0` 后完成脚本回归。
- 优化问题 2 主脚本：
  - 删除局部 `SimHei`、`sns.set_theme()` 和重复导入，统一使用 `_shared/pv_project.py` 的中文期刊绘图配置。
  - 增加 `PV_FORECAST_EPOCHS`、`PV_FORECAST_PATIENCE`、`PV_FORECAST_BATCH_SIZE`、`PV_FORCE_RETRAIN` 等运行参数入口。
  - 预测输出后裁剪到物理可行的非负功率区间。
  - 预测表改为 `起报时间=目标日前一日 00:00`，`预报时间=目标测试日 96 个 15 分钟点`，实际功率直接与 `test_Y` 同日对齐。
  - `run_summary.json` 新增测试日期范围、训练参数、checkpoint 复用状态、白昼标量误差和模型文件清单。
  - 三模型指标热力图按列归一化着色并保留原始数值标注，日内曲线改用 0-24 小时数值轴，避免 Matplotlib datetime 轴出现小时偏移。
  - 生成静态 PNG 与 Plotly HTML 交互曲线，统一写入 `outputs/figures/`。
- 更新 `2025/RUN_GUIDE.md` 和 `2025/CODE_INDEX.md`，记录问题 2 时间对齐口径和运行参数。

### 验证结果

- `python -u 2025\02_problem_solutions\problem2_baseline_forecasting\problem2_baseline_three_model_forecast.py`：通过，三模型均复用 checkpoint。
- 问题 2 当前白昼指标：
  - PureLSTM：`E_rmse=0.1141`，`C_R=88.59%`，`Q_R=96.05%`。
  - FusionModel：`E_rmse=0.0833`，`C_R=91.67%`，`Q_R=98.07%`。
  - BiFusionModel：`E_rmse=0.0967`，`C_R=90.33%`，`Q_R=97.99%`。
- `python 2025\tools\project_health_check.py`：通过。
- `python -m unittest discover -s tests -q`：通过，6 个测试全部成功。

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
