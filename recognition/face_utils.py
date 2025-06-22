import threading
import os
import cv2
import numpy as np
import face_recognition
from collections import defaultdict, deque

_KNOWN_FACES_CACHE = None
_CACHE_LOCK = threading.Lock()

def load_known_faces(known_faces_dir, id_card_dir, scale=0.5, use_cache=True):
    global _KNOWN_FACES_CACHE

    if use_cache and _KNOWN_FACES_CACHE is not None:
        return _KNOWN_FACES_CACHE

    with _CACHE_LOCK:
        known_face_encodings = []
        known_face_names = []
        id_card_cache = {}

        image_files = [f for f in os.listdir(known_faces_dir)
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        print(f"📁 Found {len(image_files)} image files in {known_faces_dir}")

        for i, filename in enumerate(sorted(image_files), 1):
            path = os.path.join(known_faces_dir, filename)
            print(f"\n[{i}/{len(image_files)}] Processing: {filename}")

            try:
                image = cv2.imread(path)
                if image is None:
                    print("   ⚠️ Could not read image")
                    continue

                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                small_image = cv2.resize(rgb_image, (0, 0), fx=scale, fy=scale)
                encodings = face_recognition.face_encodings(small_image, num_jitters=1)

                if encodings:
                    print(f"   ✅ Found {len(encodings)} face(s)")
                    known_face_encodings.append(encodings[0])
                    name = os.path.splitext(filename)[0].capitalize()
                    known_face_names.append(name)

                    idcard_path = os.path.join(id_card_dir, f'ID_{name}.jpg')
                    if os.path.exists(idcard_path):
                        id_card = cv2.imread(idcard_path)
                        if id_card is not None:
                            id_card_cache[name] = cv2.resize(id_card, (200, 250))
                            print("   🪪 ID card loaded")
                        else:
                            print("   ⚠️ Failed to load ID card image")
                    else:
                        print("   ⚠️ ID card not found")
                else:
                    print("   ⚠️ No face detected")

            except Exception as e:
                print(f"   ❌ Error: {str(e)}")

        result =  (np.array(known_face_encodings), known_face_names, id_card_cache)

        if use_cache:
            _KNOWN_FACES_CACHE = result
        return result


def get_face_encodings(image, model='hog', scale=0.25, min_size=100):
    if image is None or image.size == 0:
        return [], []

    # Use grayscale for faster processing (if color not needed)
    if model == 'hog':
        small_frame = cv2.resize(image, (0, 0), fx=scale, fy=scale)
        gray_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        face_locations = face_recognition.face_locations(gray_frame, model=model)
    else:
        small_frame = cv2.resize(image, (0, 0), fx=scale, fy=scale)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame, model=model)

    # Filter small faces
    face_locations = [
        loc for loc in face_locations
        if (loc[2] - loc[0]) >= min_size and (loc[1] - loc[3]) >= min_size
    ]

    if not face_locations:
        return [], []

    # Only convert to RGB when needed for encodings
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    face_encodings = face_recognition.face_encodings(
        rgb_small_frame,
        face_locations,
        num_jitters=1,
        model='small'  # Faster model
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

def visualize_encoding(frame, encoding, position, width=200, height=100):
    x, y = position
    vis_img = np.zeros((height, width, 3), dtype=np.uint8)

    norm_encoding = (encoding - encoding.min()) / (encoding.max() - encoding.min() + 1e-8)
    bar_width = max(1, width // len(encoding))

    for i, val in enumerate(norm_encoding):
        bar_height = int(val * height)
        color = (int(val * 255), 150, int((1 - val) * 255))
        cv2.rectangle(vis_img,
                      (i * bar_width, height - bar_height),
                      ((i + 1) * bar_width - 1, height),
                      color, -1)

    if x + width <= frame.shape[1] and y + height <= frame.shape[0]:
        frame[y:y + height, x:x + width] = vis_img

    cv2.putText(frame, "Encoding Values:", (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

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
# def overlay_id_cards(frame, recognized_faVces, id_card_cache, scale=0.25, display_duration=10):
#     """
#     Overlay ID card next to recognized faces (modifies frame in-place)
#     """
#     for name, (last_frame, face_location) in recognized_faces.items():
#         if frame_count - last_frame < display_duration and name in id_card_cache:
#             top, right, bottom, left = [int(coord / scale) for coord in face_location]
#             face_width = right - left
#             face_height = bottom - top
       
#             idcard_resized = cv2.resize(id_card_cache[name], (face_width, face_height))

#             x_start = right
#             x_end = right + face_width
#             y_start = top
#             y_end = top + face_height

#             if x_end <= frame.shape[1] and y_end <= frame.shape[0]:
#                 frame[y_start:y_end, x_start:x_end] = idcard_resized
# 🛠 Suggested Tweaks
# GPU Acceleration: Consider using dlib with CUDA or switching to face_recognition + ONNX models.
#
# Multi-threading: Move webcam capture to a separate thread to decouple UI from detection.
#
# Confidence Display: Show distance (or confidence) score under name box.
