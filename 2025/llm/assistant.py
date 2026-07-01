# -*- coding: utf-8 -*-
"""Project operation assistant with offline-first language behavior."""

from __future__ import annotations

import json
import os
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .prompts import REPORT_BRIEF_PROMPT, SYSTEM_PROMPT
from .result_context import TaskContext, best_row_by_metric, collect_all_context, format_context_for_prompt


REMOTE_PROVIDERS = {
    "api",
    "openai",
    "openai-compatible",
    "compatible-http",
    "remote",
    "local",
    "local-codex",
    "codex",
    "codex-local",
    "codex-config",
}
LOCAL_PROVIDERS = {"local", "local-codex", "codex", "codex-local", "openai-compatible", "compatible-http"}


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "offline"
    model: str = "offline-template"
    api_key: str = ""
    base_url: str = ""
    wire_api: str = "chat"
    timeout_seconds: int = 20
    source: str = "default"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        provider_from_env = (
            os.getenv("PV_LLM_PROVIDER")
            or os.getenv("CODEX_LLM_PROVIDER")
            or os.getenv("OPENAI_PROVIDER")
        )
        if not provider_from_env:
            codex_config = cls.from_codex_config()
            if codex_config is not None:
                return codex_config

        provider = (provider_from_env or "offline").strip().lower() or "offline"
        model = (
            os.getenv("PV_LLM_MODEL")
            or os.getenv("CODEX_LLM_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "offline-template"
        )
        api_key = (
            os.getenv("PV_LLM_API_KEY")
            or os.getenv("CODEX_LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        base_url = (
            os.getenv("PV_LLM_BASE_URL")
            or os.getenv("CODEX_LLM_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or ""
        )
        wire_api = (
            os.getenv("PV_LLM_WIRE_API")
            or os.getenv("CODEX_LLM_WIRE_API")
            or os.getenv("OPENAI_WIRE_API")
            or "chat"
        )
        return cls(
            provider=provider,
            model=model.strip() or "offline-template",
            api_key=api_key.strip(),
            base_url=base_url.strip(),
            wire_api=wire_api.strip().lower() or "chat",
            timeout_seconds=int(os.getenv("PV_LLM_TIMEOUT", "20")),
            source="environment",
        )

    @classmethod
    def from_codex_config(cls) -> "LLMConfig | None":
        codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
        config_path = codex_home / "config.toml"
        auth_path = codex_home / "auth.json"
        if not config_path.exists():
            return None

        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return None

        provider_name = str(config.get("model_provider") or "").strip()
        providers = config.get("model_providers") or {}
        provider_config = providers.get(provider_name) if provider_name else None
        if not isinstance(provider_config, dict):
            return None

        base_url = str(provider_config.get("base_url") or "").strip()
        if not base_url:
            return None

        api_key = ""
        if auth_path.exists():
            try:
                auth = json.loads(auth_path.read_text(encoding="utf-8"))
                api_key = str(auth.get("OPENAI_API_KEY") or "").strip()
            except (OSError, json.JSONDecodeError):
                api_key = ""

        return cls(
            provider="codex-config",
            model=str(config.get("model") or "gpt-5.5").strip(),
            api_key=api_key,
            base_url=base_url,
            wire_api=str(provider_config.get("wire_api") or "chat").strip().lower() or "chat",
            timeout_seconds=int(os.getenv("PV_LLM_TIMEOUT", "90")),
            source=str(config_path),
        )

    def endpoint(self) -> str:
        if not self.base_url:
            if self.wire_api == "responses":
                return "https://api.openai.com/v1/responses"
            return "https://api.openai.com/v1/chat/completions"
        base_url = self.base_url.rstrip("/")
        if self.wire_api == "responses":
            if base_url.endswith("/responses"):
                return base_url
            if base_url.endswith("/v1"):
                return f"{base_url}/responses"
            return f"{base_url}/v1/responses"
        if base_url.endswith("/chat/completions"):
            return base_url
        if base_url.endswith("/v1"):
            return f"{base_url}/chat/completions"
        return f"{base_url}/v1/chat/completions"

    def endpoint_display(self) -> str:
        if self.provider == "offline":
            return "offline-template"
        api_key_state = "set" if self.api_key else "empty/local"
        return (
            f"provider={self.provider}; model={self.model}; wire_api={self.wire_api}; "
            f"endpoint={self.endpoint()}; api_key={api_key_state}; source={self.source}"
        )

    def requires_api_key(self) -> bool:
        return self.provider in {"api", "openai", "remote", "codex-config"} and not self.api_key


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    used_remote: bool = False
    error: str = ""


def _label(row: dict[str, str] | None) -> str:
    if not row:
        return "暂无记录"
    return row.get("模型_输入") or row.get("模型") or row.get("Model") or row.get("index") or "记录"


def _metric(row: dict[str, str] | None, key: str) -> str:
    if not row:
        return "暂无"
    return row.get(key) or "暂无"


def _offline_answer(question: str, contexts: dict[str, TaskContext]) -> str:
    q = question.lower()
    task2 = contexts.get("2")
    task3 = contexts.get("3")
    task4 = contexts.get("4")
    row2 = best_row_by_metric(task2) if task2 else None
    row3 = best_row_by_metric(task3) if task3 else None
    row4 = best_row_by_metric(task4) if task4 else None

    if any(key in q for key in ("lmd", "mixed", "混合", "降尺度", "局地", "校正", "输入评估")):
        return (
            "局地校正融合链路比较了NWP、LMD和NWP+LMD混合输入。LMD代表更贴近站点局地状态的实测气象信息，"
            "混合输入同时保留NWP的日前预报性和LMD的局地尺度特征。"
            f"当前最优组合为{_label(row4)}，E_rmse={_metric(row4, 'E_rmse')}，"
            f"C_R={_metric(row4, 'C_R')}%，Q_R={_metric(row4, 'Q_R')}%。"
            "该结果支持“空间降尺度或局地气象补充可以改善光伏功率预测”的结论。"
        )

    if any(key in q for key in ("nwp", "气象", "预报融合", "提升")):
        return (
            "气象预报融合链路在历史功率序列之外加入目标日NWP气象序列，使模型提前看到辐照、温度、湿度、风速等未来天气条件。"
            f"当前结果中，历史功率基线最优为{_label(row2)}，E_rmse={_metric(row2, 'E_rmse')}，C_R={_metric(row2, 'C_R')}%；"
            f"气象预报融合最优为{_label(row3)}，E_rmse={_metric(row3, 'E_rmse')}，C_R={_metric(row3, 'C_R')}%。"
            "这说明气象信息能降低白昼归一化误差，并提升日前预测对天气扰动的响应能力。"
        )

    if any(key in q for key in ("e_rmse", "c_r", "q_r", "附件", "指标")):
        return (
            "附件1指标采用装机容量归一化误差。E_rmse越小，说明预测曲线相对容量的均方误差越低；"
            "C_R=(1-E_rmse)*100%，越高表示准确率越好；Q_R统计归一化绝对误差小于0.25的样本比例，"
            "越高表示预测点更稳定地落在合格阈值内。本项目核心预测链路的指标都只在白昼时段统计。"
        )

    if any(key in q for key in ("不足", "改进", "展望", "材料", "期末")):
        return (
            "当前项目的主要不足包括：深度模型定义仍有重复、历史工作区体积较大、LLM模块默认采用离线模板兜底、"
            "交付报告仍需和最新outputs指标完全同步。后续可继续抽取统一预测模型模块，压缩提交包，"
            "并接入本地轻量语言接口或稳定API来增强自然语言问答能力。"
        )

    if any(key in q for key in ("app.py", "run_project", "llm", "代码", "协同", "入口")):
        return (
            "软件入口采用三层协同：run_project.py 负责项目级任务编排、依赖顺序和 outputs 查看；"
            "llm/result_context.py 把各条链路的运行摘要和指标表整理成结构化上下文；"
            "app.py 负责 Streamlit 交互界面，把结果浏览、代码查看、安全命令和运行解读组织到同一个控制台。"
            "这样教师或演示视频可以先双击 start_software.vbs 进入桌面启动器，再按页面查看结果或提问，不必直接接触训练脚本。"
        )

    return (
        "本项目围绕光伏电站日前功率预测建立了完整工程闭环：站点机理诊断用于把握理论功率与发电特性，"
        "历史功率基线提供无天气输入时的保底预测能力，气象预报融合把NWP信息纳入日前计划，"
        "局地校正融合比较NWP、LMD和混合输入以验证空间降尺度价值。"
        f"当前关键结论是：历史功率基线最优{_label(row2)}，气象预报融合最优{_label(row3)}，"
        f"局地校正融合最优{_label(row4)}。"
    )


def _headers(config: LLMConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _extract_responses_text(data: dict[str, object]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    output = data.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text") or part.get("content")
                if isinstance(text, str) and text.strip():
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)
    raise ValueError("remote LLM response has empty output text")


def _remote_responses(messages: list[dict[str, str]], config: LLMConfig) -> str:
    payload = {
        "model": config.model,
        "input": messages,
        "temperature": 0.2,
        "max_output_tokens": 700,
    }
    request = urllib.request.Request(
        config.endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(config),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    return _extract_responses_text(data)


def _remote_chat(messages: list[dict[str, str]], config: LLMConfig) -> str:
    if config.requires_api_key():
        raise ValueError("PV_LLM_API_KEY or OPENAI_API_KEY is empty")
    if config.wire_api == "responses":
        return _remote_responses(messages, config)
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    request = urllib.request.Request(
        config.endpoint(),
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(config),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("remote LLM response has no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise ValueError("remote LLM response has empty content")
    return str(content)


def answer_question(
    question: str,
    contexts: dict[str, TaskContext] | None = None,
    config: LLMConfig | None = None,
    history: Sequence[dict[str, str]] | None = None,
    extra_context: str = "",
) -> LLMResponse:
    contexts = contexts or collect_all_context()
    config = config or LLMConfig.from_env()
    context_text = format_context_for_prompt(contexts)
    if extra_context.strip():
        context_text = f"{context_text}\n\n补充代码上下文：\n{extra_context.strip()}"

    if config.provider in REMOTE_PROVIDERS:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for item in list(history or [])[-8:]:
            role = item.get("role", "")
            content = item.get("content", "")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:4000]})
        messages.append({"role": "user", "content": f"{context_text}\n\n问题：{question}"})
        try:
            return LLMResponse(
                text=_remote_chat(messages, config),
                provider=config.provider,
                used_remote=True,
            )
        except (ValueError, urllib.error.URLError, TimeoutError) as exc:
            fallback = _offline_answer(question, contexts)
            return LLMResponse(
                text=f"{fallback}\n\n远程语言接口调用失败，已使用离线模板兜底。错误：{exc}",
                provider="offline-fallback",
                used_remote=False,
                error=str(exc),
            )

    return LLMResponse(text=_offline_answer(question, contexts), provider="offline-template")


def generate_report_brief(
    contexts: dict[str, TaskContext] | None = None,
    config: LLMConfig | None = None,
) -> LLMResponse:
    return answer_question(REPORT_BRIEF_PROMPT, contexts=contexts, config=config)
