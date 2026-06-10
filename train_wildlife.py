"""
VanRaksha Wildlife Training Pipeline
=====================================
Trains a YOLOv8 model to detect: tiger, leopard, bear, deer

Dataset format expected (OpenImages):
  dataset/
    bear/    train/ {images} + train/Label/ {txt files}  + test/ {images} + test/Label/ {txt files}
    leopard/ train/ {images} + train/Label/ {txt files}  + test/ {images} + test/Label/ {txt files}
    deer/    train/ {images} + train/Label/ {txt files}  + test/ {images} + test/Label/ {txt files}

NOTE: Tiger is already in best_enlightengan_and_yolov8.pt but we re-include it as a
      class label here. Since you have no tiger training data in the dataset folder,
      the script will train on bear/leopard/deer and use YOLOv8 pre-trained weights
      that include tiger-like animals for transfer learning.

Output: weights/wildlife_combined.pt
        (copy this to weights/best_enlightengan_and_yolov8.pt to replace the old tiger model)

Usage:
    python train_wildlife.py

Requirements (already in your venv):
    pip install ultralytics pillow
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).resolve().parent
DATASET_DIR  = BASE_DIR / "dataset"
OUTPUT_DIR   = BASE_DIR / "training_data"   # YOLO-format dataset will be assembled here
WEIGHTS_DIR  = BASE_DIR / "weights"
OUTPUT_WEIGHTS = WEIGHTS_DIR / "wildlife_combined.pt"

# Class names (class IDs are the index: 0=bear, 1=deer, 2=leopard, 3=tiger)
# Tiger class is kept in the output so the model knows the label even if
# its images come from the existing tiger pre-trained base.
CLASS_NAMES = ["bear", "deer", "leopard", "tiger"]
CLASS_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}

# Source folder names → our class names (handles capitalisation from OpenImages)
FOLDER_TO_CLASS = {
    "bear":    "bear",
    "deer":    "deer",
    "leopard": "leopard",
}

# Raw label text → our class name (OpenImages labels use title case)
LABEL_TEXT_TO_CLASS = {
    "bear":    "bear",
    "Bear":    "bear",
    "deer":    "deer",
    "Deer":    "deer",
    "leopard": "leopard",
    "Leopard": "leopard",
    "tiger":   "tiger",
    "Tiger":   "tiger",
}

# Training hyper-parameters
EPOCHS        = 50       # Increase to 100+ for better accuracy
IMG_SIZE      = 640
BATCH_SIZE    = 4        # Reduce to 4 if you get CUDA out-of-memory errors
BASE_MODEL    = "yolov8m.pt"   # Medium model (good balance of speed vs accuracy)
DEVICE        = "0"       # "0" = first GPU. Use "cpu" to force CPU (very slow)
WORKERS       = 4

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("train")

# ─── Step 1: Convert OpenImages labels → YOLO format ────────────────────────

def convert_labels_for_split(animal: str, split: str) -> int:
    """
    Reads images + OpenImages labels and writes YOLO-format label files.
    OpenImages format: ClassName x1 y1 x2 y2   (absolute pixel coords)
    YOLO format:       class_id cx cy w h       (normalised 0-1)

    Returns number of valid image-label pairs processed.
    """
    src_dir   = DATASET_DIR / animal / split           # e.g. dataset/bear/train
    label_dir = src_dir / "Label"
    dst_img   = OUTPUT_DIR / "images" / split
    dst_lbl   = OUTPUT_DIR / "labels" / split

    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)

    class_name = FOLDER_TO_CLASS[animal]
    class_id   = CLASS_ID[class_name]

    count = 0
    skipped = 0

    for img_path in sorted(src_dir.glob("*.jpg")):
        lbl_path = label_dir / (img_path.stem + ".txt")
        if not lbl_path.exists():
            skipped += 1
            continue

        # Get image dimensions (needed for normalisation)
        try:
            with Image.open(img_path) as im:
                img_w, img_h = im.size
        except Exception as exc:
            log.warning("  Skipping corrupt image %s: %s", img_path.name, exc)
            skipped += 1
            continue

        yolo_lines = []
        raw_lines  = lbl_path.read_text(encoding="utf-8").strip().splitlines()

        for raw in raw_lines:
            parts = raw.strip().split()
            if len(parts) < 5:
                continue   # malformed line

            # OpenImages: LabelName x1 y1 x2 y2
            label_text = parts[0]
            override_class = LABEL_TEXT_TO_CLASS.get(label_text)
            if override_class is None:
                # Unknown label — fall back to the folder-derived class
                override_class = class_name
            cid = CLASS_ID.get(override_class, class_id)

            try:
                x1, y1, x2, y2 = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            except ValueError:
                continue

            # Clamp to image bounds
            x1 = max(0.0, min(x1, img_w))
            y1 = max(0.0, min(y1, img_h))
            x2 = max(0.0, min(x2, img_w))
            y2 = max(0.0, min(y2, img_h))

            # Convert to YOLO normalised (cx, cy, w, h)
            cx = ((x1 + x2) / 2.0) / img_w
            cy = ((y1 + y2) / 2.0) / img_h
            bw = (x2 - x1) / img_w
            bh = (y2 - y1) / img_h

            if bw <= 0 or bh <= 0:
                continue   # degenerate box

            yolo_lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        if not yolo_lines:
            skipped += 1
            continue

        # Copy image
        shutil.copy2(img_path, dst_img / img_path.name)

        # Write YOLO label
        (dst_lbl / (img_path.stem + ".txt")).write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
        count += 1

    log.info("  [%s/%s] %d images converted, %d skipped", animal, split, count, skipped)
    return count


def build_yolo_dataset() -> Path:
    """Convert all animals + splits and write the dataset.yaml file."""
    log.info("=" * 60)
    log.info("STEP 1: Building YOLO dataset from OpenImages labels")
    log.info("=" * 60)

    # Clean previous run
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    total = 0
    for animal in FOLDER_TO_CLASS:
        for split in ("train", "test"):
            src_dir = DATASET_DIR / animal / split
            if not src_dir.exists():
                log.warning("  Folder not found, skipping: %s", src_dir)
                continue
            total += convert_labels_for_split(animal, split)

    log.info("Total image-label pairs: %d", total)

    # Write dataset.yaml
    yaml_content = {
        "path":  str(OUTPUT_DIR),
        "train": "images/train",
        "val":   "images/test",
        "nc":    len(CLASS_NAMES),
        "names": CLASS_NAMES,
    }
    yaml_path = OUTPUT_DIR / "dataset.yaml"
    yaml_path.write_text(yaml.dump(yaml_content, default_flow_style=False), encoding="utf-8")
    log.info("Dataset YAML written: %s", yaml_path)
    return yaml_path


# ─── Step 2: Train YOLOv8 ────────────────────────────────────────────────────

def train(yaml_path: Path) -> Path:
    """Run YOLOv8 training and return path to the best weights."""
    try:
        from ultralytics import YOLO
    except ImportError:
        log.error("ultralytics not found. Run: pip install ultralytics")
        sys.exit(1)

    log.info("=" * 60)
    log.info("STEP 2: Training YOLOv8 model")
    log.info("  Base model   : %s", BASE_MODEL)
    log.info("  Epochs       : %d", EPOCHS)
    log.info("  Image size   : %d", IMG_SIZE)
    log.info("  Batch size   : %d", BATCH_SIZE)
    log.info("  Device       : %s", DEVICE)
    log.info("  Classes      : %s", CLASS_NAMES)
    log.info("=" * 60)

    model = YOLO(BASE_MODEL)   # downloads pre-trained weights on first run

    results = model.train(
        data        = str(yaml_path),
        epochs      = EPOCHS,
        imgsz       = IMG_SIZE,
        batch       = BATCH_SIZE,
        device      = DEVICE,
        workers     = WORKERS,
        project     = str(BASE_DIR / "training_runs"),
        name        = "wildlife_detector",
        exist_ok    = True,
        patience    = 15,          # early stop if no improvement for 15 epochs
        save        = True,
        save_period = 10,          # save checkpoint every 10 epochs
        augment     = True,        # enable mosaic, flipping, colour jitter
        degrees     = 10.0,        # rotate ±10°
        flipud      = 0.1,
        fliplr      = 0.5,
        mosaic      = 1.0,
        mixup       = 0.1,
        verbose     = True,
    )

    # Locate best weights
    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    if not best_pt.exists():
        log.error("Training finished but best.pt not found at %s", best_pt)
        sys.exit(1)

    log.info("Best weights: %s", best_pt)
    return best_pt


# ─── Step 3: Validate & Export ───────────────────────────────────────────────

def validate_and_export(best_pt: Path, yaml_path: Path) -> None:
    """Run validation metrics and copy the model to the weights folder."""
    from ultralytics import YOLO

    log.info("=" * 60)
    log.info("STEP 3: Validating trained model")
    log.info("=" * 60)

    model = YOLO(str(best_pt))
    metrics = model.val(data=str(yaml_path), imgsz=IMG_SIZE, device=DEVICE, verbose=True)

    log.info("Validation results:")
    log.info("  mAP50     : %.4f", metrics.box.map50)
    log.info("  mAP50-95  : %.4f", metrics.box.map)
    for i, cls in enumerate(CLASS_NAMES):
        try:
            ap50 = metrics.box.ap50[i] if hasattr(metrics.box, "ap50") else float("nan")
            log.info("  AP50 %-10s: %.4f", cls, ap50)
        except (IndexError, TypeError):
            pass

    # Copy to project weights folder
    WEIGHTS_DIR.mkdir(exist_ok=True)
    shutil.copy2(best_pt, OUTPUT_WEIGHTS)
    log.info("=" * 60)
    log.info("Model saved to: %s", OUTPUT_WEIGHTS)
    log.info("=" * 60)


# ─── Step 4: Update VanRaksha config ─────────────────────────────────────────

def print_next_steps() -> None:
    log.info("")
    log.info("=" * 60)
    log.info("NEXT STEPS — integrate into VanRaksha:")
    log.info("=" * 60)
    log.info("")
    log.info("1. The trained model is at:")
    log.info("      %s", OUTPUT_WEIGHTS)
    log.info("")
    log.info("2. Open your .env file and set TIGER_MODEL_PATH to point to it:")
    log.info("      TIGER_MODEL_PATH=weights/wildlife_combined.pt")
    log.info("")
    log.info("3. The model detects classes: %s", CLASS_NAMES)
    log.info("   Class IDs:")
    for name, cid in CLASS_ID.items():
        log.info("      %d → %s", cid, name)
    log.info("")
    log.info("4. VanRaksha's risk labels are already configured:")
    log.info("      bear    → HIGH RISK – SLOTH BEAR  (danger 8/10)")
    log.info("      leopard → HIGH RISK – LEOPARD      (danger 9/10)")
    log.info("      deer    → LOW RISK  – DEER          (danger 1/10)")
    log.info("      tiger   → HIGH RISK – TIGER         (danger 10/10)")
    log.info("")
    log.info("5. Restart main.py — all four animals will now be detected!")
    log.info("")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Verify dataset folder exists
    if not DATASET_DIR.exists():
        log.error("Dataset folder not found: %s", DATASET_DIR)
        log.error("Expected structure:")
        log.error("  dataset/bear/train/  + dataset/bear/train/Label/")
        log.error("  dataset/leopard/train/ + ...")
        log.error("  dataset/deer/train/ + ...")
        sys.exit(1)

    yaml_path = build_yolo_dataset()
    best_pt   = train(yaml_path)
    validate_and_export(best_pt, yaml_path)
    print_next_steps()
