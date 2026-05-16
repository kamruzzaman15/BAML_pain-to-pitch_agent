"""
Local LLM client using the Ollama HTTP API.

Robust version: smaller models such as qwen2.5-coder:7b often fail to
return clean schema-constrained JSON when the payload contains code with
newlines, quotes, and backticks. So chat_json tries three modes in order:

  1. strict   : format = JSON schema   (best when it works)
  2. loose     : format = "json"        (model still returns JSON)
  3. freeform  : no format              (we extract the JSON ourselves)

It also retries, and prints a truncated raw response when parsing fails
so you can actually see what the model produced.
"""

from __future__ import annotations

import json

import requests

import config


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None):
        self.host = (host or config.OLLAMA_HOST).rstrip("/")
        self.model = model or config.OLLAMA_MODEL

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=10)
            return r.status_code == 200
        except requests.RequestException:
            return False

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def chat_json(
        self,
        prompt: str,
        schema: dict,
        required_nonempty: list[str] | None = None,
        max_attempts: int = 3,
        label: str = "model",
    ) -> dict | None:
        """
        Return a parsed dict, or None after all attempts fail.

        required_nonempty: keys that must be present AND non-empty. If any
        is empty, the result is treated as a failure and we retry with a
        looser mode.
        """
        modes = ["strict", "loose", "freeform"]

        for attempt in range(1, max_attempts + 1):
            mode = modes[min(attempt - 1, len(modes) - 1)]
            content = self._call(prompt, schema, mode)
            if content is None:
                print(f"   [{label}] attempt {attempt} ({mode}): no response")
                continue

            parsed = self._parse_json(content)
            if parsed is None:
                print(
                    f"   [{label}] attempt {attempt} ({mode}): "
                    f"unparseable. raw start: {content.strip()[:160]!r}"
                )
                continue

            if required_nonempty:
                missing = [
                    k
                    for k in required_nonempty
                    if not str(parsed.get(k, "")).strip()
                ]
                if missing:
                    print(
                        f"   [{label}] attempt {attempt} ({mode}): "
                        f"empty fields {missing}, retrying"
                    )
                    continue

            return parsed

        return None

    # -----------------------------------------------------------------
    # Single HTTP call
    # -----------------------------------------------------------------
    def _call(self, prompt: str, schema: dict, mode: str) -> str | None:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192},
        }
        if mode == "strict":
            payload["format"] = schema
        elif mode == "loose":
            payload["format"] = "json"
        # freeform: no format key

        try:
            r = requests.post(
                f"{self.host}/api/chat", json=payload, timeout=300
            )
        except requests.RequestException as exc:
            print(f"   [error] Ollama request failed: {exc}")
            return None

        if r.status_code != 200:
            print(f"   [error] Ollama returned {r.status_code}: {r.text[:200]}")
            return None

        try:
            return r.json().get("message", {}).get("content", "")
        except ValueError:
            return None

    # -----------------------------------------------------------------
    # Lenient JSON parsing
    # -----------------------------------------------------------------
    @staticmethod
    def _parse_json(text: str) -> dict | None:
        if not text:
            return None
        cleaned = text.strip()

        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1]
                if cleaned.lstrip().lower().startswith("json"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        cleaned = cleaned.strip().strip("`").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None
