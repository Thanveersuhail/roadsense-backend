from ultralytics import YOLO
from utils.supabase_storage import upload_image  # re-export for views.py

_model = None

def get_model():
    global _model
    if _model is None:
        import os
        model_path = os.environ.get("YOLO_MODEL_PATH", "best.pt")
        _model = YOLO(model_path)
    return _model
