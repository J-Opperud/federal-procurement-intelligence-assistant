"""Assess whether retrieved passages are relevant enough to answer a question."""

from collections.abc import Sequence
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def assess_evidence(
    evidence: Sequence[dict[str, Any]],
    *,
    distance_threshold: float | None = None,
) -> bool:
  """Return true when retrieved passages are available and meet the threshold.

  Includes graceful fallbacks for missing or uncalibrated distance scores inside
  containers.
  """
  threshold = (
      settings.retrieval_distance_threshold
      if distance_threshold is None
      else distance_threshold
  )

  if not evidence:
    logger.warning(
        "[EVIDENCE ASSESSMENT] ❌ No evidence chunks were returned by"
        " retrieval."
    )
    return False

  for i, item in enumerate(evidence):
    text = str(item.get("text", "")).strip()
    if not text:
      continue

    distance_val = item.get("distance")

    # Fallback: If distance is missing/None but text exists, trust the retrieval
    if distance_val is None:
      logger.info(
          f"[EVIDENCE ASSESSMENT] ⚠️ Chunk {i} is missing a distance score, but"
          " text is present. Permitting as fallback."
      )
      return True

    try:
      distance = float(distance_val)
      logger.info(
          f"[EVIDENCE ASSESSMENT] 🔍 Chunk {i} distance: {distance} (Threshold:"
          f" {threshold})"
      )

      if 0 <= distance <= threshold:
        logger.info(
            f"[EVIDENCE ASSESSMENT] ✅ PASS! Chunk {i} met distance threshold."
        )
        return True
    except (TypeError, ValueError) as exc:
      logger.warning(
          f"[EVIDENCE ASSESSMENT] ⚠️ Error parsing distance for chunk {i}:"
          f" {exc}. Permitting due to valid text content."
      )
      # If the text is there, don't let a bad float conversion kill the response
      return True

  logger.warning(
      "[EVIDENCE ASSESSMENT] ❌ All retrieved chunks exceeded the distance"
      " threshold or lacked valid text."
  )
  return False