# 模型权重索引

模型权重用于直接复现实验输出和工作台展示，避免评阅时临时重训。

| 文件 | 对应链路 | 模型/输入 | 用途 |
| --- | --- | --- | --- |
| `problem2_PureLSTM.pth` | 历史功率基线 | PureLSTM | 作为单分支 LSTM 对照 |
| `problem2_FusionModel.pth` | 历史功率基线 | FusionModel | 历史功率链路最优模型 |
| `problem2_BiFusionModel.pth` | 历史功率基线 | BiFusionModel | 双向融合结构对照 |
| `problem3_PureLSTM.pth` | 气象预报融合 | PureLSTM + NWP | NWP 输入对照 |
| `problem3_FusionModel.pth` | 气象预报融合 | FusionModel + NWP | NWP 链路最优模型 |
| `problem3_BiFusionModel.pth` | 气象预报融合 | BiFusionModel + NWP | 深层融合对照 |
| `problem4_FusionModel_nwp.pth` | 局地校正融合 | FusionModel + NWP | Q4 仅 NWP 输入 |
| `problem4_FusionModel_lmd.pth` | 局地校正融合 | FusionModel + LMD | Q4 仅 LMD 输入 |
| `problem4_FusionModel_mixed.pth` | 局地校正融合 | FusionModel + NWP+LMD | Q4 最优输入 |

如果需要重新训练，可进入代码包执行：

```powershell
python 2025\run_project.py --run 2
python 2025\run_project.py --run 3
python 2025\run_project.py --run 4
```

提交演示建议优先读取已有权重和输出，避免长时间训练影响现场效果。
