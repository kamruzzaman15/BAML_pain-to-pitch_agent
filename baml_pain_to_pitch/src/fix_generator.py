"""
Stage 7: Generate an illustrative BAML rewrite of the brittle section.

Two quality gates:
  1. The BAML code field must be non-empty (handled by ollama_client).
  2. The BAML code must LOOK like real BAML, not Python. A small model
     often returns a Python class or copies the original parsing loop.
     We reject that and retry, so the final rewrite is much cleaner.
"""

from __future__ import annotations

from src.ollama_client import OllamaClient
from src.resources import get_schema, render_prompt

_SCHEMA = get_schema("fix_schema.json")

# Signs the model returned fake/Python output instead of real BAML.
_BAD_SIGNS = [
    "json.loads",
    "json.parse",
    "try:",
    "except",
    "@prompt",
    "def __init__",
    "import openai",
    "requests.post",
]

# At least one of these should appear in real BAML.
_GOOD_SIGNS = [
    "class ",
    "function ",
    "client ",
    "prompt #",
]


def _looks_like_real_baml(code: str) -> bool:
    if not code or not code.strip():
        return False
    low = code.lower()
    if any(bad in low for bad in _BAD_SIGNS):
        return False
    return any(good in low for good in _GOOD_SIGNS)


def generate_fix(lead: dict, llm: OllamaClient) -> dict | None:
    base_prompt = render_prompt(
        "fix_prompt.txt",
        repo_full_name=lead.get("repo_full_name", ""),
        file_path=lead.get("file_path", ""),
        pain_type=lead.get("pain_type", "other"),
        use_case=lead.get("use_case", "unknown"),
        snippet_text=lead.get("snippet_text", ""),
    )

    # Up to 2 rounds. The second round adds a strong corrective note.
    for round_num in (1, 2):
        prompt = base_prompt
        if round_num == 2:
            prompt = (
                base_prompt
                + "\n\nYOUR LAST ANSWER WAS WRONG. It contained Python or "
                "manual parsing. Return ONLY real BAML: a `class` block "
                "and a `function` block with `client` and `prompt #\" \"#`. "
                "No json.loads, no try/except, no Python class."
            )
        result = llm.chat_json(
            prompt,
            _SCHEMA,
            required_nonempty=["baml_schema_or_function"],
            label="fix",
        )
        if result is None:
            continue
        if _looks_like_real_baml(result.get("baml_schema_or_function", "")):
            return result
        print(
            f"   [fix] round {round_num}: output was not real BAML "
            f"(looked like Python), retrying"
        )

    # Return the last attempt even if imperfect, so the lead still has
    # something. The write-up can note this as a known limitation.
    return result
