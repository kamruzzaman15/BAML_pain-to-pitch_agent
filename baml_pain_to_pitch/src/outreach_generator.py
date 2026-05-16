"""
Stage 8: Draft a short, human-reviewed outreach message.

Nothing is auto-sent. This only produces a draft for review.
"""

from __future__ import annotations

from src.ollama_client import OllamaClient
from src.resources import get_schema, render_prompt

_SCHEMA = get_schema("outreach_schema.json")


def generate_outreach(lead: dict, llm: OllamaClient) -> dict | None:
    prompt = render_prompt(
        "outreach_prompt.txt",
        repo_full_name=lead.get("repo_full_name", ""),
        pain_type=lead.get("pain_type", "other"),
        why_baml_may_help=lead.get("why_baml_may_help", ""),
        fix_summary=lead.get("fix_summary", ""),
    )
    return llm.chat_json(
        prompt,
        _SCHEMA,
        required_nonempty=["message"],
        label="outreach",
    )
