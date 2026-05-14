"""Threat scoring engine."""
from __future__ import annotations

from datetime import datetime

from threat.species_index import get_danger_score


class ThreatScorer:
    """Compute wildlife threat score in range 0-100."""

    def score(self, species: str, bbox: list, frame_shape: tuple, animal_count: int, detection_confidence: float) -> float:
        """Return weighted threat score from species, proximity, time and confidence."""
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

        hour = datetime.now().hour
        time_multiplier = 1.4 if hour >= 18 or hour < 6 else 1.0
        animal_count_factor = min(animal_count, 5) * 2
        base_detection_score = max(0.0, min(detection_confidence, 1.0)) * 10

        score = (
            (species_danger / 10) * 35
            + proximity_score * 30
            + time_multiplier * 10
            + animal_count_factor * 5
            + base_detection_score * 20
        )
        return round(max(0.0, min(score, 100.0)), 2)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    scorer = ThreatScorer()
    logging.getLogger(__name__).info(
        "Threat scorer self-test: %s",
        scorer.score("tiger", [0, 0, 400, 200], (720, 1280, 3), 2, 0.9),
    )
