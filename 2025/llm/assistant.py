# -*- coding: utf-8 -*-
"""Project result assistant with offline-first LLM behavior."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .prompts import REPORT_BRIEF_PROMPT, SYSTEM_PROMPT
from .result_context import TaskContext, best_row_by_metric, collect_all_context, compact_metric_row, format_context_for_prompt


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "offline"
    model: str = "offline-template"
    api_key: str = ""
    base_url: str = ""
    timeout_seconds: int = 20

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            provider=os.getenv("PV_LLM_PROVIDER", "offline").strip().lower() or "offline",
            model=os.getenv("PV_LLM_MODEL", "offline-template").strip() or "offline-template",
            api_key=os.getenv("PV_LLM_API_KEY", "").strip(),
            base_url=os.getenv("PV_LLM_BASE_URL", "").strip(),
            timeout_seconds=int(os.getenv("PV_LLM_TIMEOUT", "20")),
        )


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

    if any(key in q for key in ("lmd", "mixed", "混合", "降尺度", "问题4")):
        return (
            "问题4比较了NWP、LMD和NWP+LMD混合输入。LMD代表更贴近站点局地状态的实测气象信息，"
            "混合输入同时保留NWP的日前预报性和LMD的局地尺度特征。"
            f"当前最优组合为{_label(row4)}，E_rmse={_metric(row4, 'E_rmse')}，"
            f"C_R={_metric(row4, 'C_R')}%，Q_R={_metric(row4, 'Q_R')}%。"
            "该结果支持“空间降尺度或局地气象补充可以改善光伏功率预测”的结论。"
        )

    if any(key in q for key in ("nwp", "气象", "问题3", "提升")):
        return (
            "问题3在历史功率序列之外加入目标日NWP气象序列，使模型提前看到辐照、温度、湿度、风速等未来天气条件。"
            f"当前结果中，问题2最优为{_label(row2)}，E_rmse={_metric(row2, 'E_rmse')}，C_R={_metric(row2, 'C_R')}%；"
            f"问题3最优为{_label(row3)}，E_rmse={_metric(row3, 'E_rmse')}，C_R={_metric(row3, 'C_R')}%。"
            "这说明气象信息能降低白昼归一化误差，并提升日前预测对天气扰动的响应能力。"
        )

    if any(key in q for key in ("e_rmse", "c_r", "q_r", "附件", "指标")):
        return (
            "附件1指标采用装机容量归一化误差。E_rmse越小，说明预测曲线相对容量的均方误差越低；"
            "C_R=(1-E_rmse)*100%，越高表示准确率越好；Q_R统计归一化绝对误差小于0.25的样本比例，"
            "越高表示预测点更稳定地落在合格阈值内。本项目所有问题2-4的核心指标都只在白昼时段统计。"
        )

    if any(key in q for key in ("不足", "改进", "展望")):
        return (
            "当前项目的主要不足包括：深度模型定义仍有重复、历史工作区体积较大、LLM模块默认采用离线模板兜底、"
            "最终课程主报告仍需和最新outputs指标完全同步。后续可继续抽取统一预测模型模块，压缩提交包，"
            "并接入本地轻量大模型或稳定API来增强自然语言问答能力。"
        )

    return (
        "本项目围绕光伏电站日前功率预测建立了完整工程闭环：问题1进行理论功率与发电特性分析，"
        "问题2建立历史功率基准深度学习模型，问题3加入NWP气象信息并做场景划分，"
        "问题4比较NWP、LMD和混合输入以验证空间降尺度价值。"
        f"当前关键结论是：问题2最优{_label(row2)}，问题3最优{_label(row3)}，"
        f"问题4最优{_label(row4)}。"
    )


def _remote_chat(messages: list[dict[str, str]], config: LLMConfig) -> str:
    if not config.api_key:
        raise ValueError("PV_LLM_API_KEY is empty")
    base_url = config.base_url or "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": config.model,
        "messages": messages,
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
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
) -> LLMResponse:
    contexts = contexts or collect_all_context()
    config = config or LLMConfig.from_env()
    context_text = format_context_for_prompt(contexts)

    if config.provider in {"api", "openai", "openai-compatible", "remote"}:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{context_text}\n\n问题：{question}"},
        ]
        try:
            return LLMResponse(
                text=_remote_chat(messages, config),
                provider=config.provider,
                used_remote=True,
            )
        except (ValueError, urllib.error.URLError, TimeoutError) as exc:
            fallback = _offline_answer(question, contexts)
            return LLMResponse(
                text=f"{fallback}\n\n远程大模型调用失败，已使用离线模板兜底。错误：{exc}",
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
