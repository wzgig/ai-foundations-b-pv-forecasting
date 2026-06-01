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


def iter_code_files() -> list[Path]:
    return sorted([*ROOT.rglob("*.py"), *ROOT.rglob("*.m")])


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
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["python_parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
