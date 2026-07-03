# -*- coding: utf-8 -*-
"""Static health checks for the 2025 course project.

This intentionally does not execute training scripts.  It checks that scripts
are syntactically valid, reports duplicate code snapshots, and highlights
relative input files that are not present beside the script.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECT_INPUT_PATTERN = re.compile(r"(?:read_csv|read_excel|readtable)\(\s*['\"]([^'\"]+)['\"]")
ASSIGN_PATTERN = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*=\s*['\"]([^'\"]+)['\"]")
VARIABLE_INPUT_PATTERN = re.compile(r"(?:read_csv|read_excel|readtable)\(\s*([A-Za-z_]\w*)")
MANAGED_OUTPUT_SCRIPTS = {
    Path("02_problem_solutions/problem1_data_analysis/theoretical_power_baseline.py"),
    Path("02_problem_solutions/problem1_data_analysis/theoretical_power_calculation.py"),
    Path("02_problem_solutions/problem1_data_analysis/theoretical_power_diagnostics.py"),
    Path("02_problem_solutions/problem3_scenario_analysis/problem3_extended_scenario_analysis.py"),
    Path("02_problem_solutions/problem3_scenario_analysis/problem3_integrated_scenario_analysis.py"),
    Path("02_problem_solutions/problem3_scenario_analysis/problem3_scenario_ieee_analysis.py"),
    Path("02_problem_solutions/problem3_scenario_analysis/problem3_three_model_curve_plot.py"),
    Path("01_modeling_workspace/pvod_full_experiment/problem2_baseline_three_model_forecast.py"),
    Path("01_modeling_workspace/pvod_full_experiment/problem3_weather_feature_forecast.py"),
    Path("01_modeling_workspace/pvod_full_experiment/problem4_feature_ablation_forecast.py"),
    Path("02_problem_solutions/problem2_baseline_forecasting/problem2_baseline_three_model_forecast.py"),
    Path("02_problem_solutions/problem3_scenario_analysis/problem3_weather_feature_forecast.py"),
    Path("02_problem_solutions/problem4_feature_ablation/problem4_feature_ablation_forecast.py"),
}
DIRECT_OUTPUT_PATTERNS = {
    "direct_csv_write": re.compile(r"\.to_csv\s*\("),
    "matplotlib_show": re.compile(r"\bplt\.show\s*\("),
    "plotly_show": re.compile(r"\bfig\.show\s*\("),
    "direct_savefig": re.compile(r"\.savefig\s*\("),
}
IGNORED_CODE_PART_PREFIXES = ("06_",)


def is_generated_delivery_path(path: Path) -> bool:
    """Return True for generated submission-package copies under 2025/06_*."""

    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    return any(part.startswith(IGNORED_CODE_PART_PREFIXES) for part in relative.parts)


def iter_code_files() -> list[Path]:
    files = [*ROOT.rglob("*.py"), *ROOT.rglob("*.m")]
    return sorted(path for path in files if not is_generated_delivery_path(path))


def parse_python_files(paths: list[Path]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for path in paths:
        if path.suffix != ".py":
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
    return errors


def duplicate_code_groups(paths: list[Path]) -> list[dict[str, object]]:
    groups: dict[str, list[str]] = {}
    for path in paths:
        if path.suffix not in {".py", ".m"}:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        groups.setdefault(digest, []).append(str(path.relative_to(ROOT)))

    return [
        {"hash": digest, "paths": files}
        for digest, files in sorted(groups.items())
        if len(files) > 1
    ]


def unresolved_relative_inputs(paths: list[Path]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assigned_literals = dict(ASSIGN_PATTERN.findall(text))
        inputs = [match.group(1) for match in DIRECT_INPUT_PATTERN.finditer(text)]
        inputs.extend(
            assigned_literals[match.group(1)]
            for match in VARIABLE_INPUT_PATTERN.finditer(text)
            if match.group(1) in assigned_literals
        )

        for raw in sorted(set(inputs)):
            if re.match(r"^[a-zA-Z]:[\\/]", raw) or raw.startswith(("/", "\\")):
                continue
            if raw.startswith(("http://", "https://")):
                continue
            local = path.parent / raw
            if local.exists():
                continue
            fallback = sorted(ROOT.rglob(Path(raw).name))
            if fallback:
                status = f"found elsewhere: {fallback[0].relative_to(ROOT)}"
            else:
                status = "missing in project"
            issues.append(
                {
                    "script": str(path.relative_to(ROOT)),
                    "input": raw,
                    "status": status,
                }
            )
    return issues


def managed_output_issues() -> list[dict[str, str]]:
    """Flag final training scripts that bypass the shared output manager."""

    issues: list[dict[str, str]] = []
    for relative_path in sorted(MANAGED_OUTPUT_SCRIPTS):
        path = ROOT / relative_path
        if not path.exists():
            issues.append(
                {
                    "script": str(relative_path),
                    "issue": "missing_managed_script",
                    "line": "",
                }
            )
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        if "ExperimentArtifacts(" not in text:
            issues.append(
                {
                    "script": str(relative_path),
                    "issue": "missing_experiment_artifacts",
                    "line": "",
                }
            )
        if "write_summary(" not in text:
            issues.append(
                {
                    "script": str(relative_path),
                    "issue": "missing_run_summary",
                    "line": "",
                }
            )

        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for issue_name, pattern in DIRECT_OUTPUT_PATTERNS.items():
                if pattern.search(line):
                    issues.append(
                        {
                            "script": str(relative_path),
                            "issue": issue_name,
                            "line": str(line_number),
                        }
                    )
    return issues


def build_report() -> dict[str, object]:
    files = iter_code_files()
    python_files = [path for path in files if path.suffix == ".py"]
    matlab_files = [path for path in files if path.suffix == ".m"]
    return {
        "root": str(ROOT),
        "python_files": len(python_files),
        "matlab_files": len(matlab_files),
        "python_parse_errors": parse_python_files(python_files),
        "duplicate_code_groups": duplicate_code_groups(files),
        "unresolved_relative_inputs": unresolved_relative_inputs(files),
        "managed_output_issues": managed_output_issues(),
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["python_parse_errors"] or report["managed_output_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
