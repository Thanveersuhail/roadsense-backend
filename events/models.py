from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

class Device(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Event(models.Model):
    EVENT_TYPES = [
        ('longitudinal_crack', 'Longitudinal Crack'),
        ('transverse_crack', 'Transverse Crack'),
        ('alligator_crack', 'Alligator Crack'),
        ('pothole', 'Pothole'),
        ('patch_repair_area', 'Patch/Repair Area'),
        ('other_surface_damage', 'Other Surface Damage'),
        ('manhole_road_utility_cover', 'Manhole/Road Utility Cover'),
        ('pending', 'Pending'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='pending')
    severity = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    speed_kmph = models.FloatField(null=True, blank=True)
    detected_at = models.DateTimeField(null=True, blank=True)

    frame = models.ImageField(upload_to='frames/', null=True, blank=True)
    image_crop = models.ImageField(upload_to='crops/', null=True, blank=True)

    image_crop_path = models.CharField(max_length=500, blank=True, default='')
    full_frame_path = models.CharField(max_length=500, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.status} - {self.created_at}"
