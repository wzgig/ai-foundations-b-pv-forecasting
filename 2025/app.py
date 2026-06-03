# -*- coding: utf-8 -*-
"""Streamlit console for the PV forecasting coursework project."""

from __future__ import annotations

import os
import subprocess
import sys
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from llm.assistant import LLMConfig, answer_question, generate_report_brief
from llm.prompts import DEFAULT_QUESTIONS
from llm.result_context import ROOT, TaskContext, collect_all_context, project_relative


PAGE_TITLE = "光伏日前预测课程项目"
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
    ("app.py", "当前 Streamlit 软件入口，负责界面、结果浏览、代码交互和 LLM 问答。"),
    ("run.bat", "Windows 一键启动脚本，推荐双击或在 PowerShell 中运行。"),
    ("llm/result_context.py", "读取 outputs 中的 run_summary.json 和指标 CSV，组织问答上下文。"),
    ("llm/assistant.py", "离线模板与 OpenAI-compatible/本地 Codex API 调用入口。"),
    ("llm/prompts.py", "课程展示问答和报告摘要提示词。"),
    ("tools/project_health_check.py", "静态健康检查，验证代码语法、输出管理约束和输入文件引用。"),
]


STYLE = """
<style>
:root {
  --ink: #1c2327;
  --muted: #5e6972;
  --line: #d8dee4;
  --paper: #f4f6f4;
  --panel: #ffffff;
  --panel-soft: #f8faf9;
  --teal: #0f766e;
  --leaf: #4f7d3f;
  --blue: #1f5f99;
  --gold: #b7791f;
  --red: #b33a3a;
}
.stApp {
  background:
    linear-gradient(180deg, rgba(244,246,244,1), rgba(238,242,244,1));
  color: var(--ink);
}
section[data-testid="stSidebar"] {
  background: #182125;
  border-right: 1px solid #10171a;
}
section[data-testid="stSidebar"] * {
  color: #f2f6f4;
}
.block-container {
  padding-top: 1.35rem;
  padding-bottom: 3rem;
  max-width: 1280px;
}
.pv-title {
  border: 1px solid var(--line);
  border-left: 7px solid var(--teal);
  background: rgba(255,255,255,.88);
  padding: 1.05rem 1.15rem;
  margin-bottom: 1rem;
}
.pv-title h1 {
  margin: 0;
  font-size: 1.88rem;
  line-height: 1.2;
  letter-spacing: 0;
  color: var(--ink);
}
.pv-title p {
  margin: .55rem 0 0 0;
  color: var(--muted);
  max-width: 74rem;
}
.pv-kicker {
  margin-bottom: .35rem;
  color: var(--teal);
  font-weight: 700;
  font-size: .84rem;
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .75rem;
  margin: .5rem 0 1rem 0;
}
.status-cell {
  background: var(--panel);
  border: 1px solid var(--line);
  padding: .78rem .85rem;
  min-height: 5.3rem;
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
.metric-card, .tool-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-top: 4px solid var(--teal);
  padding: .9rem .95rem;
  min-height: 8.1rem;
}
.tool-card {
  border-left-color: var(--blue);
  border-top-color: var(--blue);
  min-height: 6.9rem;
}
.metric-card h3, .tool-card h3 {
  margin: 0 0 .45rem 0;
  font-size: 1rem;
  color: var(--ink);
}
.metric-card .value {
  font-size: 1.36rem;
  font-weight: 700;
  color: var(--teal);
  overflow-wrap: anywhere;
}
.metric-card .delta {
  display: inline-block;
  margin-top: .45rem;
  padding: .18rem .45rem;
  background: rgba(15,118,110,.1);
  border: 1px solid rgba(15,118,110,.22);
  color: #0d5f59;
  font-size: .78rem;
}
.caption, .metric-card .caption, .tool-card .caption {
  margin-top: .35rem;
  color: var(--muted);
  font-size: .9rem;
}
.status-strip {
  border: 1px solid var(--line);
  background: rgba(255,255,255,.86);
  padding: .72rem .9rem;
  margin: .35rem 0 1rem 0;
}
.note {
  border-left: 4px solid var(--gold);
  padding: .72rem .9rem;
  background: rgba(255,255,255,.78);
  color: var(--ink);
}
.danger-note {
  border-left-color: var(--red);
}
div[data-testid="stMetric"] {
  background: var(--panel);
  border: 1px solid var(--line);
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
  border: 1px solid var(--line);
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
  border: 1px solid var(--line);
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
@media (max-width: 900px) {
  .status-grid,
  .workflow-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 560px) {
  .status-grid,
  .workflow-band {
    grid-template-columns: 1fr;
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
        return "离线模板"
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
          <div class="status-cell"><b>大模型接入</b><span>{llm_status_label(llm_config)}</span></div>
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
          <div class="workflow-step"><b>4. LLM 辅助交付</b><span>读取 outputs 形成问答、报告摘要和演示口播素材。</span></div>
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
    st.markdown(
        """
        <div class="pv-title">
          <div class="pv-kicker">AI Foundations B · PV Day-Ahead Forecasting</div>
          <h1>光伏电站发电功率日前预测软件</h1>
          <p>面向《人工智能基础B》期末大作业的工程化入口：集中查看四问结果、浏览本地代码、执行受保护命令，并自动接入本机 Codex / OpenAI-compatible 大模型配置。</p>
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
                  <h3>{title}</h3>
                  <div class="value">{label_from_row(row)}</div>
                  <div class="caption">E_rmse={value_from_row(row, 'E_rmse')} | C_R={value_from_row(row, 'C_R')}% | Q_R={value_from_row(row, 'Q_R')}%</div>
                  <div class="delta">白昼附件指标</div>
                  <div class="caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_workbench(contexts: dict[str, TaskContext]) -> None:
    st.subheader("工作台")
    render_status_grid(contexts)
    render_workflow_band()
    render_metric_cards(contexts)
    st.markdown(
        '<div class="note">界面默认只读取已有 outputs，不触发长时间训练；需要重训时请到“运行控制”页显式勾选确认。</div>',
        unsafe_allow_html=True,
    )

    st.subheader("功能入口")
    tool_cols = st.columns(3)
    tools = [
        ("查看运行结果", "指标表、静态 PNG、交互 HTML 和摘要文件集中浏览。"),
        ("本地代码交互", "选择入口脚本/文档查看代码，执行 --list、--show、--dry-run 等安全命令。"),
        ("大模型问答", "默认离线可用，也可接入本地 Codex 或 OpenAI-compatible chat completions 端点。"),
    ]
    for col, (title, caption) in zip(tool_cols, tools):
        with col:
            st.markdown(
                f"""
                <div class="tool-card">
                  <h3>{title}</h3>
                  <div class="caption">{caption}</div>
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
        st.caption(project_relative(image_options[image_name]))
        st.image(str(image_options[image_name]), use_container_width=True)

    if html_files:
        html_name = st.selectbox("交互式 HTML", [path.name for path in html_files], index=0)
        selected = next(path for path in html_files if path.name == html_name)
        st.caption(project_relative(selected))
        components.html(selected.read_text(encoding="utf-8", errors="ignore"), height=560, scrolling=True)


def render_artifact_summary(contexts: dict[str, TaskContext]) -> None:
    st.subheader("产物状态")
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
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_results(contexts: dict[str, TaskContext]) -> None:
    st.subheader("运行结果")
    render_metric_cards(contexts)
    tabs = st.tabs(["指标表", "图表", "产物状态"])
    with tabs[0]:
        render_metric_tables(contexts)
    with tabs[1]:
        render_figures(contexts)
    with tabs[2]:
        render_artifact_summary(contexts)


def render_code_lab() -> None:
    st.subheader("本地代码交互")
    st.markdown(
        '<div class="status-strip">此页只允许查看项目内文本/代码文件，并执行经过固定参数拼接的轻量命令；不会开放任意 shell。</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        pd.DataFrame(CORE_FILES, columns=["文件", "用途"]),
        use_container_width=True,
        hide_index=True,
    )

    command_tabs = st.tabs(["安全命令", "文件浏览"])
    with command_tabs[0]:
        action = st.radio(
            "选择操作",
            ["列出任务", "查看全部已有输出", "预演 main 运行计划", "预演 all 运行计划"],
            horizontal=True,
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
        if st.checkbox("把当前文件片段加入大模型问答上下文"):
            st.session_state["code_context_for_llm"] = f"当前查看文件：{selected}\n\n{text[:12000]}"
            st.success("已加入本轮会话上下文。")


def build_llm_config_from_ui() -> LLMConfig:
    env_config = LLMConfig.from_env()
    with st.expander("大模型接口配置", expanded=False):
        st.caption("默认自动读取本机 Codex 配置；也支持任何 OpenAI-compatible Chat Completions 或 Responses 端点。密钥不会写入项目文件。")
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
        if st.button("测试大模型连接"):
            response = answer_question(
                "请用一句话说明你已连接到项目问答助手。",
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
    st.subheader("大模型问答交流")
    config = build_llm_config_from_ui()
    st.markdown(
        f"""
        <div class="llm-panel">
          <b>当前接入：</b>{config.provider} · {config.model} · {config.wire_api}<br>
          <b>端点：</b>{config.endpoint()}<br>
          <b>密钥：</b>{"已读取" if config.api_key else "未配置"}；远程失败时自动使用离线模板兜底。
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": "我已读取当前 outputs 指标和摘要。可以问我模型效果、指标含义、报告写法、演示口播或代码入口。",
            }
        ]

    quick_questions = DEFAULT_QUESTIONS + [
        "请写一段 3 分钟演示视频的口播提纲。",
        "请解释 app.py、run_project.py、llm/ 三者如何协同。",
        "请指出当前项目作为期末大作业还需要补哪些材料。",
    ]
    selected_quick = st.selectbox("常用问题", quick_questions, index=1)
    quick_cols = st.columns([1, 1, 3])
    pending_prompt = ""
    if quick_cols[0].button("发送常用问题", type="primary"):
        pending_prompt = selected_quick
    if quick_cols[1].button("清空对话"):
        st.session_state["chat_messages"] = []
        st.rerun()

    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("输入关于结果、代码、报告或演示的问题")
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

    with st.expander("生成报告摘要草稿", expanded=False):
        if st.button("根据当前结果生成摘要"):
            response = generate_report_brief(contexts=contexts, config=config)
            st.write(response.text)
            if response.error:
                st.caption(response.error)


