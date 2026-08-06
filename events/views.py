import logging
import os
import tempfile
import traceback
import uuid

import cv2
import numpy as np

from django.http import JsonResponse
from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_datetime

from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Device, Event
from .serializers import EventSerializer
from .utils import get_model
from utils.supabase_storage import upload_image


logger = logging.getLogger(__name__)


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
    stage = "start"
    request_id = uuid.uuid4().hex[:8]

    try:
        stage = "reading_uploaded_image"

        image_file = request.FILES.get("image")

        if not image_file:
            return Response(
                {
                    "error": "No image uploaded",
                    "stage": stage,
                    "request_id": request_id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_name = request.data.get(
            "device_name",
            "unknown-device",
        )

        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        speed_kmph = request.data.get("speed_kmph")
        detected_at_raw = request.data.get("detected_at")

        stage = "parsing_timestamp"

        detected_at = (
            parse_datetime(detected_at_raw)
            if detected_at_raw
            else None
        )

        if detected_at is None:
            detected_at = django_timezone.now()
        elif django_timezone.is_naive(detected_at):
            detected_at = django_timezone.make_aware(
                detected_at,
                django_timezone.get_current_timezone(),
            )

        stage = "creating_or_getting_device"

        device, _ = Device.objects.get_or_create(
            name=device_name
        )

        stage = "reading_image_bytes"

        image_bytes = image_file.read()

        if not image_bytes:
            raise ValueError("Uploaded image is empty")

        timestamp = django_timezone.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        unique_id = uuid.uuid4().hex[:8]

        stage = "uploading_original_image"

        original_supabase_path = (
            f"frames/{timestamp}_{unique_id}.jpg"
        )

        public_url = upload_image(
            image_bytes,
            original_supabase_path,
        )

        stage = "creating_pending_database_event"

        event = Event.objects.create(
            device=device,
            status="pending",
            latitude=(
                float(latitude)
                if latitude not in [None, ""]
                else None
            ),
            longitude=(
                float(longitude)
                if longitude not in [None, ""]
                else None
            ),
            speed_kmph=(
                float(speed_kmph)
                if speed_kmph not in [None, ""]
                else None
            ),
            detected_at=detected_at,
            full_frame_path=public_url,
        )

        stage = "creating_temporary_image_file"

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".jpg",
                delete=False,
            ) as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name

            stage = "loading_yolo_model"

            model = get_model()

            stage = "running_yolo_inference"

            results = model(
                temp_path,
                conf=0.15,
            )

        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        crop_url = None

        has_detection = (
            results
            and len(results) > 0
            and results[0].boxes is not None
            and len(results[0].boxes) > 0
        )

        if has_detection:
            stage = "reading_detection_result"

            box = results[0].boxes[0]

            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            raw_label = results[0].names.get(
                cls_id,
                "other",
            )

            event.event_type = CANONICAL_EVENT_TYPE_MAP.get(
                raw_label,
                "other_surface_damage",
            )
            event.confidence = confidence
            event.severity = confidence

            stage = "decoding_image_for_annotation"

            nparr = np.frombuffer(
                image_bytes,
                np.uint8,
            )
            image = cv2.imdecode(
                nparr,
                cv2.IMREAD_COLOR,
            )

            if image is not None:
                coordinates = box.xyxy[0].tolist()

                x1, y1, x2, y2 = [
                    int(value)
                    for value in coordinates
                ]

                label_text = (
                    f"{event.event_type} "
                    f"{event.confidence:.2f}"
                )

                stage = "drawing_detection_box"

                cv2.rectangle(
                    image,
                    (x1, y1),
                    (x2, y2),
                    (0, 0, 255),
                    3,
                )

                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2

                (text_width, text_height), _ = (
                    cv2.getTextSize(
                        label_text,
                        font,
                        font_scale,
                        thickness,
                    )
                )

                label_y1 = max(
                    0,
                    y1 - text_height - 10,
                )

                cv2.rectangle(
                    image,
                    (x1, label_y1),
                    (
                        x1 + text_width + 6,
                        y1,
                    ),
                    (0, 0, 255),
                    -1,
                )

                cv2.putText(
                    image,
                    label_text,
                    (x1 + 3, max(20, y1 - 5)),
                    font,
                    font_scale,
                    (255, 255, 255),
                    thickness,
                )

                stage = "encoding_annotated_image"

                success, buffer = cv2.imencode(
                    ".jpg",
                    image,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        90,
                    ],
                )

                if not success:
                    raise RuntimeError(
                        "Could not encode annotated image"
                    )

                annotated_bytes = buffer.tobytes()

                stage = "uploading_annotated_image"

                annotated_supabase_path = (
                    "frames/annotated/"
                    f"{timestamp}_{unique_id}_bbox.jpg"
                )

                crop_url = upload_image(
                    annotated_bytes,
                    annotated_supabase_path,
                )

        else:
            stage = "setting_no_detection_values"

            event.event_type = "other_surface_damage"
            event.confidence = 0.0
            event.severity = 0.0

        stage = "saving_completed_event"

        event.status = "done"

        if crop_url:
            event.image_crop_path = crop_url

        event.save(
            update_fields=[
                "event_type",
                "severity",
                "confidence",
                "status",
                "image_crop_path",
            ]
        )

        logger.info(
            "[RoadSense] Detection completed "
            "request_id=%s event_id=%s",
            request_id,
            event.id,
        )

        return Response(
            {
                "status": "done",
                "request_id": request_id,
                "event": EventSerializer(event).data,
                "message": (
                    "Detection completed and image uploaded "
                    "to Supabase"
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as error:
        logger.error(
            "[RoadSense] Detection failed "
            "request_id=%s stage=%s error=%s",
            request_id,
            stage,
            error,
        )
        traceback.print_exc()

        if event is not None:
            try:
                event.status = "failed"
                event.save(update_fields=["status"])
            except Exception:
                traceback.print_exc()

        return Response(
            {
                "error": str(error),
                "stage": stage,
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventDetailView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
