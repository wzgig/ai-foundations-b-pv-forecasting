# 运行验证记录

验证时间：2026-07-03
验证环境：Windows PowerShell，Python 3.12

| 检查项 | 命令或方式 | 结果 |
| --- | --- | --- |
| 核心 Python 语法检查 | `python -m py_compile 2025\app.py 2025\run_project.py 2025\llm\assistant.py 2025\llm\result_context.py 2025\llm\prompts.py 2025\software_launcher.py` | 通过 |
| 项目健康检查 | `python 2025\tools\project_health_check.py` | 通过，无解析错误，无受管输出问题 |
| 单元测试 | `python -m unittest discover -s tests -q` | 25 项通过 |
| 任务列表 | `python 2025\run_project.py --list` | 可列出站点机理诊断、历史功率基线、气象预报融合、运行场景归因、局地校正融合 |
| 结果汇总 | `python 2025\run_project.py --show all` | 可读取各链路摘要、指标和预测表 |
| 报告 PDF | `人工智能基础B_王子成组.pdf` | 16 页，约 1.31MB |
| 演示视频 | `人工智能基础B项目视频.mp4` | 00:02:58，1080P，约 59.7MB |

说明：Q4 三输入指标表已从已有预测 CSV 重新汇总，未触发重新训练；当前最优为 `FusionModel_mixed`。
