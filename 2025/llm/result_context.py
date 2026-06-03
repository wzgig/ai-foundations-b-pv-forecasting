# -*- coding: utf-8 -*-
"""Read existing experiment outputs and prepare compact LLM context."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
UTF8_SIG = "utf-8-sig"


@dataclass(frozen=True)
class TaskSpec:
    key: str
    title: str
    report: Path
    metrics: Path | None
    output_dir: Path


@dataclass(frozen=True)
class TaskContext:
    key: str
    title: str
    report_path: Path
    metrics_path: Path | None
    output_dir: Path
    metadata: dict[str, Any]
    artifacts: dict[str, list[str]]
    metric_rows: list[dict[str, str]]

    @property
    def report_exists(self) -> bool:
        return self.report_path.exists()

    @property
    def metrics_exists(self) -> bool:
        return self.metrics_path is not None and self.metrics_path.exists()

    @property
    def primary_label(self) -> str:
        if not self.metric_rows:
            return "无指标记录"
        row = self.metric_rows[0]
        for key in ("模型_输入", "模型", "Model", "method", "index"):
            if row.get(key):
                return row[key]
        return next(iter(row.values()), "无指标记录")


TASK_SPECS = [
    TaskSpec(
        key="1",
        title="问题1 数据分析与理论功率",
        report=ROOT / "02_problem_solutions" / "problem1_data_analysis" / "outputs" / "reports" / "run_summary.json",
        metrics=ROOT / "02_problem_solutions" / "problem1_data_analysis" / "outputs" / "metrics" / "problem1_daylight_error_metrics.csv",
        output_dir=ROOT / "02_problem_solutions" / "problem1_data_analysis" / "outputs",
    ),
    TaskSpec(
        key="2",
        title="问题2 历史功率基准预测",
        report=ROOT / "02_problem_solutions" / "problem2_baseline_forecasting" / "outputs" / "reports" / "run_summary.json",
        metrics=ROOT / "02_problem_solutions" / "problem2_baseline_forecasting" / "outputs" / "metrics" / "三模型白昼指标对比.csv",
        output_dir=ROOT / "02_problem_solutions" / "problem2_baseline_forecasting" / "outputs",
    ),
    TaskSpec(
        key="3",
        title="问题3 融入NWP信息预测",
        report=ROOT / "02_problem_solutions" / "problem3_scenario_analysis" / "outputs" / "reports" / "run_summary.json",
        metrics=ROOT / "02_problem_solutions" / "problem3_scenario_analysis" / "outputs" / "metrics" / "三模型白昼指标对比.csv",
        output_dir=ROOT / "02_problem_solutions" / "problem3_scenario_analysis" / "outputs",
    ),
    TaskSpec(
        key="3-analysis",
        title="问题3 场景划分与提升来源",
        report=ROOT / "02_problem_solutions" / "problem3_scenario_analysis" / "outputs" / "reports" / "problem3_scenario_ieee_analysis_summary.json",
        metrics=ROOT / "02_problem_solutions" / "problem3_scenario_analysis" / "outputs" / "metrics" / "场景划分提升分析结果.csv",
        output_dir=ROOT / "02_problem_solutions" / "problem3_scenario_analysis" / "outputs",
    ),
    TaskSpec(
        key="4",
        title="问题4 NWP空间降尺度输入消融",
        report=ROOT / "02_problem_solutions" / "problem4_feature_ablation" / "outputs" / "reports" / "run_summary.json",
        metrics=ROOT / "02_problem_solutions" / "problem4_feature_ablation" / "outputs" / "metrics" / "Q4_模型输入对比结果.csv",
        output_dir=ROOT / "02_problem_solutions" / "problem4_feature_ablation" / "outputs",
    ),
]


def project_relative(path: Path | str) -> str:
    target = Path(path)
    if not target.is_absolute():
        return target.as_posix()
    try:
        return target.relative_to(ROOT).as_posix()
    except ValueError:
        return str(target)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path | None, limit: int = 12) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding=UTF8_SIG, newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if index >= limit:
                break
            rows.append({key or "index": value for key, value in row.items()})
    return rows


def _normalize_artifacts(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[key] = [str(item) for item in value]
    return result


def collect_task_context(spec: TaskSpec) -> TaskContext:
    report = read_json(spec.report)
    metadata = report.get("metadata", {}) if isinstance(report.get("metadata", {}), dict) else {}
    artifacts = _normalize_artifacts(report.get("artifacts", {}))
    return TaskContext(
        key=spec.key,
        title=spec.title,
        report_path=spec.report,
        metrics_path=spec.metrics,
        output_dir=spec.output_dir,
        metadata=metadata,
        artifacts=artifacts,
        metric_rows=read_csv_rows(spec.metrics),
    )


def collect_all_context() -> dict[str, TaskContext]:
    return {spec.key: collect_task_context(spec) for spec in TASK_SPECS}


def compact_metric_row(row: dict[str, str]) -> str:
    label = row.get("模型_输入") or row.get("模型") or row.get("Model") or row.get("index") or "记录"
    parts = [label]
    for key in ("RMSE", "MAE", "MAPE", "E_rmse", "E_mae", "E_me", "r", "C_R", "Q_R", "RMSE_MW", "MAE_MW", "Correlation"):
        value = row.get(key)
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    return "；".join(parts)


def format_context_for_prompt(contexts: dict[str, TaskContext]) -> str:
    lines = ["项目上下文："]
    for task in contexts.values():
        lines.append(f"- {task.title}")
        lines.append(f"  摘要文件：{project_relative(task.report_path)}，存在={task.report_exists}")
        if task.metrics_path:
            lines.append(f"  指标文件：{project_relative(task.metrics_path)}，存在={task.metrics_exists}")
        if task.metadata:
            for key in ("problem", "models", "input_modes", "best_run_by_E_rmse", "best_models", "elapsed_seconds"):
                if key in task.metadata:
                    lines.append(f"  {key}: {task.metadata[key]}")
        for row in task.metric_rows[:5]:
            lines.append(f"  指标：{compact_metric_row(row)}")
    return "\n".join(lines)


def best_row_by_metric(task: TaskContext, metric: str = "E_rmse") -> dict[str, str] | None:
    rows = [row for row in task.metric_rows if row.get(metric) not in (None, "")]
    if not rows:
        return None

    def value(row: dict[str, str]) -> float:
        try:
            return float(row[metric])
        except (TypeError, ValueError):
            return float("inf")

    return min(rows, key=value)
