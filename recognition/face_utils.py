import face_recognition
from django.core.files.base import ContentFile
import numpy as np
import io
from PIL import Image


def encode_face(image_path):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        return None # No faces

    return encodings[0]

