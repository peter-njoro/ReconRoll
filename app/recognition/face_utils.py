import os
import cv2
import uuid
import numpy as np
import face_recognition
from recognition.models import Student, FaceEncoding
from django.conf import settings
from collections import defaultdict, deque


def load_known_encodings_from_db():
    known_encodings = []
    known_names = []

    for student in Student.objects.all():
        for encoding_obj in student.encodings.all():
            path = os.path.join(settings.BASE_DIR, encoding_obj.file_path)
            try:
                encoding = np.load(path)
                known_encodings.append(encoding)
                known_names.append(student.full_name)
            except Exception as e:
                print(f"Failed to load encoding for {student.full_name}: {e}")

    return np.array(known_encodings), known_names

def get_face_encodings(image, model='cnn', scale=0.25, min_size=100, dnn_net=None):
    small_frame = cv2.resize(image, (0, 0), fx=scale, fy=scale) if scale != 1.0 else image
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    if model == 'dnn' and dnn_net is not None:
        # DNN face detection
        (h, w) = rgb_small_frame.shape[:2]
        blob = cv2.dnn.blobFromImage(rgb_small_frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
        dnn_net.setInput(blob)
        detections = dnn_net.forward()
        face_locations = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (left, top, right, bottom) = box.astype("int")
                # Ensure box is within image bounds and meets min_size
                if (right - left) >= min_size and (bottom - top) >= min_size:
                    face_locations.append((top, right, bottom, left))
        if not face_locations:
            return [], []
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame, face_locations, num_jitters=1
        )
        return face_locations, face_encodings

    # Default to HOG/CNN
    face_locations = face_recognition.face_locations(
        rgb_small_frame,
        number_of_times_to_upsample=1,
        model=model
    )
    face_locations = [
        loc for loc in face_locations
        if (loc[2] - loc[0]) >= min_size and (loc[1] - loc[3]) >= min_size
    ]
    if not face_locations:
        return [], []
    face_encodings = face_recognition.face_encodings(
        rgb_small_frame,
        face_locations,
        num_jitters=1
    )

    return face_locations, face_encodings

def matches_face_encoding(encoding, known_encodings, known_names, tolerance=0.5):
    if not known_encodings.any():
        return "unknown", float("inf"), -1

    distances = np.linalg.norm(known_encodings - encoding, axis=1)
    best_match_index = np.argmin(distances)
    best_distance = distances[best_match_index]

    name = known_names[best_match_index] if best_distance <= tolerance else "unknown"
    return name, best_distance, best_match_index

def annotate_frame(frame, face_locations, face_names, face_encodings=None, scale=0.25):
    for i, ((top, right, bottom, left), name) in enumerate(zip(face_locations, face_names)):
        top, right, bottom, left = [int(coord / scale) for coord in (top, right, bottom, left)]
        color = (0, 255, 0) if name != "unknown" else (0, 0, 255)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)

        label = name
        if face_encodings is not None and i < len(face_encodings):
            preview = ', '.join(f"{x:.2f}" for x in face_encodings[i][:3])
            label += f" [{preview}...]"

        cv2.putText(frame, label, (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    return frame

def safe_load_dnn_model():
    config_path = os.path.join("models", "deploy.prototxt")
    model_path = os.path.join("models", "res10_300x300_ssd_iter_140000.caffemodel")
    net = cv2.dnn.readNetFromCaffe(config_path, model_path)

    try:
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        # Dry test to validate CUDA compatibility
        dummy = cv2.dnn.blobFromImage(np.zeros((300, 300, 3), dtype=np.uint8))
        net.setInput(dummy)
        _ = net.forward()
        print("🚀 CUDA is available and working")
    except:
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        print("⚠️ CUDA not available. Falling back to CPU")

    return net

def save_unidentified_face(frame, face_location):
    """
    Crop face from frame & save to file; return relative path to save in DB
    """
    top, right, bottom, left = face_location
    cropped = frame[top:bottom, left:right]
    filename = f"{uuid.uuid4()}.jpg"
    relative_path = os.path.join("unidentified", filename)
    abs_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    try:
        cv2.imwrite(abs_path, cropped)
        return relative_path
    except Exception as e:
        print(f"❌ Failed to save unidentified face: {e}")
        return None