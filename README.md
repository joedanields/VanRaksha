# VanRaksha AI

Protecting lives on both sides of the forest through real-time wildlife detection and alerting.

## Project Overview

VanRaksha AI is a Python-based wildlife threat monitoring system that:

- Captures a live camera feed
- Detects animals using YOLOv8
- Classifies species (with fallback behavior when classifier weights are unavailable)
- Computes a threat score and maps it to alert levels
- Triggers voice/SMS/LED alerts for dangerous events
- Stores events in SQLite
- Serves a live Flask + Socket.IO dashboard

Core runtime entry point: `main.py`

## Key Features

- **Real-time detection** with configurable confidence threshold
- **Day/Night model switching** via configurable time window
- **Threat scoring pipeline** based on species danger, proximity, time, count, and confidence
- **Alert channels**
  - Voice alerts (offline `pyttsx3` or online `gTTS`)
  - SMS alerts (Twilio/GSM/mock with cooldown)
  - LED controller (GPIO/serial/mock)
- **Dashboard**
  - Live MJPEG stream
  - Recent events
  - Aggregate statistics
  - Runtime config controls (mute/confidence)

## Repository Structure

```text
VanRaksha/
├── main.py                  # Application orchestration loop
├── config.py                # Environment-based configuration
├── detection/               # YOLO detector + species classifier + night switch
├── threat/                  # Threat score and alert-level logic
├── output/                  # Voice, SMS, and LED outputs
├── logger/                  # SQLite event logging and stats
├── dashboard/               # Flask + Socket.IO dashboard and frontend assets
├── tests/                   # Unit tests
└── requirements.txt         # Python dependencies
```

## Setup

### 1) Prerequisites

- Python 3.10+ recommended
- Camera source (USB camera or stream)
- (Optional) GPU/CUDA for faster inference
- (Optional) Twilio account or GSM modem for SMS alerts

### 2) Clone and enter the repository

```bash
git clone https://github.com/joedanields/VanRaksha.git
cd VanRaksha
```

### 3) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows (PowerShell)
```

### 4) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5) Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` for your setup:

- `CAMERA_SOURCE` (default `0`)
- `CAMERA_ZONE`
- `YOLO_MODEL_PATH`
- `CLASSIFIER_MODEL_PATH`
- `NIGHT_MODEL_PATH` (optional)
- `TWILIO_*` and `OFFICER_PHONE_LIST` (if using Twilio SMS)
- `LED_MODE` (`mock`, `gpio`, or `serial`)
- `FLASK_PORT`

## Model Files

By default, configuration expects:

- `detection/models/yolov8n.pt`
- `detection/models/species_classifier.pt`

If model files are missing:

- Detection/classification components degrade gracefully (with logged warnings and fallback behavior).

## Run the Project

Start the full pipeline:

```bash
python main.py
```

Dashboard will be available at:

- `http://localhost:5000` (or your configured `FLASK_PORT`)

## Testing and Validation

Run syntax check:

```bash
python -m compileall .
```

Run unit tests:

```bash
python -m unittest discover -s tests -v
```

## Configuration Notes

- All configuration is loaded from `.env` through `config.py`.
- `SMS_PROVIDER` supports `twilio` (default), `gsm`, or mock behavior.
- Alert mute and confidence threshold can be updated at runtime via dashboard API.

## Wild-Animal Filtering and Human Proximity Alerts

To focus detection on wild animals while still detecting humans for critical alerts:

- `WILD_ANIMAL_LABELS` — comma-separated labels to keep (lowercase). Example:
  `tiger,elephant,leopard,deer,wild_boar`
- `HUMAN_LABELS` — labels treated as humans. Default: `person,human`
- `HUMAN_ANIMAL_DISTANCE_RATIO` — distance threshold as a ratio of frame width. Example: `0.15`

If any human detection is within the configured distance of a wild-animal detection in the same frame,
the alert level is forced to `CRITICAL`.

## Fine-Tuning YOLOv8 (Wild Animals + Human)

1) Collect and label images in YOLO format.

Recommended dataset layout:

```text
dataset/
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

2) Create a `data.yaml` with your class list (include a human class):

```yaml
path: /absolute/path/to/dataset
train: images/train
val: images/val
names:
  - tiger
  - elephant
  - leopard
  - deer
  - wild_boar
  - human
```

3) Train:

```bash
yolo detect train data=/path/to/data.yaml model=detection/models/yolov8n.pt epochs=100 imgsz=640
```

4) Update `.env`:

```bash
YOLO_MODEL_PATH=runs/detect/train/weights/best.pt
WILD_ANIMAL_LABELS=tiger,elephant,leopard,deer,wild_boar
HUMAN_LABELS=human,person
```

## License

This repository includes a `LICENSE` file. See `LICENSE` for details.
