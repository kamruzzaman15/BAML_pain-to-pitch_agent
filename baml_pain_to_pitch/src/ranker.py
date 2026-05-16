"""
Stage 9: Rank leads with a simple, transparent weighted score.

All component scores are put on a 1 to 5 scale, then combined with the
weights from config. The exact weights matter less than having a clear,
repeatable prioritization mechanism.

    lead_score =
        0.50 * pain_score          (1..5 from the model)
      + 0.25 * confidence_score    (confidence 0..1 mapped to 1..5)
      + 0.15 * repo_activity_score (recent push -> high)
      + 0.10 * org_fit_score       (org-backed / starred -> high)
"""

import config


def _activity_score(lead: dict) -> float:
    if lead.get("is_archived"):
        return 1.0
    days = lead.get("days_since_push", 9999)
    if days <= 30:
        return 5.0
    if days <= 90:
        return 4.0
    if days <= 180:
        return 3.0
    if days <= 365:
        return 2.0
    return 1.0


def _org_fit_score(lead: dict) -> float:
    score = 1.0
    if str(lead.get("owner_type", "")).lower() == "organization":
        score += 2.0
    stars = lead.get("repo_stars", 0) or 0
    if stars >= 500:
        score += 2.0
    elif stars >= 100:
        score += 1.5
    elif stars >= 20:
        score += 1.0
    return min(5.0, score)


def compute_lead_score(lead: dict) -> dict:
    pain = float(lead.get("pain_score", 1))                # 1..5
    confidence = 1.0 + 4.0 * float(lead.get("confidence", 0.0))  # 1..5
    activity = _activity_score(lead)                       # 1..5
    org_fit = _org_fit_score(lead)                         # 1..5

    lead_score = (
        config.WEIGHT_PAIN * pain
        + config.WEIGHT_CONFIDENCE * confidence
        + config.WEIGHT_ACTIVITY * activity
        + config.WEIGHT_ORG_FIT * org_fit
    )

    lead["repo_activity_score"] = round(activity, 2)
    lead["org_fit_score"] = round(org_fit, 2)
    lead["lead_score"] = round(lead_score, 3)
    return lead


def rank(leads: list[dict]) -> list[dict]:
    for lead in leads:
        compute_lead_score(lead)
    ranked = sorted(leads, key=lambda x: x["lead_score"], reverse=True)
    for i, lead in enumerate(ranked, start=1):
        lead["lead_rank"] = i
    return ranked
