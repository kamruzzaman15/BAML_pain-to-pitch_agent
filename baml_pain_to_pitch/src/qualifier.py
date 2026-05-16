"""
Stage 5: Qualification.

Two layers:
  1. A deterministic guard. If the snippet contains NO sign of a language
     model call at all, it is rejected before the model is even asked.
     This kills the obvious false positives (profiler logs, SQL columns,
     config files) where json.loads is unrelated to any LLM.
  2. The local model judges the remaining snippets and scores the pain.
"""

from __future__ import annotations

import config
from src.ollama_client import OllamaClient
from src.resources import get_schema, render_prompt

_SCHEMA = get_schema("qualification_schema.json")

# Lowercased tokens that indicate a real language model call/usage.
LLM_INDICATORS = [
    "openai",
    "anthropic",
    "claude",
    "gpt-",
    "gpt3",
    "gpt4",
    "gemini",
    "mistral",
    "ollama",
    "litellm",
    "langchain",
    "llamaindex",
    "chat.completions",
    "completions.create",
    "completion(",
    "messages=[",
    'role": "system"',
    "role': 'system'",
    "huggingface",
    "transformers",
    "vllm",
    "llm.",
    "llm(",
    "_llm",
    "llm_",
    "chatcompletion",
    "generate(",
    "model=",
]


def snippet_has_llm_signal(snippet: str) -> bool:
    """Cheap check: does the snippet look like it touches a model at all."""
    if not snippet:
        return False
    low = snippet.lower()
    return any(tok in low for tok in LLM_INDICATORS)


def qualify(lead: dict, llm: OllamaClient) -> dict | None:
    """
    Return a qualification dict. If the deterministic guard fails, return
    a hard rejection without calling the model.
    """
    snippet = lead.get("snippet_text", "")

    if not snippet_has_llm_signal(snippet):
        return {
            "is_baml_relevant": False,
            "pain_score": 1,
            "confidence": 1.0,
            "pain_type": "other",
            "use_case": "unknown",
            "evidence": "No language model call visible in the snippet, "
            "so the json parsing is unrelated to LLM output.",
            "why_baml_may_help": "Not applicable. BAML is for LLM "
            "structured output, and no LLM call is present here.",
            "rejected_by_guard": True,
        }

    prompt = render_prompt(
        "qualify_prompt.txt",
        repo_full_name=lead.get("repo_full_name", ""),
        file_path=lead.get("file_path", ""),
        matched_query=lead.get("matched_query", ""),
        snippet_text=snippet,
    )
    result = llm.chat_json(prompt, _SCHEMA, label="qualify")
    if result is None:
        return None

    try:
        result["pain_score"] = max(1, min(5, int(result.get("pain_score", 1))))
    except (TypeError, ValueError):
        result["pain_score"] = 1
    try:
        result["confidence"] = max(
            0.0, min(1.0, float(result.get("confidence", 0.0)))
        )
    except (TypeError, ValueError):
        result["confidence"] = 0.0

    result["rejected_by_guard"] = False
    return result


def passes_threshold(qual: dict) -> bool:
    return (
        bool(qual.get("is_baml_relevant"))
        and not qual.get("rejected_by_guard", False)
        and qual.get("pain_score", 0) >= config.MIN_PAIN_SCORE
        and qual.get("confidence", 0.0) >= config.MIN_CONFIDENCE
    )
