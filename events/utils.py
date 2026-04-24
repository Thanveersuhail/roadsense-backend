from ultralytics import YOLO
import os, requests

_model = None

def get_model():
    global _model
    if _model is None:
        model_path = os.environ.get("YOLO_MODEL_PATH", "best.pt")
        if not os.path.exists(model_path):
            model_url = os.environ.get("YOLO_MODEL_URL")
            if not model_url:
                raise ValueError("YOLO_MODEL_URL env var not set and best.pt not found")
            print(f"[RoadSense] Downloading model from {model_url}...")
            r = requests.get(model_url, stream=True)
            with open(model_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("[RoadSense] Model downloaded ✅")
        _model = YOLO(model_path)
    return _model
