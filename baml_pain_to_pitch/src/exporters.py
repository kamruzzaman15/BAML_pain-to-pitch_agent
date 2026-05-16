"""
Save pipeline outputs:
  - raw_candidates.csv
  - qualified_leads.csv
  - final_ranked_leads.csv
  - top_examples.md   (best N leads formatted for the write-up)
"""

from __future__ import annotations

import pandas as pd

import config

FINAL_COLUMNS = [
    "lead_rank",
    "repo_full_name",
    "owner",
    "owner_type",
    "file_path",
    "repo_url",
    "file_url",
    "language",
    "pain_type",
    "use_case",
    "pain_score",
    "confidence",
    "evidence",
    "why_baml_may_help",
    "repo_stars",
    "days_since_push",
    "is_archived",
    "repo_activity_score",
    "org_fit_score",
    "lead_score",
    "fix_summary",
    "baml_schema_or_function",
    "example_client_usage",
    "limits",
    "outreach_message",
    "tone_check",
    "snippet_text",
]


def _to_df(rows: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if columns:
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        df = df[columns]
    return df


def save_raw_candidates(rows: list[dict]) -> None:
    _to_df(rows).to_csv(config.RAW_CANDIDATES_CSV, index=False)


def save_qualified(rows: list[dict]) -> None:
    _to_df(rows).to_csv(config.QUALIFIED_LEADS_CSV, index=False)


def save_final(rows: list[dict]) -> None:
    _to_df(rows, FINAL_COLUMNS).to_csv(config.FINAL_RANKED_CSV, index=False)


def write_top_examples(rows: list[dict], count: int | None = None) -> None:
    count = count or config.TOP_EXAMPLES_COUNT
    top = rows[:count]
    lines: list[str] = []
    lines.append("# BAML Pain-to-Pitch — Top Examples\n")
    lines.append(
        "Best leads produced by the agent. Each one shows the public "
        "pain signal, the model's diagnosis, an illustrative BAML-style "
        "rewrite, and a human-reviewable outreach draft.\n"
    )

    for i, r in enumerate(top, start=1):
        lines.append(f"\n---\n\n## Example {i}: {r.get('repo_full_name', '')}\n")
        lines.append(f"- **Source file:** {r.get('file_url', '')}")
        lines.append(f"- **Language:** {r.get('language', '')}")
        lines.append(
            f"- **Pain type:** {r.get('pain_type', '')}  |  "
            f"**Use case:** {r.get('use_case', '')}"
        )
        lines.append(
            f"- **Pain score:** {r.get('pain_score', '')}/5  |  "
            f"**Confidence:** {r.get('confidence', '')}  |  "
            f"**Lead score:** {r.get('lead_score', '')}"
        )
        lines.append(f"- **Why BAML may help:** {r.get('why_baml_may_help', '')}\n")

        lines.append("### Original brittle code\n")
        lines.append("```\n" + str(r.get("snippet_text", "")).strip() + "\n```\n")

        lines.append("### Agent diagnosis\n")
        lines.append(str(r.get("evidence", "")).strip() + "\n")

        lines.append("### Illustrative BAML-style rewrite\n")
        lines.append(
            "```\n" + str(r.get("baml_schema_or_function", "")).strip() + "\n```\n"
        )
        lines.append("**Client usage:**\n")
        lines.append(
            "```\n" + str(r.get("example_client_usage", "")).strip() + "\n```\n"
        )
        lines.append(
            f"_Limits:_ {str(r.get('limits', '')).strip()}\n"
        )

        lines.append("### Outreach draft (for human review)\n")
        lines.append("> " + str(r.get("outreach_message", "")).strip().replace(
            "\n", "\n> "
        ))
        lines.append(f"\n_Tone check:_ {r.get('tone_check', '')}\n")

    config.TOP_EXAMPLES_MD.write_text("\n".join(lines), encoding="utf-8")
