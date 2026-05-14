"""Alert level mapping."""
from enum import Enum


class AlertLevel(Enum):
    """Threat alert levels."""

    SAFE = ("SAFE", "green", 0)
    CAUTION = ("CAUTION", "yellow", 1)
    HIGH = ("HIGH", "orange", 2)
    CRITICAL = ("CRITICAL", "red", 3)


def get_alert_level(score: float) -> AlertLevel:
    """Map numeric score to alert level."""
    if score <= 25:
        return AlertLevel.SAFE
    if score <= 50:
        return AlertLevel.CAUTION
    if score <= 75:
        return AlertLevel.HIGH
    return AlertLevel.CRITICAL


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("Alert level self-test: %s", get_alert_level(76).name)
