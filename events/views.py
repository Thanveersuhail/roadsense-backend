import os
import uuid
import tempfile
from datetime import datetime
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics
from django.http import JsonResponse

from .models import Device, Event
from .serializers import EventSerializer
from .utils import get_model
from utils.supabase_storage import upload_image


@api_view(["GET"])
def health_check(request):
    return JsonResponse({"status": "healthy"})


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

        device, _ = Device.objects.get_or_create(name=device_name)
        image_bytes = image_file.read()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_file.write(image_bytes)
            temp_path = temp_file.name

        model = get_model()
        results = model(temp_path, conf=0.25)
        os.unlink(temp_path)

        if results and len(results) > 0 and results[0].boxes:
    box = results[0].boxes[0]
    cls_id = int(box.cls[0].item())
    event.confidence = float(box.conf[0].item())
    label = results[0].names.get(cls_id, "pothole")
    valid_types = dict(Event.EVENT_TYPES).keys()
    event.event_type = label if label in valid_types else "pothole"
else:
    event.event_type = "other_surface_damage"  # ✅ clean fallback
    event.confidence = 0.0

event.status = "done"
event.save(update_fields=["event_type", "confidence", "status"])

        return Response({
            "status": "done",
            "event": EventSerializer(event).data,
            "message": "Detection completed, image uploaded to Supabase"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
