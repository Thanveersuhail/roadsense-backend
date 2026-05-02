from django.apps import AppConfig
import os

class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'

    def ready(self):
        if os.environ.get("RUN_MAIN") == "true" or os.environ.get("RENDER"):
            from .utils import download_model
            try:
                download_model()
            except Exception as e:
                print(f"[RoadSense] Model preload failed: {e}")
