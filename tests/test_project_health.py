# -*- coding: utf-8 -*-
"""Regression checks for the reorganized 2025 project."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_CHECK = PROJECT_ROOT / "2025" / "tools" / "project_health_check.py"


def load_health_module():
    spec = importlib.util.spec_from_file_location("project_health_check", HEALTH_CHECK)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProjectHealthTests(unittest.TestCase):
    def test_python_sources_parse_successfully(self):
        health = load_health_module()
        report = health.build_report()

        self.assertGreaterEqual(report["python_files"], 20)
        self.assertGreaterEqual(report["matlab_files"], 10)
        self.assertEqual(report["python_parse_errors"], [])

    def test_shared_helpers_find_existing_project_inputs(self):
        shared_path = PROJECT_ROOT / "2025" / "_shared" / "pv_project.py"
        spec = importlib.util.spec_from_file_location("pv_project", shared_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        scenario_script = (
            PROJECT_ROOT
            / "2025"
            / "02_problem_solutions"
            / "problem3_scenario_analysis"
            / "问题3_场景划分分析_IEEE风格.py"
        )

        self.assertEqual(
            module.resolve_input("station00.csv", scenario_script).name,
            "station00.csv",
        )
        self.assertTrue(
            module.resolve_input("问题2三模型预测结果对比表.csv", scenario_script).exists()
        )

    def test_training_scripts_do_not_share_best_model_checkpoint_name(self):
        offenders = []
        for path in (PROJECT_ROOT / "2025").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "best_model.pth" in text:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))

        self.assertEqual(offenders, [])

    def test_checkpoint_names_are_safe_for_windows_paths(self):
        shared_path = PROJECT_ROOT / "2025" / "_shared" / "pv_project.py"
        spec = importlib.util.spec_from_file_location("pv_project", shared_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        path = module.torch_checkpoint_path("problem4 FusionModel:mixed")
        self.assertEqual(path.as_posix(), "models/problem4_FusionModel_mixed.pth")


if __name__ == "__main__":
    unittest.main()
