# Generated manually to sync event_type choices with models.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_event_frame_event_image_crop_event_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('longitudinal_crack', 'Longitudinal Crack'),
                    ('transverse_crack', 'Transverse Crack'),
                    ('alligator_crack', 'Alligator Crack'),
                    ('pothole', 'Pothole'),
                    ('patch_repair_area', 'Patch/Repair Area'),
                    ('other_surface_damage', 'Other Surface Damage'),
                    ('manhole_road_utility_cover', 'Manhole/Road Utility Cover'),
                ],
                default='pending',
                max_length=50,
            ),
        ),
    ]
