import os
import cv2
import time
import numpy as np
from collections import defaultdict, deque
from face_utils import (
    load_known_faces,
    get_face_encodings,
    matches_face_encoding,
    annotate_frame
)
from video_utils import start_video_capture, calculate_fps

# -------------------- Configuration --------------------
known_faces_dir = './uploads/faces/'
scale_factor = 0.25
tolerance = 0.6
target_fps = 30
process_every_n_frames = 3
min_face_size = 60
id_card_dir = ''  # No ID cards for now
window_title = 'Face Recognition - Encoding Visualization'

# -------------------- Initialization --------------------
print("🔄 Loading known face images...")
known_face_encodings, known_face_names, _ = load_known_faces(
    known_faces_dir,
    id_card_dir,
    scale=scale_factor
)

cap = start_video_capture(fps=target_fps)

if not cap or not cap.isOpened():
    print("❌ Failed to initialize webcam.")
    exit(1)

print("📷 Starting webcam stream - Press 'q' to quit...")

frame_count = 0
prev_time = time.time()
fps_history = []

# -------------------- Main Loop --------------------
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)  # Mirror view
    process_this_frame = (frame_count % process_every_n_frames == 0)

    face_locations = []
    face_names = []
    face_encodings_display = []

    if process_this_frame:
        face_locations, face_encodings = get_face_encodings(
            frame,
            model='hog',
            scale=scale_factor,
            min_size=min_face_size
        )

        for face_encoding in face_encodings:
            name, distance, _ = matches_face_encoding(
                face_encoding,
                known_face_encodings,
                known_face_names,
                tolerance=tolerance
            )
            face_names.append(name)
            face_encodings_display.append(face_encoding)

    # -------------------- Annotation --------------------
    frame = annotate_frame(
        frame,
        face_locations,
        face_names,
        face_encodings=face_encodings_display if process_this_frame else None,
        scale=scale_factor
    )

    # -------------------- Performance Info --------------------
    fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)

    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # -------------------- Display --------------------
    cv2.imshow(window_title, frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("👋 Exiting...")
        break

cap.release()
cv2.destroyAllWindows()
