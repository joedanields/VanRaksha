"""Threat scoring engine."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from threat.species_index import get_danger_score


# Distance band multipliers applied to the final score when a human is detected.
# Bands are expressed as a fraction of frame width (pixel_distance / frame_width).
_DISTANCE_BANDS = [
    (0.10, 1.50),   # < 10% frame width  → VERY CLOSE  (1.5× multiplier)
    (0.20, 1.25),   # 10–20%             → CLOSE        (1.25×)
    (0.40, 1.00),   # 20–40%             → MODERATE     (1.0×)
    (float("inf"), 0.80),  # > 40%       → FAR           (0.8×)
]


def _distance_multiplier(distance_px: float, frame_width: float) -> float:
    """Return a score multiplier based on pixel distance between animal and human.

    A smaller distance → larger multiplier → higher threat score.
    If distance or frame_width are invalid, returns 1.0 (neutral).
    """
    if not frame_width or distance_px < 0:
        return 1.0
    ratio = distance_px / frame_width
    for threshold, multiplier in _DISTANCE_BANDS:
        if ratio < threshold:
            return multiplier
    return 0.80  # fallback (should never reach here)


class ThreatScorer:
    """Compute wildlife threat score in range 0-100."""

    def score(
        self,
        species: str,
        bbox: list,
        frame_shape: tuple,
        animal_count: int,
        detection_confidence: float,
        distance_px: float | None = None,
    ) -> float:
        """Return weighted threat score from species, proximity, time, confidence and distance.

        Args:
            species:              Normalised species label.
            bbox:                 Bounding box [x1, y1, x2, y2] in pixels.
            frame_shape:          OpenCV frame.shape tuple (height, width, channels).
            animal_count:         Number of animals of this species detected.
            detection_confidence: YOLO detection confidence in [0, 1].
            distance_px:          Pixel distance between animal centre and nearest human centre.
                                  Pass None or negative when no human is present.
        """
        species_danger = get_danger_score(species)

        frame_width = frame_shape[1]
        bbox_width = max(0, bbox[2] - bbox[0])
        coverage = (bbox_width / frame_width) if frame_width else 0
        if coverage > 0.4:
            proximity_score = 10
        elif coverage > 0.2:
            proximity_score = 7
        elif coverage > 0.1:
            proximity_score = 4
        else:
            proximity_score = 1

        hour = datetime.now(timezone.utc).hour
        time_multiplier = 1.4 if hour >= 18 or hour < 6 else 1.0
        animal_count_factor = min(animal_count, 5) * 2
        base_detection_score = max(0.0, min(detection_confidence, 1.0)) * 10

        raw_score = (
            (species_danger / 10) * 35
            + proximity_score * 30
            + time_multiplier * 10
            + animal_count_factor * 5
            + base_detection_score * 20
        )

        # Apply distance-based multiplier when a human is visible nearby.
        if distance_px is not None and distance_px >= 0 and frame_width:
            raw_score *= _distance_multiplier(distance_px, float(frame_width))

        return round(max(0.0, min(raw_score, 100.0)), 2)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    scorer = ThreatScorer()
    logging.getLogger(__name__).info(
        "Threat scorer self-test (tiger, very close): %s",
        scorer.score("tiger", [0, 0, 400, 200], (720, 1280, 3), 2, 0.9, distance_px=60),
    )
    logging.getLogger(__name__).info(
        "Threat scorer self-test (deer, far): %s",
        scorer.score("deer", [0, 0, 100, 80], (720, 1280, 3), 1, 0.7, distance_px=600),
    )
    logging.getLogger(__name__).info(
        "Threat scorer self-test (deer, very close): %s",
        scorer.score("deer", [400, 200, 500, 350], (720, 1280, 3), 1, 0.85, distance_px=50),
    )

