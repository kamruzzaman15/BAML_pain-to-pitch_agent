"""
Extract a small code window around the first painful anchor line.

We do not send the whole file to the model. We find the first line that
contains a known anchor (json.loads, JSON.parse, etc.) and take a window
of lines before and after it.
"""

from __future__ import annotations

import config


def extract_snippet(file_text: str) -> dict | None:
    """
    Return a dict with the snippet and metadata, or None if no anchor
    is found in the file.
    """
    if not file_text:
        return None

    lines = file_text.splitlines()
    anchor_idx = None
    matched_anchor = None

    for i, line in enumerate(lines):
        for anchor in config.SNIPPET_ANCHORS:
            if anchor in line:
                anchor_idx = i
                matched_anchor = anchor
                break
        if anchor_idx is not None:
            break

    if anchor_idx is None:
        return None

    start = max(0, anchor_idx - config.SNIPPET_LINES_BEFORE)
    end = min(len(lines), anchor_idx + config.SNIPPET_LINES_AFTER + 1)
    snippet = "\n".join(lines[start:end])

    return {
        "snippet_text": snippet,
        "match_keyword": matched_anchor,
        "snippet_start_line": start + 1,   # 1-indexed for humans
        "snippet_end_line": end,
    }
