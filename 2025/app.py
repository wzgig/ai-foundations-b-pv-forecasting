# -*- coding: utf-8 -*-
"""Streamlit console for the PV forecasting coursework project."""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import logging
from functools import lru_cache
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from llm.assistant import LLMConfig, answer_question, generate_report_brief
from llm.prompts import DEFAULT_QUESTIONS
from llm.result_context import ROOT, TaskContext, collect_all_context, project_relative


PAGE_TITLE = "光伏电站日前预测工作台"
TEXT_SUFFIXES = {".py", ".md", ".bat", ".txt", ".m", ".json"}
EXCLUDED_TEXT_DIRS = {
    "__pycache__",
    ".pytest_cache",
    "models",
    "outputs",
    "node_modules",
}
CORE_FILES = [
    ("run_project.py", "项目总控入口，负责列出、运行、查看问题 1-4 的实验任务。"),
    ("app.py", "当前 Streamlit 工作台入口，负责结果浏览、交付索引、代码交互和结果解释。"),
    ("run.bat", "Windows 一键启动脚本，推荐双击或在 PowerShell 中运行。"),
    ("llm/result_context.py", "读取 outputs 中的 run_summary.json 和指标 CSV，组织解释上下文。"),
    ("llm/assistant.py", "离线规则解释与可选兼容 HTTP 接口入口。"),
    ("llm/prompts.py", "结果解释和报告整理提示词。"),
    ("tools/project_health_check.py", "静态健康检查，验证代码语法、输出管理约束和输入文件引用。"),
]
HERO_VISUAL = (
    ROOT
    / "02_problem_solutions"
    / "problem3_scenario_analysis"
    / "outputs"
    / "figures"
    / "三模型每日预测对比图_白昼.png"
)
FEATURED_VISUALS = [
    (
        "预测曲线",
        ROOT
        / "02_problem_solutions"
        / "problem3_scenario_analysis"
        / "outputs"
        / "figures"
        / "三模型每日预测对比图_白昼.png",
        "问题3 · NWP信息融入后的单日预测对比",
    ),
    (
        "输入消融",
        ROOT
        / "02_problem_solutions"
        / "problem4_feature_ablation"
        / "outputs"
        / "figures"
        / "FusionModel_输入对比雷达图.png",
        "问题4 · NWP、LMD、NWP+LMD综合得分",
    ),
    (
        "系统流程",
        ROOT / "03_figures" / "paper_assets" / "光伏发电数据驱动预测流程图.png",
        "论文素材 · 数据驱动预测流程",
    ),
]
REFERENCE_FILES = [
    ("题目要求", ROOT / "00_course_materials" / "A题：光伏电站发电功率日前预测问题.pdf", "课程题面"),
    ("评价附件", ROOT / "00_course_materials" / "附件1.pdf", "指标定义与约束"),
    ("最终论文", ROOT / "04_paper" / "final_submission" / "003158 A.pdf", "PDF提交件"),
    ("最终论文", ROOT / "04_paper" / "final_submission" / "003158 A.docx", "可编辑提交件"),
    ("运行说明", ROOT / "README.md", "项目说明"),
    ("运行说明", ROOT / "RUN_GUIDE.md", "复现流程"),
    ("代码索引", ROOT / "CODE_INDEX.md", "文件用途表"),
    ("维护记录", ROOT.parent / "PROJECT_LOG.md", "改动备注"),
]
NAVIGATION = ["工作台", "运行结果", "交付引用", "代码与命令", "结果解释", "运行控制"]


