# -*- coding: utf-8 -*-
"""Regression checks for the reorganized 2025 project."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_CHECK = PROJECT_ROOT / "2025" / "tools" / "project_health_check.py"
RUN_PROJECT = PROJECT_ROOT / "2025" / "run_project.py"


def load_health_module():
    spec = importlib.util.spec_from_file_location("project_health_check", HEALTH_CHECK)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_run_project_module():
    spec = importlib.util.spec_from_file_location("run_project", RUN_PROJECT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
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
            / "problem3_scenario_ieee_analysis.py"
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

    def test_experiment_artifacts_write_under_script_outputs(self):
        shared_path = PROJECT_ROOT / "2025" / "_shared" / "pv_project.py"
        spec = importlib.util.spec_from_file_location("pv_project", shared_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "experiment.py"
            script.write_text("# test script\n", encoding="utf-8")

            artifacts = module.ExperimentArtifacts(script)
            csv_path = artifacts.write_csv(
                "metrics",
                "metrics.csv",
                module.pd.DataFrame({"value": [1]}),
                index=False,
            )
            summary_path = artifacts.write_summary({"ok": True})

            self.assertEqual(csv_path.parent.name, "metrics")
            csv_text = csv_path.read_text(encoding=module.UTF8_SIG).replace("\r\n", "\n").strip()
            self.assertEqual(csv_text, "value\n1")
            self.assertEqual(summary_path.parent.name, "reports")
            metrics_records = [path.replace("\\", "/") for path in artifacts.artifacts["metrics"]]
            report_records = [path.replace("\\", "/") for path in artifacts.artifacts["reports"]]
            self.assertIn("outputs/metrics/metrics.csv", metrics_records)
            self.assertIn("outputs/reports/run_summary.json", report_records)

            summary = module.json.loads(summary_path.read_text(encoding="utf-8"))
            summary_reports = [path.replace("\\", "/") for path in summary["artifacts"]["reports"]]
            self.assertIn("outputs/reports/run_summary.json", summary_reports)

    def test_managed_training_scripts_use_output_manager(self):
        health = load_health_module()
        report = health.build_report()

        self.assertEqual(report["managed_output_issues"], [])

    def test_project_runner_expands_task_aliases(self):
        runner = load_run_project_module()

        self.assertEqual(runner.parse_task_selection(["1,3-analysis"]), ["1", "3-analysis"])
        self.assertEqual(runner.parse_task_selection(["main"]), ["1", "2", "3", "4"])
        self.assertEqual(runner.parse_task_selection(["all"]), ["1", "2", "3", "4", "3-analysis"])

    def test_project_runner_orders_analysis_after_dependencies(self):
        runner = load_run_project_module()

        batches = runner.build_execution_batches(["1", "2", "3", "4", "3-analysis"], parallel=True)
        self.assertIn("2", batches[0])
        self.assertIn("3", batches[0])
        self.assertEqual(batches[-1], ["3-analysis"])

    def test_project_runner_records_problem3_analysis_dependencies(self):
        runner = load_run_project_module()

        self.assertEqual(runner.TASKS["3-analysis"].depends, ("2", "3"))
        self.assertTrue(runner.task_outputs_ready("2"))
        self.assertTrue(runner.task_outputs_ready("3"))


if __name__ == "__main__":
    unittest.main()
