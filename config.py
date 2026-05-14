"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _camera_source(value: str) -> int | str:
    if value is None:
        return 0
    return int(value) if value.isdigit() else value


# Camera
CAMERA_SOURCE = _camera_source(os.getenv("CAMERA_SOURCE", "0"))
CAMERA_ZONE = os.getenv("CAMERA_ZONE", "Zone-A-North")
FRAME_WIDTH = _as_int(os.getenv("FRAME_WIDTH"), 1280)
FRAME_HEIGHT = _as_int(os.getenv("FRAME_HEIGHT"), 720)

# Models
YOLO_MODEL_PATH = BASE_DIR / os.getenv("YOLO_MODEL_PATH", "detection/models/yolov8n.pt")
CLASSIFIER_MODEL_PATH = BASE_DIR / os.getenv("CLASSIFIER_MODEL_PATH", "detection/models/species_classifier.pt")
NIGHT_MODEL_PATH = os.getenv("NIGHT_MODEL_PATH", "")
NIGHT_MODEL_PATH = BASE_DIR / NIGHT_MODEL_PATH if NIGHT_MODEL_PATH else None
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))

# Alerts
NIGHT_START_HOUR = _as_int(os.getenv("NIGHT_START_HOUR"), 18)
NIGHT_END_HOUR = _as_int(os.getenv("NIGHT_END_HOUR"), 6)

# Voice
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")
USE_ONLINE_TTS = _as_bool(os.getenv("USE_ONLINE_TTS"), False)
VOICE_COOLDOWN_SECONDS = _as_int(os.getenv("VOICE_COOLDOWN_SECONDS"), 30)

# SMS
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "twilio")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
OFFICER_PHONE_LIST = [n.strip() for n in os.getenv("OFFICER_PHONE_LIST", "").split(",") if n.strip()]
SMS_COOLDOWN_MINUTES = _as_int(os.getenv("SMS_COOLDOWN_MINUTES"), 10)

# LED
LED_MODE = os.getenv("LED_MODE", "mock")
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUD = _as_int(os.getenv("SERIAL_BAUD"), 9600)

# Dashboard
FLASK_PORT = _as_int(os.getenv("FLASK_PORT"), 5000)
FLASK_DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), False)

# Database
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "logger/vanraksha.db")

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).info("Config self-test: %s %.2f", CAMERA_ZONE, CONFIDENCE_THRESHOLD)
