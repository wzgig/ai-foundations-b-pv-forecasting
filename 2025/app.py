# -*- coding: utf-8 -*-
"""Streamlit dashboard for the PV forecasting coursework project."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from llm.assistant import LLMConfig, answer_question, generate_report_brief
from llm.prompts import DEFAULT_QUESTIONS
from llm.result_context import ROOT, TaskContext, collect_all_context, project_relative


st.set_page_config(
    page_title="光伏日前预测课程项目",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


STYLE = """
<style>
:root {
  --ink: #202226;
  --muted: #65717d;
  --line: #d8dee3;
  --paper: #f6f4ef;
  --panel: #ffffff;
  --teal: #1b7c76;
  --copper: #b66a3c;
  --green: #4f7f45;
}
.stApp {
  background:
    linear-gradient(180deg, rgba(246,244,239,0.96), rgba(238,241,239,0.98));
  color: var(--ink);
}
section[data-testid="stSidebar"] {
  background: #22272b;
  border-right: 1px solid #15191c;
}
section[data-testid="stSidebar"] * {
  color: #f4f0e8;
}
.block-container {
  padding-top: 2rem;
  padding-bottom: 3rem;
}
.pv-title {
  border-bottom: 2px solid var(--ink);
  padding-bottom: .7rem;
  margin-bottom: 1rem;
}
.pv-title h1 {
  margin: 0;
  font-size: 2.2rem;
  line-height: 1.15;
  letter-spacing: 0;
  color: var(--ink);
}
.pv-title p {
  margin: .55rem 0 0 0;
  color: var(--muted);
  max-width: 68rem;
}
.metric-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 5px solid var(--teal);
  padding: 1rem 1.05rem;
  min-height: 8.2rem;
}
.metric-card h3 {
  margin: 0 0 .45rem 0;
  font-size: 1rem;
  color: var(--ink);
}
.metric-card .value {
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--teal);
}
.metric-card .caption {
  margin-top: .35rem;
  color: var(--muted);
  font-size: .9rem;
}
.status-strip {
  border: 1px solid var(--line);
  background: rgba(255,255,255,.74);
  padding: .7rem .9rem;
  margin: .4rem 0 1rem 0;
}
.note {
  border-left: 4px solid var(--copper);
  padding: .7rem .9rem;
  background: rgba(255,255,255,.76);
  color: var(--ink);
}
div[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
  padding: .9rem;
}
</style>
"""


def apply_style() -> None:
    st.markdown(STYLE, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_contexts() -> dict[str, TaskContext]:
    return collect_all_context()


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


def render_title() -> None:
    st.markdown(
        """
        <div class="pv-title">
          <h1>光伏电站发电功率日前预测项目控制台</h1>
          <p>面向《人工智能基础B》期末大作业的交互展示层：集中查看四问结果、附件指标、图表产物和大模型辅助解读。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview(contexts: dict[str, TaskContext]) -> None:
    st.subheader("核心结果")
    tables = {key: read_metric_table(task) for key, task in contexts.items()}
    row2 = best_row(tables.get("2", pd.DataFrame()))
    row3 = best_row(tables.get("3", pd.DataFrame()))
    row4 = best_row(tables.get("4", pd.DataFrame()))

    cols = st.columns(3)
    cards = [
        ("问题2 基准预测", row2, "仅历史功率序列"),
        ("问题3 融入NWP", row3, "前一日功率 + 目标日NWP"),
        ("问题4 输入消融", row4, "NWP / LMD / mixed"),
    ]
    for col, (title, row, caption) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                  <h3>{title}</h3>
                  <div class="value">{label_from_row(row)}</div>
                  <div class="caption">E_rmse={value_from_row(row, 'E_rmse')} | C_R={value_from_row(row, 'C_R')}% | Q_R={value_from_row(row, 'Q_R')}%</div>
                  <div class="caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="note">默认展示已有 outputs，不触发长时间训练；需要重训时请使用 run_project.py 的 --force-retrain 参数。</div>',
        unsafe_allow_html=True,
    )


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
            st.dataframe(df, use_container_width=True, hide_index=False)


def artifact_paths(task: TaskContext, category: str) -> list[Path]:
    paths: list[Path] = []
    for raw in task.artifacts.get(category, []):
        path = task.output_dir.parent / raw if raw.startswith("outputs") else task.output_dir / raw
        if path.exists():
            paths.append(path)
    return paths


def render_figures(contexts: dict[str, TaskContext]) -> None:
    st.subheader("图表展示")
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
        st.image(str(image_options[image_name]), use_container_width=True)

    if html_files:
        html_name = st.selectbox("交互式HTML", [path.name for path in html_files], index=0)
        selected = next(path for path in html_files if path.name == html_name)
        st.caption(project_relative(selected))
        components.html(selected.read_text(encoding="utf-8", errors="ignore"), height=560, scrolling=True)


def render_llm(contexts: dict[str, TaskContext]) -> None:
    st.subheader("大模型辅助解读")
    config = LLMConfig.from_env()
    st.markdown(
        f'<div class="status-strip">当前模式：{config.provider}；模型：{config.model}。未配置远程密钥时自动使用离线模板，保证课堂演示稳定。</div>',
        unsafe_allow_html=True,
    )
    question = st.selectbox("选择一个问题", DEFAULT_QUESTIONS, index=1)
    custom = st.text_area("也可以输入自定义问题", placeholder="例如：如何在报告中解释问题4 mixed 输入的优势？", height=90)
    actual_question = custom.strip() or question
    if st.button("生成解读", type="primary"):
        response = answer_question(actual_question, contexts=contexts, config=config)
        st.write(response.text)
        if response.error:
            st.caption(response.error)

    if st.button("生成报告摘要草稿"):
        response = generate_report_brief(contexts=contexts, config=config)
        st.write(response.text)


def render_runner() -> None:
    st.subheader("一键查看与运行控制")
    command = [sys.executable, str(ROOT / "run_project.py"), "--show", "all"]
    st.code(" ".join(command), language="powershell")
    if st.button("刷新并展示全部已有输出"):
        completed = subprocess.run(
            command,
            cwd=ROOT.parent,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        st.text_area("命令输出", completed.stdout, height=360)

    st.caption("如需重新训练，请在 PowerShell 中显式运行 run_project.py，避免界面演示时误触发长时间训练。")


def main() -> None:
    apply_style()
    contexts = load_contexts()
    render_title()

    page = st.sidebar.radio(
        "导航",
        ["项目总览", "指标表", "图表", "大模型解读", "运行控制"],
        index=0,
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"项目目录：{ROOT}")
    st.sidebar.caption(f"LLM Provider：{os.getenv('PV_LLM_PROVIDER', 'offline')}")

    if page == "项目总览":
        render_overview(contexts)
    elif page == "指标表":
        render_metric_tables(contexts)
    elif page == "图表":
        render_figures(contexts)
    elif page == "大模型解读":
        render_llm(contexts)
    else:
        render_runner()


if __name__ == "__main__":
    main()
