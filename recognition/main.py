import os
import cv2
import time
import numpy as np
from face_utils import (
    load_known_faces,
    matches_face_encoding,
    annotate_frame
)
from video_utils import start_video_capture, calculate_fps
import face_recognition

# -------------------- Configuration --------------------
known_faces_dir = './uploads/faces/'
scale_factor = 0.25  # Resize for faster encoding
tolerance = 0.6
target_fps = 30
process_every_n_frames = 3
min_confidence = 0.6
min_face_size = 60
model_path = "/models/res10_300x300_ssd_iter_140000.caffemodel"
config_path = "/models/deploy.prototxt"
window_title = 'Face Recognition - DNN Detection'

# -------------------- Load DNN Model --------------------
print("⚙️ Loading DNN face detector...")
net = cv2.dnn.readNetFromCaffe(config_path, model_path)

try:
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    print("🚀 Using GPU for inference (CUDA)")
except:
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    print("⚠️ CUDA not available. Using CPU instead.")

# -------------------- Load Known Faces --------------------
print("🔄 Loading known face images...")
known_face_encodings, known_face_names, _ = load_known_faces(
    known_faces_dir,
    '',  # No ID cards for now
    scale=scale_factor
)

# -------------------- DNN Face Detection Function --------------------
def detect_faces_dnn(frame, net, conf_threshold=0.6):
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
                                 (104.0, 177.0, 123.0))  # mean subtraction
    net.setInput(blob)
    detections = net.forward()
    
    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            boxes.append((y1, x2, y2, x1))  # (top, right, bottom, left)
    return boxes

# -------------------- Start Video Capture --------------------
cap = start_video_capture(fps=target_fps)
if not cap or not cap.isOpened():
    print("❌ Failed to initialize webcam.")
    exit(1)

print("📷 Starting webcam - Press 'q' to quit...")

frame_count = 0
prev_time = time.time()
fps_history = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)
    process_this_frame = (frame_count % process_every_n_frames == 0)

    face_locations = []
    face_names = []
    face_encodings_display = []

    if process_this_frame:
        face_locations = detect_faces_dnn(frame, net, conf_threshold=min_confidence)

        # Encode using face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations, num_jitters=1)

        for encoding in face_encodings:
            name, distance, _ = matches_face_encoding(
                encoding,
                known_face_encodings,
                known_face_names,
                tolerance=tolerance
            )
            face_names.append(name)
            face_encodings_display.append(encoding)

    # -------------------- Annotation --------------------
    frame = annotate_frame(
        frame,
        face_locations,
        face_names,
        face_encodings=face_encodings_display if process_this_frame else None,
        scale=1.0  # DNN uses original scale
    )

    fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)

    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow(window_title, frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("👋 Exiting...")
        break

cap.release()
cv2.destroyAllWindows()
