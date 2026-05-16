"""Helpers to load prompt templates and JSON schemas from disk."""

import json
from functools import lru_cache

import config


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt template by file name, e.g. 'qualify_prompt.txt'."""
    path = config.PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def load_schema(name: str) -> str:
    """Load a JSON schema file and return it as a dict (cached as str)."""
    path = config.SCHEMAS_DIR / name
    return path.read_text(encoding="utf-8")


def get_schema(name: str) -> dict:
    return json.loads(load_schema(name))


def render_prompt(name: str, **values: str) -> str:
    """
    Fill a prompt template safely.

    We do NOT use str.format() because the prompt files contain literal
    curly braces from real BAML code examples (class { ... }, prompt
    #" {{ ctx.output_format }} "#). str.format() would treat those as
    placeholders and crash. Instead we replace only the exact tokens
    "{key}" that we explicitly pass in.
    """
    text = load_prompt(name)
    for key, val in values.items():
        text = text.replace("{" + key + "}", str(val))
    return text
