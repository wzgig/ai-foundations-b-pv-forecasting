# 项目协作规则

本文件是当前项目的代理协作说明。后续在本仓库内的新对话和维护任务，应优先遵守这里的规则。

## GitHub 推送与改动备注

- 当用户要求把修改推送到 GitHub 时，必须先确认 `git status --short --branch` 和远程仓库。
- 每次重要代码、文档、入口脚本或项目结构调整，都必须在根目录 `PROJECT_LOG.md` 追加或更新详细改动备注。
- `PROJECT_LOG.md` 的备注至少包含：调整目标、主要改动、验证命令与结果、后续注意事项。
- 若改动影响文件名、入口脚本、运行流程或提交材料说明，必须同步更新相关文档，例如 `README.md`、`2025/README.md`、`2025/RUN_GUIDE.md`、`2025/CODE_INDEX.md`、`2025/ASSIGNMENT_REQUIREMENTS_ANALYSIS.md`。
- 推送前优先运行轻量验证：
  - `python 2025\tools\project_health_check.py`
  - `python -m unittest discover -s tests -q`
- 提交时使用清晰的 Conventional Commit 信息，并在提交正文中写明主要变更和验证结果。
- 推送后必须确认本地分支与 `origin/main` 同步，并向用户说明提交哈希、推送目标和验证结果。

## 项目维护边界

- 不要回滚用户已有改动；遇到无关脏文件时保留并说明。
- 不要在普通展示或文档任务中触发长时间模型重训；需要重训时必须由用户明确确认。
- 当前课程演示入口优先使用 `2025\start_software.vbs`；`2025\run.bat` 保留为命令行调试入口。