STYLE = """
<style>
:root {
  --ink: #17201d;
  --muted: #5d6763;
  --hairline: rgba(23, 32, 29, .12);
  --paper: #f6f7f3;
  --paper-warm: #fbfaf6;
  --panel: rgba(255, 255, 255, .82);
  --panel-solid: #ffffff;
  --panel-soft: rgba(250, 250, 247, .88);
  --graphite: #24302c;
  --solar: #d1912a;
  --leaf: #44705c;
  --cyan: #2b7783;
  --blue: #356b9a;
  --red: #b24545;
  --shadow-soft: 0 16px 36px rgba(25, 37, 32, .08);
}
.stApp {
  background:
    radial-gradient(circle at 72% 0%, rgba(209, 145, 42, .10), transparent 28rem),
    linear-gradient(180deg, #fbfaf6 0%, #f2f4f0 54%, #eef2ef 100%);
  color: var(--ink);
}
section[data-testid="stSidebar"] {
  background:
    linear-gradient(180deg, rgba(31, 44, 40, .98), rgba(21, 30, 28, .98));
  border-right: 1px solid rgba(255, 255, 255, .08);
}
section[data-testid="stSidebar"] * {
  color: #f7f4ea;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
  border-radius: 8px;
}
.stButton > button,
.stDownloadButton > button {
  border-radius: 8px;
  border: 1px solid rgba(23, 32, 29, .16);
  box-shadow: none;
  font-weight: 650;
}
.stButton > button[kind="primary"] {
  background: #17201d;
  color: #fff;
  border-color: #17201d;
}
.block-container {
  padding-top: 1.1rem;
  padding-bottom: 3rem;
  max-width: 1320px;
}
.hero-panel {
  min-height: 22rem;
  border: 1px solid var(--hairline);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  margin-bottom: 1rem;
  background-size: cover;
  background-position: center;
  box-shadow: var(--shadow-soft);
}
.hero-panel::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(251, 250, 246, .96) 0%, rgba(251, 250, 246, .90) 39%, rgba(251, 250, 246, .42) 78%, rgba(251, 250, 246, .18) 100%),
    linear-gradient(180deg, rgba(255, 255, 255, .35), rgba(255, 255, 255, .08));
}
.hero-content {
  position: relative;
  z-index: 1;
  padding: clamp(1.35rem, 4vw, 3.2rem);
  max-width: 50rem;
}
.pv-kicker {
  color: var(--cyan);
  font-weight: 750;
  font-size: .84rem;
  margin-bottom: .5rem;
}
.hero-content h1 {
  margin: 0;
  max-width: 43rem;
  font-size: clamp(2.05rem, 4vw, 4.45rem);
  line-height: 1.02;
  letter-spacing: 0;
  color: var(--ink);
}
.hero-content p {
  margin: 1rem 0 0 0;
  color: var(--muted);
  max-width: 38rem;
  font-size: 1.02rem;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
  margin-top: 1.25rem;
}
.hero-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid rgba(23, 32, 29, .14);
  background: rgba(255, 255, 255, .70);
  padding: .42rem .72rem;
  color: var(--graphite);
  font-weight: 650;
  font-size: .84rem;
  backdrop-filter: blur(12px);
}
.section-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: .75rem;
  margin: 1.15rem 0 .65rem 0;
}
.section-title h2 {
  font-size: 1.25rem;
  line-height: 1.2;
  margin: 0;
}
.section-title span {
  color: var(--muted);
  font-size: .9rem;
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .75rem;
  margin: .5rem 0 1rem 0;
}
.status-cell {
  background: var(--panel);
  border: 1px solid var(--hairline);
  border-radius: 8px;
  padding: .9rem .95rem;
  min-height: 5.6rem;
  box-shadow: var(--shadow-soft);
}
.status-cell b {
  display: block;
  font-size: .86rem;
  color: var(--muted);
  margin-bottom: .28rem;
}
.status-cell span {
  display: block;
  font-size: 1.08rem;
  font-weight: 700;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.metric-card,
.tool-card,
.reference-card,
.insight-card {
  background: var(--panel);
  border: 1px solid var(--hairline);
  border-radius: 8px;
  padding: .96rem 1rem;
  min-height: 8.2rem;
  box-shadow: var(--shadow-soft);
}
.tool-card {
  min-height: 7.1rem;
}
.metric-card {
  border-top: 4px solid var(--leaf);
}
.reference-card {
  border-top: 4px solid var(--solar);
  min-height: 6.9rem;
}
.insight-card {
  border-top: 4px solid var(--cyan);
}
.metric-card h3,
.tool-card h3,
.reference-card h3,
.insight-card h3 {
  margin: 0 0 .45rem 0;
  font-size: 1rem;
  color: var(--ink);
}
.metric-card .value {
  font-size: 1.34rem;
  font-weight: 700;
  color: var(--leaf);
  overflow-wrap: anywhere;
}
.insight-card .value,
.reference-card .value {
  font-size: 1.18rem;
  font-weight: 750;
  color: var(--graphite);
  overflow-wrap: anywhere;
}
.metric-card .delta {
  display: inline-block;
  margin-top: .45rem;
  padding: .22rem .52rem;
  border-radius: 999px;
  background: rgba(68, 112, 92, .10);
  border: 1px solid rgba(68, 112, 92, .20);
  color: #315c49;
  font-size: .78rem;
  font-weight: 650;
}
.caption,
.metric-card .caption,
.tool-card .caption,
.reference-card .caption,
.insight-card .caption {
  margin-top: .35rem;
  color: var(--muted);
  font-size: .9rem;
}
.status-strip {
  border: 1px solid var(--hairline);
  border-radius: 8px;
  background: rgba(255,255,255,.76);
  padding: .78rem .95rem;
  margin: .35rem 0 1rem 0;
}
.note {
  border-left: 4px solid var(--solar);
  border-radius: 0 8px 8px 0;
  padding: .78rem .95rem;
  background: rgba(255,255,255,.78);
  color: var(--ink);
}
.danger-note {
  border-left-color: var(--red);
}
div[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--hairline);
  border-radius: 8px;
  padding: .9rem;
}
.workflow-band {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .75rem;
  margin: .85rem 0 1.1rem 0;
}
.workflow-step {
  background: var(--panel-soft);
  border: 1px solid var(--hairline);
  border-radius: 8px;
  padding: .82rem .86rem;
  min-height: 6.2rem;
}
.workflow-step b {
  display: block;
  color: var(--ink);
  margin-bottom: .32rem;
}
.workflow-step span {
  color: var(--muted);
  font-size: .88rem;
}
.llm-panel {
  background: #f7faf8;
  border: 1px solid var(--hairline);
  border-radius: 8px;
  border-left: 5px solid var(--leaf);
  padding: .8rem .95rem;
  margin-bottom: .85rem;
}
.llm-panel b {
  color: var(--ink);
}
pre, code {
  white-space: pre-wrap;
}
.visual-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
  margin: .85rem 0 1.15rem 0;
}
.visual-card {
  background: rgba(255, 255, 255, .74);
  border: 1px solid var(--hairline);
  border-radius: 8px;
  padding: .65rem;
  box-shadow: var(--shadow-soft);
}
.visual-card img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(23, 32, 29, .10);
  background: #fff;
}
.visual-card b {
  display: block;
  margin: .55rem 0 .12rem 0;
}
.visual-card span {
  color: var(--muted);
  font-size: .86rem;
}
.pipeline-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: .55rem;
  margin: .75rem 0 1rem 0;
}
.pipeline-node {
  border: 1px solid var(--hairline);
  border-radius: 8px;
  background: rgba(255,255,255,.72);
  padding: .78rem .82rem;
  min-height: 5.6rem;
}
.pipeline-node b {
  display: block;
}
.pipeline-node span {
  color: var(--muted);
  font-size: .84rem;
}
.path-pill {
  display: inline-block;
  max-width: 100%;
  padding: .18rem .45rem;
  border-radius: 999px;
  background: rgba(53, 107, 154, .10);
  color: #25567d;
  border: 1px solid rgba(53, 107, 154, .18);
  font-size: .78rem;
  overflow-wrap: anywhere;
}
@media (max-width: 900px) {
  .status-grid,
  .workflow-band,
  .visual-grid,
  .pipeline-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .hero-panel::after {
    background: linear-gradient(180deg, rgba(251, 250, 246, .96), rgba(251, 250, 246, .72));
  }
}
@media (max-width: 560px) {
  .status-grid,
  .workflow-band,
  .visual-grid,
  .pipeline-list {
    grid-template-columns: 1fr;
  }
  .hero-panel {
    min-height: 25rem;
  }
  .hero-actions {
    display: grid;
  }
}
</style>
"""


