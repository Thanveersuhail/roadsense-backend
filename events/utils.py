from ultralytics import YOLO
import os
import requests
import tempfile

_model = None
MODEL_PATH = os.path.join(tempfile.gettempdir(), "best.pt")


def download_model():
    """Download model if not already present."""
    if not os.path.exists(MODEL_PATH):
        model_url = os.environ.get("YOLO_MODEL_URL")
        if not model_url:
            raise ValueError("YOLO_MODEL_URL env var not set and model not found")
        print(f"[RoadSense] Downloading model from {model_url}...")
        r = requests.get(model_url, stream=True, timeout=120)
        r.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[RoadSense] Model downloaded to {MODEL_PATH}")
    else:
        print(f"[RoadSense] Model already cached at {MODEL_PATH}")


def get_model():
    global _model
    if _model is not None:
        return _model

    if not os.path.exists(MODEL_PATH):
        download_model()

    _model = YOLO(MODEL_PATH)
    print(f"[RoadSense] Model loaded into memory from {MODEL_PATH}")
    return _model
