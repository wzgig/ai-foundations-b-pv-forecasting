# tools 维护脚本

本目录保存不直接训练模型、但用于维护项目质量和交付物的脚本。

| 文件 | 用途 |
| --- | --- |
| `project_health_check.py` | 静态健康检查：Python 解析、重复代码快照、相对输入路径和受管输出约束。 |
| `generate_csust_report.py` | 从 `05_delivery/项目主报告_终稿.md` 生成按长沙理工大学样张排版的 Word 报告。 |
| `export_csust_report.ps1` | 调用生成器、更新 Word 目录/页码、导出 PDF，并在可用时渲染检查页。 |

常用命令：

```powershell
python 2025\tools\project_health_check.py
.\2025\tools\export_csust_report.ps1
```

维护脚本应保持可重复、无密钥、无远程依赖。临时渲染图写入根目录 `tmp/`，不进入 Git。
