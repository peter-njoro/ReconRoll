import os
import cv2
import uuid
import numpy as np
import face_recognition
from recognition.models import Student, UnidentifiedFace
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

def matches_face_encoding(encoding, known_encodings, known_names, unknown_encodings=None, tolerance=0.5):
    """
    Compare a face encoding against known and unknown encodings.
    Returns:
      - name: student name or "unknown"
      - distance: best match distance
      - index: index of the match (for known) or None (for unknown)
      - is_known: True if match was a known student, False if it's an existing unknown
    """
    best_name = "unknown"
    best_distance = float("inf")
    best_index = -1
    is_known = False

    # 1. Compare with known encodings
    if known_encodings is not None and known_encodings.any():
        distances = np.linalg.norm(known_encodings - encoding, axis=1)
        idx = np.argmin(distances)
        if distances[idx] <= tolerance:
            best_name = known_names[idx]
            best_distance = distances[idx]
            best_index = idx
            is_known = True

    # 2. Compare with unknown encodings if still "unknown"
    if not is_known and unknown_encodings is not None and len(unknown_encodings) > 0:
        distances = np.linalg.norm(unknown_encodings - encoding, axis=1)
        idx = np.argmin(distances)
        if distances[idx] <= tolerance:
            best_name = "unknown"  # but matched an existing unknown
            best_distance = distances[idx]
            best_index = idx
            is_known = False

    return best_name, best_distance, best_index, is_known


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

def save_unidentified_faces(frame, face_location, session=None, base_dir='uploads/unidentified/', encoding=None):
    """
    Save both the cropped face AND the full frame with face marked.
    Returns: (cropped_path, full_path, encoding)
    """
    import cv2, os, uuid
    from django.conf import settings

    top, right, bottom, left = face_location

    # Save cropped face
    cropped = frame[top:bottom, left:right]
    cropped_filename = f"{uuid.uuid4()}_cropped.jpg"
    cropped_path = os.path.join(base_dir, 'cropped', cropped_filename)
    cropped_abs_path = os.path.join(settings.MEDIA_ROOT, cropped_path)
    os.makedirs(os.path.dirname(cropped_abs_path), exist_ok=True)

    # Save full frame with rectangle
    full_frame = frame.copy()
    cv2.rectangle(full_frame, (left, top), (right, bottom), (0, 255, 0), 2)
    full_filename = f"{uuid.uuid4()}_full.jpg"
    full_path = os.path.join(base_dir, 'full', full_filename)
    full_abs_path = os.path.join(settings.MEDIA_ROOT, full_path)
    os.makedirs(os.path.dirname(full_abs_path), exist_ok=True)

    try:
        cv2.imwrite(cropped_abs_path, cropped)
        cv2.imwrite(full_abs_path, full_frame)

        # If encoding was not passed, compute it
        if encoding is None:
            import face_recognition
            rgb_face = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            encodings = face_recognition.face_encodings(rgb_face)
            encoding = encodings[0] if encodings else None

        return cropped_path, full_path, encoding
    except Exception as e:
        print(f"❌ Failed to save unidentified face: {e}")
        return None, None, None
