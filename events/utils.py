from ultralytics import YOLO
import os, requests

_model = None
MODEL_PATH = "/tmp/best.pt"

def download_model():
    """Download model at startup if not already present."""
    if not os.path.exists(MODEL_PATH):
        model_url = os.environ.get("YOLO_MODEL_URL")
        if not model_url:
            raise ValueError("YOLO_MODEL_URL env var not set and model not found at /tmp/best.pt")
        print(f"[RoadSense] Downloading model from {model_url}...")
        r = requests.get(model_url, stream=True, timeout=120)
        r.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print("[RoadSense] Model downloaded ✅")
    else:
        print("[RoadSense] Model already cached at /tmp/best.pt ✅")

def get_model():
    global _model
    if _model is None:
        download_model()
        _model = YOLO(MODEL_PATH)
        print("[RoadSense] YOLO model loaded ✅")
    return _model
