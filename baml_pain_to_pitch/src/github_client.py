"""
Thin GitHub REST API client.

Handles:
  - code search           (GET /search/code)
  - file content          (GET /repos/{owner}/{repo}/contents/{path})
  - repository metadata    (GET /repos/{owner}/{repo})

Includes retry/backoff for secondary rate limits and a mandatory pause
between code-search calls (code search is limited to ~10 req/min).
"""

from __future__ import annotations

import base64
import time

import requests

import config


class GitHubClient:
    def __init__(self, token: str):
        if not token:
            raise ValueError("GitHub token is required.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "baml-pain-to-pitch-agent",
            }
        )

    # -----------------------------------------------------------------
    # Low level request with retry/backoff
    # -----------------------------------------------------------------
    def _get(self, url: str, params: dict | None = None) -> requests.Response | None:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(
                    url, params=params, timeout=config.REQUEST_TIMEOUT
                )
            except requests.RequestException as exc:
                print(f"  [warn] request error ({attempt}/{config.MAX_RETRIES}): {exc}")
                time.sleep(3 * attempt)
                continue

            # Primary / secondary rate limit
            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After")
                remaining = resp.headers.get("X-RateLimit-Remaining")
                if retry_after:
                    wait = int(retry_after)
                elif remaining == "0":
                    reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                    wait = max(5, reset - int(time.time()) + 2)
                else:
                    wait = 15 * attempt
                print(f"  [warn] rate limited, sleeping {wait}s "
                      f"({attempt}/{config.MAX_RETRIES})")
                time.sleep(min(wait, 90))
                continue

            return resp

        print("  [error] giving up after retries")
        return None

    # -----------------------------------------------------------------
    # Code search
    # -----------------------------------------------------------------
    def search_code(self, query: str, per_page: int) -> list[dict]:
        """Return a list of candidate file dicts for one query."""
        url = f"{config.GITHUB_API}/search/code"
        params = {"q": query, "per_page": per_page}
        resp = self._get(url, params)

        if resp is None:
            return []
        if resp.status_code == 422:
            print(f"  [skip] query rejected by GitHub (422): {query}")
            return []
        if resp.status_code != 200:
            print(f"  [skip] query failed ({resp.status_code}): {query}")
            return []

        items = resp.json().get("items", [])
        results = []
        for it in items:
            repo = it.get("repository", {})
            results.append(
                {
                    "repo_full_name": repo.get("full_name", ""),
                    "owner": repo.get("owner", {}).get("login", ""),
                    "owner_type": repo.get("owner", {}).get("type", ""),
                    "repo_name": repo.get("name", ""),
                    "file_path": it.get("path", ""),
                    "file_url": it.get("html_url", ""),
                    "matched_query": query,
                }
            )
        return results

    # -----------------------------------------------------------------
    # File content
    # -----------------------------------------------------------------
    def get_file_content(self, repo_full_name: str, file_path: str) -> str | None:
        """Return decoded text content of a file, or None on failure."""
        url = f"{config.GITHUB_API}/repos/{repo_full_name}/contents/{file_path}"
        resp = self._get(url)
        if resp is None or resp.status_code != 200:
            return None

        data = resp.json()
        if data.get("encoding") == "base64" and data.get("content"):
            try:
                raw = base64.b64decode(data["content"])
                return raw.decode("utf-8", errors="replace")
            except Exception:
                return None

        # Fallback to the raw download url
        dl = data.get("download_url")
        if dl:
            try:
                r = self.session.get(dl, timeout=config.REQUEST_TIMEOUT)
                if r.status_code == 200:
                    return r.text
            except requests.RequestException:
                return None
        return None

    # -----------------------------------------------------------------
    # Repository metadata
    # -----------------------------------------------------------------
    def get_repo_metadata(self, repo_full_name: str) -> dict:
        url = f"{config.GITHUB_API}/repos/{repo_full_name}"
        resp = self._get(url)
        if resp is None or resp.status_code != 200:
            return {}

        d = resp.json()
        return {
            "repo_stars": d.get("stargazers_count", 0),
            "repo_updated_at": d.get("pushed_at", ""),
            "is_archived": d.get("archived", False),
            "language": d.get("language", ""),
            "repo_url": d.get("html_url", ""),
            "owner_type": d.get("owner", {}).get("type", ""),
        }

    @staticmethod
    def pause_between_code_searches() -> None:
        time.sleep(config.CODE_SEARCH_SLEEP_SECONDS)
