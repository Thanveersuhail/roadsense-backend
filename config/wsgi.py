import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
# Pre-warm YOLO model on startup
try:
    from events.utils import get_model
    get_model()
    print("[RoadSense] YOLO model pre-warmed ✅")
except Exception as e:
    print(f"[RoadSense] Model pre-warm failed: {e}")
