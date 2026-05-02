from rest_framework import serializers
from .models import Device, Event

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'description', 'created_at']

class EventSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(write_only=True, required=False)
    device = DeviceSerializer(read_only=True)

    class Meta:
        model = Event
        fields = [
    'id', 'device', 'device_name', 'event_type', 'severity',
    'confidence', 'latitude', 'longitude', 'speed_kmph',
    'detected_at', 'image_crop_path', 'full_frame_path',
    'status',        # ✅ ADD THIS
    'created_at'
]
        read_only_fields = ['created_at', 'device']

    def create(self, validated_data):
        device_name = validated_data.pop('device_name', 'unknown-device')
        device, created = Device.objects.get_or_create(name=device_name)
        event = Event.objects.create(device=device, **validated_data)
        return event
