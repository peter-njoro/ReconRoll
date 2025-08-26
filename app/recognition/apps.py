from django.apps import AppConfig
import threading


class RecognitionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recognition'


class RecognitionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recognition"

    _started = False  # class-level guard

    def ready(self):
        if not RecognitionConfig._started:
            RecognitionConfig._started = True
            from . import webcam_stream
            t = threading.Thread(target=webcam_stream.start_stream, daemon=True)
            t.start()
            print("✅ webcam_stream.py started only once...")
