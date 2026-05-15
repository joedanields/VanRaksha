"""VanRaksha AI entrypoint."""
from __future__ import annotations

import logging
import math
import queue
import threading
import time
from datetime import datetime, timezone

import cv2

import config
from dashboard.app import DashboardServer
from detection.classifier import SpeciesClassifier
from detection.detector import WildlifeDetector
from detection.night_switch import NightSwitch
from logger.event_logger import EventLogger
from output.led_controller import LEDController
from output.sms_alert import SMSAlert
from output.voice import VoiceAlert
from threat.alert_level import AlertLevel, get_alert_level
from threat.scorer import ThreatScorer
from threat.species_index import SPECIES_CLASS_NAMES
from utils.drawing import annotate_detection


LABEL_ALIASES = {
    "boar": "wild_boar",
    "wildboar": "wild_boar",
    "person": "human",
    "people": "human",
}


def _normalize_label(label: str) -> str:
    value = (label or "").strip().lower()
    return LABEL_ALIASES.get(value, value)


def _bbox_center(bbox: list) -> tuple[float, float]:
    x1, y1, x2, y2 = [float(v) for v in bbox]
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def _human_near_animal(animal_bbox: list, human_detections: list[dict], threshold_px: float) -> bool:
    if not human_detections:
        return False
    ax, ay = _bbox_center(animal_bbox)
    for det in human_detections:
        hx, hy = _bbox_center(det["bbox"])
        if math.hypot(ax - hx, ay - hy) <= threshold_px:
            return True
    return False


def main():
    """Run camera ingestion, detection, alerts, and dashboard updates."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("main")

    frame_queue = queue.Queue(maxsize=5)
    shared_state = {"confidence_threshold": config.CONFIDENCE_THRESHOLD, "alert_mute": False}

    event_logger = EventLogger(str(config.DB_PATH))
    night_switch = NightSwitch(str(config.YOLO_MODEL_PATH), str(config.NIGHT_MODEL_PATH) if config.NIGHT_MODEL_PATH else None, config.NIGHT_START_HOUR, config.NIGHT_END_HOUR)
    detector = WildlifeDetector(str(config.YOLO_MODEL_PATH), config.CONFIDENCE_THRESHOLD)
    active_model_path = str(config.YOLO_MODEL_PATH)
    classifier = SpeciesClassifier(str(config.CLASSIFIER_MODEL_PATH), SPECIES_CLASS_NAMES)
    scorer = ThreatScorer()
    voice = VoiceAlert(language=config.TTS_LANGUAGE, use_online=config.USE_ONLINE_TTS, cooldown_seconds=config.VOICE_COOLDOWN_SECONDS)
    led = LEDController(mode=config.LED_MODE)
    sms = SMSAlert(provider=config.SMS_PROVIDER)

    dashboard = DashboardServer(event_logger, frame_queue, shared_state)
    threading.Thread(target=dashboard.run, daemon=True).start()

    cap = cv2.VideoCapture(config.CAMERA_SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        log.warning("Camera unavailable; dashboard will show No feed")

    wild_labels = {_normalize_label(label) for label in config.WILD_ANIMAL_LABELS if label}
    human_labels = {_normalize_label(label) for label in config.HUMAN_LABELS if label}
    allowed_labels = wild_labels | human_labels

    fps_counter = 0
    tick = time.time()
    try:
        while True:
            if not cap.isOpened():
                time.sleep(0.5)
                dashboard.emit_frame_stats({"fps": 0, "detections": 0})
                continue

            ok, frame = cap.read()
            if not ok:
                continue

            detector.confidence_threshold = float(shared_state.get("confidence_threshold", config.CONFIDENCE_THRESHOLD))
            next_model_path = night_switch.get_active_model_path()
            if next_model_path != active_model_path:
                active_model_path = next_model_path
                detector = WildlifeDetector(str(active_model_path), float(shared_state["confidence_threshold"]))
            detections = detector.detect(frame)

            filtered_detections = []
            if allowed_labels:
                for det in detections:
                    label_norm = _normalize_label(det.get("label", "unknown"))
                    if label_norm not in allowed_labels:
                        continue
                    det["label_norm"] = label_norm
                    filtered_detections.append(det)
            else:
                for det in detections:
                    det["label_norm"] = _normalize_label(det.get("label", "unknown"))
                filtered_detections = detections

            human_detections = [det for det in filtered_detections if det["label_norm"] in human_labels]
            if wild_labels:
                animal_detections = [det for det in filtered_detections if det["label_norm"] in wild_labels]
            else:
                animal_detections = [det for det in filtered_detections if det["label_norm"] not in human_labels]
            distance_threshold_px = max(1.0, config.HUMAN_ANIMAL_DISTANCE_RATIO * frame.shape[1])

            for det in animal_detections:
                bbox = det["bbox"]
                yolo_label = det.get("label_norm", det.get("label", "unknown"))
                cls = classifier.classify(frame, bbox, yolo_label=yolo_label)
                species = _normalize_label(cls["species"])
                score = scorer.score(species, bbox, frame.shape, len(animal_detections), det["confidence"])
                level = get_alert_level(score)
                if _human_near_animal(bbox, human_detections, distance_threshold_px):
                    level = AlertLevel.CRITICAL
                    score = max(score, 90.0)

                annotate_detection(frame, bbox, species, det["confidence"], score, level)

                voice_played = False
                if level in (AlertLevel.CAUTION, AlertLevel.HIGH, AlertLevel.CRITICAL) and not shared_state.get("alert_mute", False):
                    voice_played = voice.speak(species, level, "nearby", camera_zone=config.CAMERA_ZONE)

                sms_sent = False
                if level in (AlertLevel.HIGH, AlertLevel.CRITICAL):
                    led.set_alert(level)
                    sms_sent = sms.send(species, level, config.CAMERA_ZONE, score)
                    dashboard.emit_new_alert(
                        {
                            "species": species,
                            "confidence": det["confidence"],
                            "score": score,
                            "alert_level": level.name,
                        }
                    )

                event_logger.log_event(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "camera_zone": config.CAMERA_ZONE,
                        "species": species,
                        "confidence": det["confidence"],
                        "threat_score": score,
                        "alert_level": level.name,
                        "bbox": bbox,
                        "sms_sent": sms_sent,
                        "voice_played": voice_played,
                    }
                )

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] {species.upper()} | conf:{det['confidence']:.2f} | "
                    f"score:{score:.1f} | {level.name} | SMS:{'sent' if sms_sent else 'skip'} | Voice:{'played' if voice_played else 'skip'}"
                )

            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except queue.Empty:
                    pass
            frame_queue.put_nowait(frame)

            fps_counter += 1
            now = time.time()
            if now - tick >= 1:
                dashboard.emit_frame_stats({"fps": fps_counter, "detections": len(animal_detections)})
                fps_counter = 0
                tick = now

    except KeyboardInterrupt:
        log.info("Shutting down VanRaksha AI")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
