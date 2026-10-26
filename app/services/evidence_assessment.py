"""Assess whether retrieved passages are relevant enough to answer a question."""

from collections.abc import Sequence
from typing import Any

from app.config import settings


def assess_evidence(
    evidence: Sequence[dict[str, Any]],
    *,
    distance_threshold: float | None = None,
) -> bool:
    """Return true only when at least one retrieved passage meets the distance threshold.

    Chroma's cosine distance is lower for more similar passages. An empty result,
    missing score, or malformed score is never treated as sufficient evidence.
    """
    threshold = (
        settings.retrieval_distance_threshold
        if distance_threshold is None
        else distance_threshold
    )
    for item in evidence:
        try:
            distance = float(item["distance"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= distance <= threshold and str(item.get("text", "")).strip():
            return True
    return False
