# -*- coding: utf-8 -*-
"""LLM-assisted result interpretation for the PV forecasting project."""

from .assistant import LLMConfig, LLMResponse, answer_question, generate_report_brief
from .result_context import TaskContext, collect_all_context, format_context_for_prompt

__all__ = [
    "LLMConfig",
    "LLMResponse",
    "TaskContext",
    "answer_question",
    "collect_all_context",
    "format_context_for_prompt",
    "generate_report_brief",
]
