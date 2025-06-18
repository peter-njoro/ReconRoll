import os
import cv2
import time
from collections import defaultdict, deque
from face_utils import *
from video_utils import *

# Configuration
known_faces_dir = './uploads/faces/'
face_idcard_dir = './uploads/faces/cards/'
scale_factor = 0.5
tolerance = 0.6
target_fps = 30
process_every_n_frames = 4
card_display_frames = 10
min_face_size = 80

# Load known faces
print("🔄 Loading known face images...")
known_face_encodings, known_face_names, id_card_cache = load_known_faces(
    known_faces_dir, face_idcard_dir, scale=scale_factor
)
print("I'm still working ...")
# Start video capture
cap = start_video_capture(fps=target_fps)

# Initialize tracking variables
frame_count = 0
prev_time = time.time()
fps_history = []
recognized_faces = {}  # name -> (last seen frame index, face location)
recent_matches = defaultdict(lambda: deque(maxlen=5))

print("📷 Starting webcam...")

while cap.isOpened():
    frame_start_time = time.time()
    frame_time = time.time() - frame_start_time
    # skip frames if we;re falling behind
    for _ in range(2 if frame_time > 1.0/target_fps else 0):
        cap.grab()
        frame_count += 1
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)
    process_this_frame = frame_count % process_every_n_frames == 0

    # Debug view
    # debug_frame = frame.copy()
    # cv2.putText(debug_frame, f"Processing: {'YES' if process_this_frame else 'NO'}",
    #             (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    # cv2.imshow('Processing View', cv2.resize(debug_frame, (0, 0), fx=0.5, fy=0.5))

    cv2.putText(frame, f'Frame: {frame_time*1000:.1f}ms', (10, 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)



    face_locations = []
    face_names = []

    if process_this_frame:
        face_locations, face_encodings = get_face_encodings(
            frame,
            model='hog',
            scale=scale_factor,
            min_size=min_face_size
        )

        if face_encodings:
            for face_encoding, face_location in zip(face_encodings, face_locations):
                name, distance, _ = matches_face_encoding(
                    face_encoding,
                    known_face_encodings,
                    known_face_names,
                    tolerance=tolerance
                )
                
                if name != "unknown":
                    label = f"{name} ({distance: .2f})"
                    recognized_faces[name] = (frame_count, face_location)
                    recent_matches[name].append(frame_count)
                else:
                    enc_preview = ', '.join(f"{v:.2f}" for v in face_encoding[:4])
                    label = f"{name}: [{enc_preview}, ...]"
                
                face_names.append(name)

                encoding_time = time.time() - frame_start_time
                cv2.putText(frame, f'Encoding: {encoding_time * 1000:.1f}ms', (10, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Annotate frame with face boxes and names
    frame = annotate_frame(frame, face_locations, face_names, scale=scale_factor)
    
    # Overlay ID cards for recognized faces
    # overlay_id_cards(frame, recognized_faces, id_card_cache, scale=scale_factor, display_duration=card_display_frames)

    # Calculate and display FPS
    fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('Face Recognition', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()