def render_runner() -> None:
    st.subheader("运行控制")
    st.markdown(
        '<div class="note danger-note">默认推荐“查看已有输出”或“dry-run 预演”。真正运行任务可能触发训练，请确认后再执行。</div>',
        unsafe_allow_html=True,
    )
    task = st.selectbox("任务", ["all", "main", "1", "2", "3", "3-analysis", "4"], index=0)
    mode = st.radio("操作", ["查看已有输出", "dry-run 预演", "运行任务"], horizontal=True)
    use_parallel = st.checkbox("并行运行互不依赖任务", value=task in {"main", "all"})
    force_retrain = st.checkbox("强制重新训练（耗时，默认不要勾选）", value=False)
    allow_long_run = st.checkbox("我确认允许启动训练/分析任务", value=False)

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
        ["工作台", "运行结果", "本地代码交互", "大模型问答", "运行控制"],
        index=0,
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(f"项目目录：{ROOT}")
    llm_config = LLMConfig.from_env()
    st.sidebar.caption(f"LLM：{llm_config.provider} / {llm_config.wire_api}")
    st.sidebar.caption(f"模型：{llm_config.model}")
    st.sidebar.caption("直接运行 app.py 只显示启动提示；演示优先用 start_software.vbs，调试用 run.bat。")

    if page == "工作台":
        render_workbench(contexts)
    elif page == "运行结果":
        render_results(contexts)
    elif page == "本地代码交互":
        render_code_lab()
    elif page == "大模型问答":
        render_llm_chat(contexts)
    else:
        render_runner()


if __name__ == "__main__":
    if running_in_streamlit():
        main()
    else:
        print_direct_run_help()
