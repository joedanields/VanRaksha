"""Frame annotation helpers."""
from __future__ import annotations

import cv2

from threat.alert_level import AlertLevel


COLOR_MAP = {
    AlertLevel.SAFE: (0, 255, 0),
    AlertLevel.CAUTION: (0, 255, 255),
    AlertLevel.HIGH: (0, 165, 255),
    AlertLevel.CRITICAL: (0, 0, 255),
}


def annotate_detection(
    frame,
    bbox,
    species: str,
    confidence: float,
    score: float,
    alert_level: AlertLevel,
    draw_frame_border: bool = True,
    label_override: str | None = None,
    risk_label: str | None = None,
):
    """Draw bbox and status labels over frame.

    Args:
        risk_label: When provided, shown in the caption instead of the raw alert
                    level name (e.g. 'HIGH RISK – TIGER').
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    color = COLOR_MAP[alert_level]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    if label_override:
        caption = label_override
    elif risk_label:
        caption = f"{species} {confidence:.2f} | {score:.1f} | {risk_label}"
    else:
        caption = f"{species} {confidence:.2f} | {score:.1f} {alert_level.name}"

    cv2.putText(frame, caption, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    if draw_frame_border:
        cv2.rectangle(frame, (0, 0), (frame.shape[1] - 1, frame.shape[0] - 1), color, 6)
    return frame


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("Drawing self-test: import successful")
