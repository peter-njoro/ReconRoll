import os
import cv2
import time
import numpy as np
from face_utils import load_known_faces, get_face_encodings, matches_face_encoding, annotate_frame, safe_load_dnn_model
from video_utils import start_video_capture, calculate_fps
from collections import deque

# -----------------------------
# ✅ Config
# -----------------------------
known_faces_dir = './uploads/faces/'
scale_factor = 0.25
tolerance = 0.6
target_fps = 30
process_every_n_frames = 3
min_face_size = 60
min_confidence = 0.5

# -----------------------------
# ✅ Load known faces
# -----------------------------
print("🔄 Loading known face images...")
known_face_encodings, known_face_names, _ = load_known_faces(
    known_faces_dir, '', scale=scale_factor  # Empty string for id_card_dir
)

# -----------------------------
# ✅ Load DNN face detector
# -----------------------------
net = safe_load_dnn_model()

# -----------------------------
# ✅ DNN Face Detection Function
# -----------------------------
def detect_faces_dnn(image, net, conf_threshold=0.5):
    h, w = image.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    face_locations = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            face_locations.append((startY, endX, endY, startX))
    return face_locations

# -----------------------------
# ✅ Start Webcam
# -----------------------------
cap = start_video_capture(fps=target_fps)
if cap is None:
    print("❌ Unable to access webcam. Exiting.")
    exit(1)
frame_count = 0
prev_time = time.time()
fps_history = []
recognition_history = deque(maxlen=10)


print("📷 Starting webcam - Press 'q' to quit...")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)
    process_this_frame = frame_count % process_every_n_frames == 0

    face_locations = []
    face_names = []
    face_encodings_display = []

    if process_this_frame:
        face_locations = detect_faces_dnn(frame, net, conf_threshold=min_confidence)
        if face_locations:
            _, face_encodings = get_face_encodings(frame, model='hog', scale=scale_factor, min_size=min_face_size)

            if face_encodings:
                recognition_frame_info = []
                for i, face_encoding in enumerate(face_encodings):
                    name, distance, _ = matches_face_encoding(
                        face_encoding, known_face_encodings, known_face_names, tolerance
                    )
                    recognition_frame_info.append((name, face_encoding))
                    print(f"[{time.strftime('%H:%M:%S')}] Detected: {name}")
                    print(f"  Match Distance: {distance:.4f}")
                    print(f"  Encoding Sample: {np.round(face_encoding[:5], 4)}\n")

                recognition_history.appendleft(recognition_frame_info)

    frame = annotate_frame(
        frame,
        face_locations,
        face_names,
        face_encodings=face_encodings_display if process_this_frame else None,
        scale=scale_factor
    )

    # info panel
    info_panel = np.zeros((frame.shape[0], 350, 3), dtype=np.uint8)
    y = 30
    for entry in recognition_history:
        for i, (name, encoding) in enumerate(entry):
            cv2.putText(info_panel, f"Face: {name}", (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if name != 'unknown' else (0, 0, 255), 1)
            enc_preview = ', '.join(f"{x:.2f}" for x in encoding[:3])
            cv2.putText(info_panel, f"Enc: [{enc_preview}...]", (10, y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
            y += 60

    # FPS and Face Count
    fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Display both windows
    cv2.imshow('Face Recognition - Webcam Feed', frame)
    cv2.imshow('Recognition Info', info_panel)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
