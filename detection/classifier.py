"""Species classifier based on EfficientNet-B4."""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

try:
    import torch
    from PIL import Image
    from torchvision import models, transforms
except ImportError:  # pragma: no cover
    torch = None
    Image = None
    models = None
    transforms = None


class SpeciesClassifier:
    """Classify cropped detections into species labels."""

    def __init__(self, model_path: str, class_names: list[str], device: str = "cpu"):
        self.logger = logging.getLogger(__name__)
        self.model_path = Path(model_path)
        self.class_names = class_names
        self.device = device
        self.model = None
        self.transform = None
        self.available = False

        if torch is None or models is None or transforms is None or Image is None:
            self.logger.warning("torch/torchvision not available; classifier fallback enabled")
            return
        if not self.model_path.exists():
            self.logger.warning("Classifier model not found; YOLO label fallback enabled")
            return
        try:
            self.model = models.efficientnet_b4(weights=None)
            in_features = self.model.classifier[1].in_features
            self.model.classifier[1] = torch.nn.Linear(in_features, len(class_names))
            state_dict = torch.load(self.model_path, map_location=device)
            self.model.load_state_dict(state_dict)
            self.model.to(device)
            self.model.eval()
            self.transform = transforms.Compose(
                [
                    transforms.Resize((380, 380)),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )
            self.available = True
        except Exception as exc:  # pragma: no cover
            self.logger.exception("Failed to initialize classifier: %s", exc)

    def classify(self, frame: np.ndarray, bbox: list, yolo_label: str = "unknown") -> dict:
        """Classify bbox crop and return top-1 and top-3 predictions."""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return {"species": yolo_label or "unknown", "confidence": 0.0, "top3": []}

        if not self.available:
            return {
                "species": yolo_label or "unknown",
                "confidence": 0.0,
                "top3": [{"species": yolo_label or "unknown", "confidence": 0.0}],
            }

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        tensor = self.transform(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            top_probs, top_idx = torch.topk(probs, k=min(3, len(self.class_names)))

        top3 = [
            {"species": self.class_names[idx], "confidence": float(prob)}
            for prob, idx in zip(top_probs.tolist(), top_idx.tolist())
        ]
        top1 = top3[0] if top3 else {"species": yolo_label or "unknown", "confidence": 0.0}
        return {"species": top1["species"], "confidence": top1["confidence"], "top3": top3}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    classifier = SpeciesClassifier("detection/models/species_classifier.pt", ["tiger", "elephant"])
    logging.getLogger(__name__).info("Classifier self-test: %s", "enabled" if classifier.available else "fallback")
