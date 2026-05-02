import os
import uuid
import tempfile
import traceback
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics
from django.http import JsonResponse
from django.utils import timezone as django_timezone

from .models import Device, Event
from .serializers import EventSerializer
from .utils import get_model
from utils.supabase_storage import upload_image

CANONICAL_EVENT_TYPE_MAP = {
    "pothole": "pothole",
    "alligator": "alligator_crack",
    "alligator_crack": "alligator_crack",
    "crack": "longitudinal_crack",
    "longitudinal_crack": "longitudinal_crack",
    "transverse_crack": "transverse_crack",
    "rough_patch": "patch_repair",
    "patch_repair": "patch_repair",
    "patch_repair_area": "patch_repair",
    "other": "other_surface_damage",
    "other_surface_damage": "other_surface_damage",
    "unknown": "other_surface_damage",
    "no_detection": "other_surface_damage",
    "manhole": "other_surface_damage",
    "manhole_road_utility_cover": "other_surface_damage",
}

@api_view(["GET"])
def health_check(request):
    return JsonResponse({"status": "healthy"})


@api_view(["POST"])
def detect_event(request):
    event = None
    try:
        image_file = request.FILES.get("image")
        if not image_file:
            return Response(
                {"error": "No image uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        device_name = request.data.get("device_name", "unknown-device")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        speed_kmph = request.data.get("speed_kmph")
        detected_at_raw = request.data.get("detected_at")

        # ✅ FIX 1: Use timezone-aware datetime
        detected_at = parse_datetime(detected_at_raw) if detected_at_raw else None
        if detected_at is None:
            detected_at = django_timezone.now()

        device, _ = Device.objects.get_or_create(name=device_name)
        image_bytes = image_file.read()

        timestamp = django_timezone.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        supabase_path = f"frames/{timestamp}_{unique_id}.jpg"
        public_url = upload_image(image_bytes, supabase_path)

        event = Event.objects.create(
            device=device,
            status="pending",
            latitude=float(latitude) if latitude not in [None, ""] else None,
            longitude=float(longitude) if longitude not in [None, ""] else None,
            speed_kmph=float(speed_kmph) if speed_kmph not in [None, ""] else None,
            detected_at=detected_at,
            full_frame_path=public_url,
        )

        # ✅ FIX 2: Safe temp file cleanup even on YOLO crash
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name

            model = get_model()
            results = model(temp_path, conf=0.15)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        crop_url = None

        if results and len(results) > 0 and results[0].boxes:
            box = results[0].boxes[0]
            cls_id = int(box.cls[0].item())
            event.confidence = float(box.conf[0].item())
            event.severity = event.confidence
            raw_label = results[0].names.get(cls_id, 'other')
            event.event_type = CANONICAL_EVENT_TYPE_MAP.get(raw_label, 'other_surface_damage')

            # --- Draw bounding box and upload annotated image ---
            import cv2
            import numpy as np

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is not None:
                b = box.xyxy[0].tolist()
                x1, y1, x2, y2 = int(b[0]), int(b[1]), int(b[2]), int(b[3])
                label_text = f"{event.event_type} {event.confidence:.2f}"

                # Draw box
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)

                # Draw label background
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                (tw, th), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
                cv2.rectangle(img, (x1, y1 - th - 10), (x1 + tw + 6, y1), (0, 0, 255), -1)
                cv2.putText(img, label_text, (x1 + 3, y1 - 5), font, font_scale, (255, 255, 255), thickness)

                # Encode and upload
                _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                annotated_bytes = buffer.tobytes()
                crop_supabase_path = f"annotated/{timestamp}_{unique_id}_bbox.jpg"
                crop_url = upload_image(annotated_bytes, crop_supabase_path)

        else:
          event.event_type = "other_surface_damage"
          event.confidence = 0.0
          event.severity = 0.0

        event.status = "done"
        if crop_url:
            event.image_crop_path = crop_url
        event.save(update_fields=["event_type", "severity", "confidence", "status", "image_crop_path"])

        return Response(
            {
                "status": "done",
                "event": EventSerializer(event).data,
                "message": "Detection completed, image uploaded to Supabase",
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        print("DETECT_EVENT_ERROR:", repr(e))
        traceback.print_exc()
        if event is not None:
            event.status = "failed"
            event.save(update_fields=["status"])
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
