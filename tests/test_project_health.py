# -*- coding: utf-8 -*-
"""Regression checks for the reorganized 2025 project."""

from __future__ import annotations

import importlib.util
import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_CHECK = PROJECT_ROOT / "2025" / "tools" / "project_health_check.py"
RUN_PROJECT = PROJECT_ROOT / "2025" / "run_project.py"
APP = PROJECT_ROOT / "2025" / "app.py"
LAUNCHER = PROJECT_ROOT / "2025" / "software_launcher.py"
START_SOFTWARE = PROJECT_ROOT / "2025" / "start_software.vbs"
STREAMLIT_THEME = PROJECT_ROOT / ".streamlit" / "config.toml"
DOCS_INDEX = PROJECT_ROOT / "docs" / "index.html"


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

    def test_llm_context_reads_existing_outputs(self):
        sys.path.insert(0, str(PROJECT_ROOT / "2025"))
        from llm.result_context import best_row_by_metric, collect_all_context

        contexts = collect_all_context()

        self.assertIn("4", contexts)
        self.assertTrue(contexts["4"].report_exists)
        self.assertGreaterEqual(len(contexts["4"].metric_rows), 3)
        self.assertEqual(best_row_by_metric(contexts["4"])["模型_输入"], "FusionModel_mixed")

    def test_llm_offline_answer_has_stable_fallback(self):
        sys.path.insert(0, str(PROJECT_ROOT / "2025"))
        from llm.assistant import LLMConfig, answer_question
        from llm.result_context import collect_all_context

        response = answer_question(
            "为什么NWP+LMD混合输入在问题4中表现最好？",
            contexts=collect_all_context(),
            config=LLMConfig(provider="offline"),
        )

        self.assertFalse(response.used_remote)
        self.assertIn("FusionModel_mixed", response.text)
        self.assertIn("空间降尺度", response.text)

    def test_llm_local_codex_config_allows_empty_api_key(self):
        sys.path.insert(0, str(PROJECT_ROOT / "2025"))
        from llm.assistant import LLMConfig

        config = LLMConfig(
            provider="local-codex",
            model="codex-local",
            base_url="http://127.0.0.1:8000/v1",
            api_key="",
        )

        self.assertFalse(config.requires_api_key())
        self.assertEqual(config.endpoint(), "http://127.0.0.1:8000/v1/chat/completions")

    def test_llm_reads_local_codex_responses_config(self):
        sys.path.insert(0, str(PROJECT_ROOT / "2025"))
        from llm.assistant import LLMConfig

        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            (codex_home / "config.toml").write_text(
                """
model_provider = "my_codex"
model = "gpt-5.5"

[model_providers.my_codex]
base_url = "https://api.example.test/v1"
wire_api = "responses"
requires_openai_auth = true
""".strip(),
                encoding="utf-8",
            )
            (codex_home / "auth.json").write_text(
                json.dumps({"OPENAI_API_KEY": "sk-test-local"}),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {
                    "CODEX_HOME": str(codex_home),
                    "PV_LLM_PROVIDER": "",
                    "CODEX_LLM_PROVIDER": "",
                    "OPENAI_PROVIDER": "",
                },
                clear=False,
            ):
                config = LLMConfig.from_env()

        self.assertEqual(config.provider, "codex-config")
        self.assertEqual(config.model, "gpt-5.5")
        self.assertEqual(config.wire_api, "responses")
        self.assertEqual(config.endpoint(), "https://api.example.test/v1/responses")
        self.assertEqual(config.api_key, "sk-test-local")

    def test_app_source_parses_successfully(self):
        ast.parse(APP.read_text(encoding="utf-8"), filename=str(APP))

    def test_app_ui_exposes_reference_and_visual_shell(self):
        text = APP.read_text(encoding="utf-8")

        self.assertIn("交付引用", text)
        self.assertIn("FEATURED_VISUALS", text)
        self.assertIn("hero-panel", text)
        self.assertIn("render_reference_hub", text)
        self.assertIn("结果解释", text)
        self.assertNotIn("use_container_width", text)

    def test_static_pages_site_references_real_assets(self):
        html = DOCS_INDEX.read_text(encoding="utf-8")

        self.assertIn("光伏电站发电功率日前预测工作台", html)
        self.assertIn("forecast-curve.png", html)
        self.assertIn("feature-radar.png", html)
        self.assertIn("GitHub Pages 只发布静态项目页", html)
        self.assertTrue((PROJECT_ROOT / "docs" / "assets" / "forecast-curve.png").exists())
        self.assertTrue((PROJECT_ROOT / "docs" / "assets" / "feature-radar.png").exists())
        self.assertTrue((PROJECT_ROOT / "docs" / "assets" / "forecast-workflow.png").exists())

    def test_streamlit_theme_is_project_scoped(self):
        text = STREAMLIT_THEME.read_text(encoding="utf-8")

        self.assertIn("[theme]", text)
        self.assertIn("primaryColor = \"#315c49\"", text)
        self.assertIn("[theme.sidebar]", text)

    def test_software_launcher_source_parses_successfully(self):
        ast.parse(LAUNCHER.read_text(encoding="utf-8"), filename=str(LAUNCHER))

    def test_no_console_launcher_points_to_desktop_launcher(self):
        text = START_SOFTWARE.read_text(encoding="utf-8")

        self.assertIn("software_launcher.py", text)
        self.assertIn("pythonw.exe", text)
        self.assertIn("shell.Run command, 1, False", text)

    def test_app_direct_python_run_prints_launch_hint(self):
        completed = subprocess.run(
            [sys.executable, str(APP)],
            cwd=PROJECT_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=20,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("python -m streamlit run", completed.stdout)
        self.assertIn("start_software.vbs", completed.stdout)
        self.assertNotIn("missing ScriptRunContext", completed.stdout)

    def test_runtime_requirements_are_version_pinned(self):
        requirements = PROJECT_ROOT / "2025" / "requirements.txt"
        lines = [
            line.strip()
            for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        self.assertIn("streamlit==1.58.0", lines)
        self.assertTrue(all("==" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
