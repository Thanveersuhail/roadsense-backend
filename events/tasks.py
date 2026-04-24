import os
from celery import shared_task
from ultralytics import YOLO
from .models import Event

_model = None

def get_model():
    global _model
    if _model is None:
        model_path = os.environ.get("YOLO_MODEL_PATH", "best.pt")
        _model = YOLO(model_path)
    return _model

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def run_detection(self, event_id):
    event = Event.objects.get(id=event_id)

    if not event.frame:
        event.status = "failed"
        event.save(update_fields=["status"])
        return

    frame_path = event.frame.path
    results = get_model()(frame_path, conf=0.25)

    label = "road_anomaly"
    confidence = 0.0

    if results and len(results) > 0 and results[0].boxes is not None and len(results[0].boxes) > 0:
        box = results[0].boxes[0]
        cls_id = int(box.cls[0].item())
        confidence = float(box.conf[0].item())
        label = results[0].names.get(cls_id, "road_anomaly")

    valid_types = dict(Event.EVENT_TYPES).keys()
    event.event_type = label if label in valid_types else "pothole"
    event.confidence = confidence
    event.status = "done"
    event.save(update_fields=["event_type", "confidence", "status"])
