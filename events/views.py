import os
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils.dateparse import parse_datetime
from PIL import Image
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics
from ultralytics import YOLO

from .models import Device, Event
from .serializers import EventSerializer
from django.http import JsonResponse


@api_view(["GET"])
def health_check(request):
    return JsonResponse({"status": "healthy"})

MODEL_PATH = os.path.join(settings.BASE_DIR, "best.pt")
model = None


def get_model():
    global model
    if model is None:
        model = YOLO(MODEL_PATH)
    return model


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


@api_view(["POST"])
def detect_event(request):
    try:
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        device_name = request.data.get("device_name", "unknown-device")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        speed_kmph = request.data.get("speed_kmph")
        detected_at_raw = request.data.get("detected_at")

        detected_at = parse_datetime(detected_at_raw) if detected_at_raw else datetime.utcnow()
        if detected_at is None:
            detected_at = datetime.utcnow()

        frames_dir = os.path.join(settings.MEDIA_ROOT, "frames")
        crops_dir = os.path.join(settings.MEDIA_ROOT, "crops")
        ensure_dir(frames_dir)
        ensure_dir(crops_dir)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        frame_filename = f"frame_{timestamp}.jpg"
        frame_relative_path = f"frames/{frame_filename}"
        frame_full_path = os.path.join(settings.MEDIA_ROOT, frame_relative_path)

        with default_storage.open(frame_full_path, "wb+") as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)

        results = get_model()(frame_full_path, conf=0.25)
        result = results[0]

        if len(result.boxes) == 0:
            return Response({
                "status": "no_detection",
                "message": "No anomaly detected",
                "full_frame_path": f"{settings.MEDIA_URL}{frame_relative_path}"
            }, status=status.HTTP_200_OK)

        best_box = max(result.boxes, key=lambda b: float(b.conf[0]))
        conf = float(best_box.conf[0])
        cls_id = int(best_box.cls[0])
        class_name = model.names.get(cls_id, "unknown")

        xyxy = best_box.xyxy[0].tolist()
        x1, y1, x2, y2 = map(int, xyxy)

        image = Image.open(frame_full_path).convert("RGB")
        crop = image.crop((x1, y1, x2, y2))

        crop_filename = f"crop_{timestamp}.jpg"
        crop_relative_path = f"crops/{crop_filename}"
        crop_full_path = os.path.join(settings.MEDIA_ROOT, crop_relative_path)
        crop.save(crop_full_path, format="JPEG")

        img_w, img_h = image.size
        box_area = max((x2 - x1), 1) * max((y2 - y1), 1)
        img_area = max(img_w * img_h, 1)
        severity = min(box_area / img_area, 1.0)

        device, created = Device.objects.get_or_create(name=device_name)
        event = Event.objects.create(
            device=device,
            event_type=class_name if class_name in dict(Event.EVENT_TYPES) else "pothole",
            severity=severity,
            confidence=conf,
            latitude=float(latitude) if latitude not in [None, ""] else None,
            longitude=float(longitude) if longitude not in [None, ""] else None,
            speed_kmph=float(speed_kmph) if speed_kmph not in [None, ""] else None,
            detected_at=detected_at,
            image_crop_path=f"{settings.MEDIA_URL}{crop_relative_path}",
            full_frame_path=f"{settings.MEDIA_URL}{frame_relative_path}",
        )

        return Response({
            "status": "detected",
            "event": EventSerializer(event).data,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
