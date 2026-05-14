"""YOLOv8 wildlife detector wrapper."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None


class WildlifeDetector:
    """Run YOLOv8 inference and normalize detections."""

    def __init__(self, model_path: str, confidence_threshold: float = 0.5):
        self.logger = logging.getLogger(__name__)
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.model = None
        if YOLO is None:
            self.logger.warning("ultralytics not available; detector disabled")
            return
        try:
            self.model = YOLO(str(self.model_path))
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Failed to load YOLO model: %s", exc)
            self.model = None

    def detect(self, frame: np.ndarray) -> list[dict]:
        """Return filtered detections with bbox, confidence, class_id and label."""
        if self.model is None or frame is None:
            return []
        detections: list[dict] = []
        try:
            results = self.model(frame, verbose=False)
            for result in results:
                names = result.names if hasattr(result, "names") else {}
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    confidence = float(box.conf.item())
                    if confidence < self.confidence_threshold:
                        continue
                    class_id = int(box.cls.item())
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                    detections.append(
                        {
                            "bbox": [x1, y1, x2, y2],
                            "confidence": confidence,
                            "class_id": class_id,
                            "label": names.get(class_id, str(class_id)),
                        }
                    )
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Detection failed: %s", exc)
        return detections


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detector = WildlifeDetector("detection/models/yolov8n.pt")
    logging.getLogger(__name__).info("Detector self-test: %s", "loaded" if detector.model else "fallback")
