"""
Add lightweight repository metadata to a lead so the ranker can use it.
"""

from __future__ import annotations

from datetime import datetime, timezone

import config
from src.github_client import GitHubClient


def _days_since(iso_ts: str) -> int | None:
    if not iso_ts:
        return None
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - ts
        return delta.days
    except Exception:
        return None


def enrich_lead(lead: dict, gh: GitHubClient) -> dict:
    """Mutate and return the lead dict with repo metadata fields."""
    meta = gh.get_repo_metadata(lead["repo_full_name"])

    lead["repo_stars"] = meta.get("repo_stars", 0)
    lead["repo_updated_at"] = meta.get("repo_updated_at", "")
    lead["is_archived"] = meta.get("is_archived", False)
    lead["language"] = meta.get("language", "") or lead.get("language", "")
    lead["repo_url"] = meta.get("repo_url", "") or (
        f"https://github.com/{lead['repo_full_name']}"
    )
    lead["owner_type"] = meta.get("owner_type", "") or lead.get("owner_type", "")

    days = _days_since(lead["repo_updated_at"])
    lead["days_since_push"] = days if days is not None else 9999
    lead["is_active"] = (
        not lead["is_archived"]
        and days is not None
        and days <= config.ACTIVE_DAYS
    )
    return lead
