import os
import cv2
import face_recognition
import numpy as np
from collections import defaultdict, deque

def load_known_faces(known_faces_dir, id_card_dir, scale=0.5):
    """
    Load all known face images and ID cards into memory
    Returns: encodings, names, id_card_cache
    """
    known_face_encodings = []
    known_face_names = []
    id_card_cache = {}
    
    for filename in sorted(os.listdir(known_faces_dir)):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        known_face_encodings, known_face_names, id_card_cache = load_known_faces(known_faces_dir, id_card_dir)
        try:
            image = cv2.imread(known_faces_dir + filename)
            if image is None:
                print(f"⚠️ Could not read image: {known_faces_dir + filename}")
                continue

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            small_image = cv2.resize(rgb_image, fx=scale, fy=scale)

            encodings = face_recognition.face_encodings(small_image, num_jitters=1)
            if encodings:
                known_face_encodings.append(encodings[0])
                name = os.path.splitext(filename)[0].capitalize()
                known_face_names.append(name)

                idcard_path = os.path.join(id_card_dir, f'ID_{name}.jpg')
                if os.path.exists(idcard_path):
                    id_card = cv2.imread(idcard_path)
                    id_card_cache[name] = cv2.resize(id_card, (200, 250))
                print(f"✅ Loaded: {name}")
            else:
                print(f"⚠️ No face detected in: {path}")
        except Exception as e:
            print(f"⚠️ Error processing {path}: {str(e)}")

    return np.array(known_face_encodings), known_face_names, id_card_cache

def get_face_encodings(image, model='hog', scale=0.25, min_size=100):
    """
    Detect and encode all faces in an image
    Returns: face_locations, face_encodings
    """
    small_frame = cv2.resize(image, (0, 0), fx=scale, fy=scale)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    face_locations = face_recognition.face_locations(
        rgb_small_frame,
        number_of_times_to_upsample=1,
        model=model
    )
    
    # Filter out small faces
    face_locations = [
        loc for loc in face_locations
        if (loc[2] - loc[0]) >= min_size and (loc[1] - loc[3]) >= min_size
    ]
    
    face_encodings = []
    if face_locations:
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame,
            face_locations,
            num_jitters=1
        )
    
    return face_locations, face_encodings

def matches_face_encoding(encoding, known_encodings, known_names, tolerance=0.5):
    """
    Match a single face encoding to known ones
    Returns: name, best_distance, best_match_index
    """
    distances = np.linalg.norm(known_encodings - encoding, axis=1)
    best_match_index = np.argmin(distances)
    best_distance = distances[best_match_index]
    
    name = "unknown"
    if best_distance <= tolerance:
        name = known_names[best_match_index]
    
    return name, best_distance, best_match_index

def annotate_frame(frame, face_locations, face_names, scale=0.25):
    """
    Draw rectangles and names on the frame
    Returns: annotated frame
    """
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top, right, bottom, left = [int(coord / scale) for coord in (top, right, bottom, left)]
        color = (0, 255, 0) if name != "unknown" else (0, 0, 255)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name.split()[0], (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    return frame

def overlay_id_cards(frame, recognized_faces, id_card_cache, scale=0.25, display_duration=10):
    """
    Overlay ID card next to recognized faces (modifies frame in-place)
    """
    for name, (last_frame, face_location) in recognized_faces.items():
        if frame_count - last_frame < display_duration and name in id_card_cache:
            top, right, bottom, left = [int(coord / scale) for coord in face_location]
            face_width = right - left
            face_height = bottom - top

            idcard_resized = cv2.resize(id_card_cache[name], (face_width, face_height))
            
            x_start = right
            x_end = right + face_width
            y_start = top
            y_end = top + face_height
            
            if x_end <= frame.shape[1] and y_end <= frame.shape[0]:
                frame[y_start:y_end, x_start:x_end] = idcard_resized
# 🛠 Suggested Tweaks
# GPU Acceleration: Consider using dlib with CUDA or switching to face_recognition + ONNX models.
#
# Multi-threading: Move webcam capture to a separate thread to decouple UI from detection.
#
# Confidence Display: Show distance (or confidence) score under name box.
