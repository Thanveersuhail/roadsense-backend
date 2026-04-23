from django.contrib import admin
from .models import Device, Event

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'created_at']
    search_fields = ['name']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'event_type', 'device', 'severity', 'confidence',
        'latitude', 'longitude', 'detected_at', 'created_at'
    ]
    list_filter = ['event_type', 'device', 'created_at']
    search_fields = ['event_type', 'device__name']