def running_in_streamlit() -> bool:
    logger = logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context")
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False
    finally:
        logger.setLevel(previous_level)


def print_direct_run_help() -> None:
    print("This file is a Streamlit app and should not be started with plain python.")
    print("")
    print("Recommended from the project root:")
    print("  python -m streamlit run 2025\\app.py")
    print("")
    print("Recommended desktop launcher:")
    print("  2025\\start_software.vbs")
    print("")
    print("Command-line diagnostics:")
    print("  2025\\run.bat")


def configure_page() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=None,
        layout="wide",
        initial_sidebar_state="auto",
    )


def apply_style() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)


def html_text(value: object) -> str:
    return escape(str(value), quote=True)


@lru_cache(maxsize=12)
def image_data_uri(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""
    mime_by_suffix = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime = mime_by_suffix.get(path.suffix.lower(), "application/octet-stream")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def path_state(path: Path) -> str:
    if path.exists():
        return "存在"
    return "缺失"


def file_size_label(path: Path) -> str:
    if not path.exists():
        return "-"
    size = path.stat().st_size
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def numeric_from_row(row: pd.Series | None, column: str) -> float | None:
    if row is None or column not in row or pd.isna(row[column]):
        return None
    try:
        return float(row[column])
    except (TypeError, ValueError):
        return None


def improvement_label(before: pd.Series | None, after: pd.Series | None, column: str = "E_rmse") -> str:
    before_value = numeric_from_row(before, column)
    after_value = numeric_from_row(after, column)
    if before_value is None or after_value is None or before_value == 0:
        return "暂无可比提升"
    change = (before_value - after_value) / abs(before_value) * 100
    if change >= 0:
        return f"{column} 降低 {change:.1f}%"
    return f"{column} 上升 {abs(change):.1f}%"


def render_section_title(title: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-title">
          <h2>{html_text(title)}</h2>
          <span>{html_text(caption)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


@lru_cache(maxsize=1)
def load_contexts() -> dict[str, TaskContext]:
    return collect_all_context()


@lru_cache(maxsize=1)
def list_text_files() -> list[str]:
    files: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            continue
        if any(part in EXCLUDED_TEXT_DIRS for part in relative.parts):
            continue
        try:
            if path.stat().st_size > 500_000:
                continue
        except OSError:
            continue
        files.append(relative.as_posix())
    return sorted(files)


def read_metric_table(task: TaskContext) -> pd.DataFrame:
    if task.metrics_path is None or not task.metrics_path.exists():
        return pd.DataFrame()
    return pd.read_csv(task.metrics_path, encoding="utf-8-sig")


def best_row(df: pd.DataFrame, metric: str = "E_rmse") -> pd.Series | None:
    if df.empty or metric not in df.columns:
        return None
    numeric = pd.to_numeric(df[metric], errors="coerce")
    if numeric.isna().all():
        return None
    return df.loc[numeric.idxmin()]


def label_from_row(row: pd.Series | None) -> str:
    if row is None:
        return "暂无"
    for column in ("模型_输入", "模型", "Model"):
        if column in row and pd.notna(row[column]):
            return str(row[column])
    return str(row.name)


def value_from_row(row: pd.Series | None, column: str) -> str:
    if row is None or column not in row or pd.isna(row[column]):
        return "暂无"
    value = row[column]
    if isinstance(value, float):
        return f"{value:.4f}"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def llm_status_label(config: LLMConfig) -> str:
    if config.provider == "offline":
        return "离线规则"
    key_state = "密钥已读取" if config.api_key else "未读取密钥"
    return f"{config.provider} / {config.wire_api} / {key_state}"


def render_status_grid(contexts: dict[str, TaskContext]) -> None:
    ready_count = sum(1 for task in contexts.values() if task.report_exists or task.metrics_exists)
    total_figures = sum(len(task.artifacts.get("figures", [])) for task in contexts.values())
    llm_config = LLMConfig.from_env()
    st.markdown(
        f"""
        <div class="status-grid">
          <div class="status-cell"><b>任务识别</b><span>{len(contexts)} 个任务</span></div>
          <div class="status-cell"><b>摘要/指标</b><span>{ready_count} 项可读</span></div>
          <div class="status-cell"><b>图表产物</b><span>{total_figures} 条记录</span></div>
          <div class="status-cell"><b>解释接口</b><span>{html_text(llm_status_label(llm_config))}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_band() -> None:
    st.markdown(
        """
        <div class="workflow-band">
          <div class="workflow-step"><b>1. 数据与物理分析</b><span>读取站点数据、理论功率、周期性和偏差诊断。</span></div>
          <div class="workflow-step"><b>2. 日前预测模型</b><span>复用 checkpoint，比较 PureLSTM、FusionModel、BiFusionModel。</span></div>
          <div class="workflow-step"><b>3. 场景与特征解释</b><span>融入 NWP/LMD，查看场景划分、误差来源和特征重要性。</span></div>
          <div class="workflow-step"><b>4. 解释与交付</b><span>读取 outputs，形成指标解释、报告段落和演示口播素材。</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_text_path(relative: str) -> Path:
    target = (ROOT / relative).resolve()
    target.relative_to(ROOT)
    if target.suffix.lower() not in TEXT_SUFFIXES:
        raise ValueError("只允许查看项目内文本/代码文件")
    return target


def read_text_preview(relative: str, max_chars: int = 40_000) -> str:
    target = safe_text_path(relative)
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n... 已截断，完整文件请在 IDE 中查看。"
    return text


def run_project_command(args: list[str], timeout_seconds: int = 240) -> tuple[int, str, str]:
    command = [sys.executable, str(ROOT / "run_project.py"), *args]
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    command_text = " ".join(f'"{item}"' if " " in item else item for item in command)
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT.parent,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout_seconds,
            env=env,
        )
        return completed.returncode, completed.stdout, command_text
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return 124, f"{output}\n\n命令超过 {timeout_seconds} 秒，已停止等待。", command_text


def render_title() -> None:
    background = image_data_uri(str(HERO_VISUAL))
    background_style = f' style="background-image: url({background});"' if background else ""
    st.markdown(
        f"""
        <div class="hero-panel"{background_style}>
          <div class="hero-content">
          <div class="pv-kicker">PV day-ahead forecasting · Station operation console</div>
          <h1>光伏电站发电功率日前预测工作台</h1>
          <p>面向电站调度复盘和课程交付的结果工作台：从真实预测曲线进入指标、图表、脚本、材料和受控运行流程，默认只读取已有 outputs。</p>
          <div class="hero-actions">
            <span class="hero-chip">白昼附件指标</span>
            <span class="hero-chip">日前曲线复盘</span>
            <span class="hero-chip">输出产物索引</span>
            <span class="hero-chip">受控复现入口</span>
          </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(contexts: dict[str, TaskContext]) -> None:
    tables = {key: read_metric_table(task) for key, task in contexts.items()}
    cards = [
        ("问题2 基准预测", best_row(tables.get("2", pd.DataFrame())), "仅历史功率序列"),
        ("问题3 融入NWP", best_row(tables.get("3", pd.DataFrame())), "前一日功率 + 目标日NWP"),
        ("问题4 输入消融", best_row(tables.get("4", pd.DataFrame())), "NWP / LMD / mixed"),
    ]
    cols = st.columns(3)
    for col, (title, row, caption) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                  <h3>{html_text(title)}</h3>
                  <div class="value">{html_text(label_from_row(row))}</div>
                  <div class="caption">E_rmse={html_text(value_from_row(row, 'E_rmse'))} | C_R={html_text(value_from_row(row, 'C_R'))}% | Q_R={html_text(value_from_row(row, 'Q_R'))}%</div>
                  <div class="delta">白昼附件指标</div>
                  <div class="caption">{html_text(caption)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_model_insights(contexts: dict[str, TaskContext]) -> None:
    tables = {key: read_metric_table(task) for key, task in contexts.items()}
    row2 = best_row(tables.get("2", pd.DataFrame()))
    row3 = best_row(tables.get("3", pd.DataFrame()))
    row4 = best_row(tables.get("4", pd.DataFrame()))
    insights = [
        (
            "NWP增益",
            improvement_label(row2, row3),
            f"问题2最优 {label_from_row(row2)}；问题3最优 {label_from_row(row3)}。",
        ),
        (
            "降尺度输入",
            label_from_row(row4),
            f"问题4当前最优输入，E_rmse={value_from_row(row4, 'E_rmse')}。",
        ),
        (
            "交付闭环",
            "结果、代码、材料同屏索引",
            "从输出摘要追溯到指标表、图表、论文和核心脚本。",
        ),
    ]
    cols = st.columns(3)
    for col, (title, value, caption) in zip(cols, insights):
        with col:
            st.markdown(
                f"""
                <div class="insight-card">
                  <h3>{html_text(title)}</h3>
                  <div class="value">{html_text(value)}</div>
                  <div class="caption">{html_text(caption)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_pipeline_nodes() -> None:
    nodes = [
        ("课程题面", "约束与指标"),
        ("数据处理", "功率/NWP/LMD"),
        ("模型预测", "LSTM与融合模型"),
        ("结果解释", "场景、消融、图表"),
        ("提交材料", "论文与软件演示"),
    ]
    html_nodes = "\n".join(
        f'<div class="pipeline-node"><b>{html_text(title)}</b><span>{html_text(caption)}</span></div>'
        for title, caption in nodes
    )
    st.markdown(f'<div class="pipeline-list">{html_nodes}</div>', unsafe_allow_html=True)


def render_featured_visuals() -> None:
    cards = []
    for title, path, caption in FEATURED_VISUALS:
        uri = image_data_uri(str(path))
        if not uri:
            continue
        cards.append(
            f"""
            <div class="visual-card">
              <img src="{uri}" alt="{html_text(title)}">
              <b>{html_text(title)}</b>
              <span>{html_text(caption)}</span>
            </div>
            """
        )
    if cards:
        st.markdown(f'<div class="visual-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_workbench(contexts: dict[str, TaskContext]) -> None:
    render_section_title("工作台", "现有 outputs 驱动的软件总览")
    render_status_grid(contexts)
    render_metric_cards(contexts)
    render_model_insights(contexts)
    render_section_title("建模链路", "从题面到交付材料")
    render_pipeline_nodes()
    render_section_title("精选图表", "直接来自项目输出与论文素材")
    render_featured_visuals()
    st.markdown(
        '<div class="note">界面默认只读取已有 outputs，不触发长时间训练；需要重训时请到“运行控制”页显式勾选确认。</div>',
        unsafe_allow_html=True,
    )

    render_section_title("功能入口", "核心工作区")
    tool_cols = st.columns(3)
    tools = [
        ("查看运行结果", "指标表、静态 PNG、交互 HTML 和摘要文件集中浏览。"),
        ("交付引用", "题面、附件、论文、日志和关键输出形成可追溯索引。"),
        ("结果解释", "默认离线可用，也可接入本地或远程语言接口。"),
    ]
    for col, (title, caption) in zip(tool_cols, tools):
        with col:
            st.markdown(
                f"""
                <div class="tool-card">
                  <h3>{html_text(title)}</h3>
                  <div class="caption">{html_text(caption)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.code(f'python -m streamlit run "{ROOT / "app.py"}"', language="powershell")


def render_metric_tables(contexts: dict[str, TaskContext]) -> None:
    st.subheader("指标表")
    tabs = st.tabs([task.title for task in contexts.values()])
    for tab, task in zip(tabs, contexts.values()):
        with tab:
            df = read_metric_table(task)
            if df.empty:
                st.warning(f"未找到指标表：{project_relative(task.metrics_path) if task.metrics_path else '未配置'}")
                continue
            st.caption(project_relative(task.metrics_path))
            st.dataframe(df, width="stretch", hide_index=False)


def artifact_paths(task: TaskContext, category: str) -> list[Path]:
    paths: list[Path] = []
    for raw in task.artifacts.get(category, []):
        path = task.output_dir.parent / raw if raw.startswith("outputs") else task.output_dir / raw
        if path.exists():
            paths.append(path)
    return paths


def render_figures(contexts: dict[str, TaskContext]) -> None:
    render_section_title("图表展示", "静态图与交互 HTML")
    choices = {task.title: task for task in contexts.values()}
    selected_title = st.selectbox("选择问题", list(choices), index=4 if len(choices) > 4 else 0)
    task = choices[selected_title]
    figures = [path for path in artifact_paths(task, "figures") if path.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    html_files = [path for path in artifact_paths(task, "figures") if path.suffix.lower() == ".html"]

    if not figures and not html_files:
        st.info("当前问题没有可展示图表。")
        return

    image_options = {path.name: path for path in figures}
    if image_options:
        image_name = st.selectbox("静态图", list(image_options), index=0)
        st.caption(project_relative(image_options[image_name]))
        st.image(str(image_options[image_name]), width="stretch")

    if html_files:
        html_name = st.selectbox("交互式 HTML", [path.name for path in html_files], index=0)
        selected = next(path for path in html_files if path.name == html_name)
        st.caption(project_relative(selected))
        components.html(selected.read_text(encoding="utf-8", errors="ignore"), height=560, scrolling=True)


def render_artifact_summary(contexts: dict[str, TaskContext]) -> None:
    render_section_title("产物状态", "输出摘要、指标和图表记录")
    rows = []
    for task in contexts.values():
        rows.append(
            {
                "任务": task.title,
                "摘要": "存在" if task.report_exists else "缺失",
                "指标": "存在" if task.metrics_exists else "缺失",
                "图表记录数": len(task.artifacts.get("figures", [])),
                "摘要路径": project_relative(task.report_path),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_results(contexts: dict[str, TaskContext]) -> None:
    render_section_title("运行结果", "指标、图表和产物状态")
    render_metric_cards(contexts)
    render_model_insights(contexts)
    tabs = st.tabs(["指标表", "图表", "产物状态"])
    with tabs[0]:
        render_metric_tables(contexts)
    with tabs[1]:
        render_figures(contexts)
    with tabs[2]:
        render_artifact_summary(contexts)


def collect_reference_rows(contexts: dict[str, TaskContext]) -> pd.DataFrame:
    rows = []
    for category, path, role in REFERENCE_FILES:
        rows.append(
            {
                "类别": category,
                "文件": path.name,
                "路径": project_relative(path),
                "状态": path_state(path),
                "大小": file_size_label(path),
                "用途": role,
            }
        )
    for task in contexts.values():
        rows.append(
            {
                "类别": task.title,
                "文件": task.report_path.name,
                "路径": project_relative(task.report_path),
                "状态": path_state(task.report_path),
                "大小": file_size_label(task.report_path),
                "用途": "运行摘要",
            }
        )
        if task.metrics_path is not None:
            rows.append(
                {
                    "类别": task.title,
                    "文件": task.metrics_path.name,
                    "路径": project_relative(task.metrics_path),
                    "状态": path_state(task.metrics_path),
                    "大小": file_size_label(task.metrics_path),
                    "用途": "指标表",
                }
            )
    return pd.DataFrame(rows)


def render_reference_cards(contexts: dict[str, TaskContext]) -> None:
    reference_df = collect_reference_rows(contexts)
    existing_count = int((reference_df["状态"] == "存在").sum()) if not reference_df.empty else 0
    rows = [
        ("材料完整度", f"{existing_count}/{len(reference_df)}", "题面、论文、运行说明和结果文件"),
        ("核心代码", f"{len(CORE_FILES)} 个入口", "工作台、总控、解释模块、健康检查"),
        ("输出摘要", f"{len(contexts)} 个任务", "run_summary 与指标 CSV"),
    ]
    cols = st.columns(3)
    for col, (title, value, caption) in zip(cols, rows):
        with col:
            st.markdown(
                f"""
                <div class="reference-card">
                  <h3>{html_text(title)}</h3>
                  <div class="value">{html_text(value)}</div>
                  <div class="caption">{html_text(caption)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_reference_hub(contexts: dict[str, TaskContext]) -> None:
    render_section_title("交付引用", "题面、结果、论文和代码入口")
    render_reference_cards(contexts)

    reference_df = collect_reference_rows(contexts)
    filters = ["全部", *reference_df["类别"].drop_duplicates().tolist()]
    selected = st.segmented_control("类别", filters, default="全部")
    visible = reference_df if selected == "全部" else reference_df[reference_df["类别"] == selected]
    st.dataframe(visible, width="stretch", hide_index=True)

    render_section_title("核心代码引用", "演示和维护入口")
    st.dataframe(
        pd.DataFrame(CORE_FILES, columns=["文件", "用途"]),
        width="stretch",
        hide_index=True,
    )

    render_section_title("引用链", "结果文件到提交材料")
    st.markdown(
        """
        <div class="status-strip">
          <span class="path-pill">00_course_materials</span>
          <span class="path-pill">02_problem_solutions/*/outputs</span>
          <span class="path-pill">03_figures</span>
          <span class="path-pill">04_paper/final_submission</span>
          <span class="path-pill">PROJECT_LOG.md</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_code_lab() -> None:
    render_section_title("代码与命令", "受控命令与文本浏览")
    st.markdown(
        '<div class="status-strip">此页只允许查看项目内文本/代码文件，并执行经过固定参数拼接的轻量命令；不会开放任意 shell。</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        pd.DataFrame(CORE_FILES, columns=["文件", "用途"]),
        width="stretch",
        hide_index=True,
    )

    command_tabs = st.tabs(["安全命令", "文件浏览"])
    with command_tabs[0]:
        action = st.segmented_control(
            "选择操作",
            ["列出任务", "查看全部已有输出", "预演 main 运行计划", "预演 all 运行计划"],
            default="列出任务",
        )
        args_by_action = {
            "列出任务": ["--list"],
            "查看全部已有输出": ["--show", "all"],
            "预演 main 运行计划": ["--run", "main", "--dry-run"],
            "预演 all 运行计划": ["--run", "all", "--parallel", "--dry-run"],
        }
        args = args_by_action[action]
        st.code("python 2025\\run_project.py " + " ".join(args), language="powershell")
        if st.button("执行轻量命令", type="primary"):
            returncode, output, command_text = run_project_command(args)
            st.caption(f"returncode={returncode} | {command_text}")
            st.text_area("命令输出", output, height=360)

    with command_tabs[1]:
        files = list_text_files()
        query = st.text_input("按文件名过滤", placeholder="例如 assistant.py、RUN_GUIDE、problem4")
        visible = [item for item in files if query.lower() in item.lower()] if query else files
        if not visible:
            st.info("没有匹配文件。")
            return
        default_index = visible.index("app.py") if "app.py" in visible else 0
        selected = st.selectbox("选择文件", visible, index=default_index)
        text = read_text_preview(selected)
        st.caption(project_relative(ROOT / selected))
        st.code(text, language="python" if selected.endswith(".py") else "text")
        if st.toggle("把当前文件片段加入结果解释上下文"):
            st.session_state["code_context_for_llm"] = f"当前查看文件：{selected}\n\n{text[:12000]}"
            st.success("已加入本轮会话上下文。", icon=":material/check_circle:")


def build_llm_config_from_ui() -> LLMConfig:
    env_config = LLMConfig.from_env()
    with st.expander("解释接口配置", expanded=False):
        st.caption("默认使用离线规则解释；也可读取本机 Codex 配置或其他 OpenAI-compatible 端点。密钥只在本机读取，不写入项目文件。")
        provider_options = ["codex-config", "offline", "openai-compatible", "local-codex", "local", "openai"]
        if env_config.provider not in provider_options:
            provider_options.insert(0, env_config.provider)
        index = provider_options.index(env_config.provider) if env_config.provider in provider_options else 1
        provider = st.selectbox("接口模式", provider_options, index=index)
        model = st.text_input("模型名称", value=env_config.model)
        wire_api_options = ["responses", "chat"]
        wire_index = wire_api_options.index(env_config.wire_api) if env_config.wire_api in wire_api_options else 1
        wire_api = st.segmented_control("接口协议", wire_api_options, default=wire_api_options[wire_index])
        base_url = st.text_input(
            "API 地址",
            value=env_config.base_url,
            placeholder="https://api.example.com/v1",
        )
        key_placeholder = "已从本机配置读取，留空继续使用" if env_config.api_key else "本地端点可留空"
        api_key_input = st.text_input("API Key", value="", placeholder=key_placeholder, type="password")
        timeout = st.number_input("超时时间（秒）", min_value=3, max_value=120, value=env_config.timeout_seconds)
        config = LLMConfig(
            provider=provider,
            model=model.strip() or env_config.model,
            api_key=api_key_input.strip() or env_config.api_key,
            base_url=base_url.strip(),
            wire_api=str(wire_api or env_config.wire_api).strip(),
            timeout_seconds=int(timeout),
            source=env_config.source,
        )
        st.caption(f"配置来源：{env_config.source}")
        st.code(config.endpoint_display(), language="text")
        if st.button("测试解释接口"):
            response = answer_question(
                "请用一句话说明当前结果解释接口可用。",
                contexts=load_contexts(),
                config=config,
            )
            st.write(response.text)
            if response.error:
                st.caption(response.error)
    return config


def append_chat(role: str, content: str) -> None:
    st.session_state.setdefault("chat_messages", [])
    st.session_state["chat_messages"].append({"role": role, "content": content})


def render_llm_chat(contexts: dict[str, TaskContext]) -> None:
    st.subheader("结果解释")
    config = build_llm_config_from_ui()
    st.markdown(
        f"""
        <div class="llm-panel">
          <b>当前接入：</b>{html_text(config.provider)} · {html_text(config.model)} · {html_text(config.wire_api)}<br>
          <b>端点：</b>{html_text(config.endpoint())}<br>
          <b>密钥：</b>{"已读取" if config.api_key else "未配置"}；远程失败时自动使用离线规则兜底。
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": "已读取当前 outputs 指标和摘要。可以查看模型效果、指标含义、报告写法、演示口播或代码入口。",
            }
        ]

    quick_questions = DEFAULT_QUESTIONS + [
        "请写一段 3 分钟演示视频的口播提纲。",
        "请解释 app.py、run_project.py、llm/ 三者如何协同。",
        "请指出当前项目作为期末大作业还需要补哪些材料。",
    ]
    selected_quick = st.selectbox("常用分析问题", quick_questions, index=1)
    quick_cols = st.columns([1, 1, 3])
    pending_prompt = ""
    if quick_cols[0].button("查看解释", type="primary"):
        pending_prompt = selected_quick
    if quick_cols[1].button("清空对话"):
        st.session_state["chat_messages"] = []
        st.rerun()

    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("输入关于结果、代码、报告或演示的分析问题")
    if prompt:
        pending_prompt = prompt

    if pending_prompt:
        extra_context = st.session_state.get("code_context_for_llm", "")
        history = st.session_state["chat_messages"][-8:]
        append_chat("user", pending_prompt)
        with st.chat_message("user"):
            st.markdown(pending_prompt)
        with st.chat_message("assistant"):
            response = answer_question(
                pending_prompt,
                contexts=contexts,
                config=config,
                history=history,
                extra_context=extra_context,
            )
            st.markdown(response.text)
            if response.error:
                st.caption(response.error)
        append_chat("assistant", response.text)

    with st.expander("整理报告摘要草稿", expanded=False):
        if st.button("根据当前结果整理摘要"):
            response = generate_report_brief(contexts=contexts, config=config)
            st.write(response.text)
            if response.error:
                st.caption(response.error)


def render_runner() -> None:
    render_section_title("运行控制", "查看输出、预演或确认执行")
    st.markdown(
        '<div class="note danger-note">默认推荐“查看已有输出”或“dry-run 预演”。真正运行任务可能触发训练，请确认后再执行。</div>',
        unsafe_allow_html=True,
    )
    task = st.selectbox("任务", ["all", "main", "1", "2", "3", "3-analysis", "4"], index=0)
    mode = st.segmented_control("操作", ["查看已有输出", "dry-run 预演", "运行任务"], default="查看已有输出")
    use_parallel = st.toggle("并行运行互不依赖任务", value=task in {"main", "all"})
    force_retrain = st.toggle("强制重新训练（耗时，默认关闭）", value=False)
    allow_long_run = st.toggle("确认启动训练/分析任务", value=False)

    if mode == "查看已有输出":
        args = ["--show", task]
    elif mode == "dry-run 预演":
        args = ["--run", task, "--dry-run"]
    else:
        args = ["--run", task]
    if mode != "查看已有输出" and use_parallel:
        args.append("--parallel")
    if mode == "运行任务" and force_retrain:
        args.append("--force-retrain")

    st.code("python 2025\\run_project.py " + " ".join(args), language="powershell")
    disabled = mode == "运行任务" and not allow_long_run
    if st.button("执行", type="primary", disabled=disabled):
        timeout = 3600 if mode == "运行任务" else 240
        returncode, output, command_text = run_project_command(args, timeout_seconds=timeout)
        st.caption(f"returncode={returncode} | {command_text}")
        st.text_area("命令输出", output, height=420)
    if disabled:
        st.warning("如需真正运行任务，请先勾选确认框。")


def main() -> None:
    configure_page()
    apply_style()
    contexts = load_contexts()
    render_title()

    page = st.sidebar.radio(
        "导航",
        NAVIGATION,
        index=0,
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"项目目录：{ROOT}")
    llm_config = LLMConfig.from_env()
    st.sidebar.caption(f"解释接口：{llm_config.provider} / {llm_config.wire_api}")
    st.sidebar.caption(f"模型：{llm_config.model}")
    st.sidebar.caption("直接运行 app.py 只显示启动提示；演示优先用 start_software.vbs，调试用 run.bat。")

    if page == "工作台":
        render_workbench(contexts)
    elif page == "运行结果":
        render_results(contexts)
    elif page == "交付引用":
        render_reference_hub(contexts)
    elif page == "代码与命令":
        render_code_lab()
    elif page == "结果解释":
        render_llm_chat(contexts)
    else:
        render_runner()


if __name__ == "__main__":
    if running_in_streamlit():
        main()
    else:
        print_direct_run_help()
