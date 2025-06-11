import face_recognition
import cv2
# from django.core.files.base import ContentFile
import numpy as np
# import io
# from PIL import Image
import os
import face_recognition
import time

# REMINDER TO CREATE A FUNCTION THAT TAKES THE ENCODINGS AND STORES THEM IN THE DATABASE UNDER THE INSTITUION

# def encode_face(image_path):
#     image = face_recognition.load_image_file(image_path)
#     encodings = face_recognition.face_encodings(image)

#     if not encodings:
#         return None # No faces

#     return encodings[0]

# def detect_faces_from_frame(frame):
#     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

#     face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

#     faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

#     return faces

# === Configuration ===

# === Settings ===
# Configuration
known_faces_dir = './uploads/faces/'
face_idcard_dir = './uploads/faces/cards/'
scale_factor = 0.25
tolerance = 0.5
target_fps = 30
process_every_n_frames = 3
card_display_frames = 10
min_face_size = 100

# === Load known faces ===
print("🔄 Loading known face images...")

# Cache for known faces and ID cards
known_face_encodings = []
known_face_names = []
id_card_cache = {}

# Preload all known faces and ID cards
for filename in sorted(os.listdir(known_faces_dir)):
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

    path = os.path.join(known_faces_dir, filename)
    try:
        image = cv2.imread(path)
        if image is None:
            print(f"⚠️ Could not read image: {path}")
            continue

        # Convert to RGB and resize for faster encoding
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        small_image = cv2.resize(rgb_image, (0, 0), fx=0.5, fy=0.5)  # Half size for encoding

        encodings = face_recognition.face_encodings(small_image)
        if encodings:
            known_face_encodings.append(encodings[0])
            name = os.path.splitext(filename)[0].capitalize()
            known_face_names.append(name)

            # Preload and resize ID card if exists
            idcard_path = os.path.join(face_idcard_dir, f'ID_{name}.jpg')
            if os.path.exists(idcard_path):
                id_card = cv2.imread(idcard_path)
                # Resize to common size to save memory and avoid resizing later
                id_card_cache[name] = cv2.resize(id_card, (200, 250))  # Standard ID card size
            print(f"✅ Loaded: {name}")
        else:
            print(f"⚠️ No face detected in: {path}")
    except Exception as e:
        print(f"⚠️ Error processing {path}: {str(e)}")

if not known_face_encodings:
    raise RuntimeError("❌ No known faces loaded. Please check your images.")

# Convert to numpy array for faster distance calculation
known_face_encodings = np.array(known_face_encodings)

# === Start webcam ===
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Reduce resolution for better FPS
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, target_fps)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Reduce buffer to minimize latency

print("📷 Starting webcam...")

# Performance tracking
frame_count = 0
prev_time = time.time()
fps_history = []
recognized_faces = {}  # name -> (last seen frame index, face location)

# Face detection model selection (hog is faster but less accurate than cnn)
face_detection_model = 'hog' if scale_factor <= 0.5 else 'cnn'

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)

    # Only process every nth frame to improve FPS
    process_this_frame = frame_count % process_every_n_frames == 0

    # Debug view
    debug_frame = frame.copy()
    cv2.putText(debug_frame, f"Processing: {'YES' if process_this_frame else 'NO'}",
                (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # show the resized version being processed
    small_debug = cv2.resize(debug_frame, (0, 0), fx=0.5, fy=0.5)
    cv2.imshow('Processing View', small_debug)



    # Resize and convert frame once
    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = []
    face_names = []

    if process_this_frame:
        # Use faster face detection model based on scale factor
        face_locations = face_recognition.face_locations(
            rgb_small_frame,
            number_of_times_to_upsample=2,  # Reduce upsampling for speed
            model=face_detection_model
        )

        # Filter out small faces
        face_locations = [
            loc for loc in face_locations
            if (loc[2] - loc[0]) >= min_face_size and (loc[1] - loc[3]) >= min_face_size
        ]

        if face_locations:
            print(f"🔍 Detected {len(face_locations)} face(s)")
            face_encodings = face_recognition.face_encodings(
                rgb_small_frame,
                face_locations,
                num_jitters=1  # Reduce from default 10 for speed
            )
            print(f"📊 Generated {len(face_encodings)} encoding(s)")

            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Fast distance calculation using numpy
                distances = np.linalg.norm(known_face_encodings - face_encoding, axis=1)
                print("📐 Distances to known faces:", distances)
                best_match_index = np.argmin(distances)
                print(f"🏆 Best match index: {best_match_index}, Distance: {distances[best_match_index]}")

                name = "unknown"
                if distances[best_match_index] <= tolerance:
                    name = known_face_names[best_match_index]
                    # Store face location with recognition info
                    recognized_faces[name] = (frame_count, face_location)
                    print(f"✅ Recognized: {name} (distance: {distances[best_match_index]:.2f})")

                else:
                    print(f"❌ No match found (min distance {distances[best_match_index]:.2f} > tolerance {tolerance})")
                face_names.append(name)
        else:
            # If no faces detected, clear some memory
            face_encodings = []
    else:
        # Reuse face data from previous processed frame
        face_names = [name for name, (last_frame, _) in recognized_faces.items()
                      if frame_count - last_frame < card_display_frames]

    # Draw all faces (recognized or not)
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face location
        top, right, bottom, left = [int(coord / scale_factor) for coord in (top, right, bottom, left)]
        color = (0, 255, 0) if name != "unknown" else (0, 0, 255)

        # Draw bounding box and label
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name.split()[0], (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Show ID cards for recently recognized faces
    for name, (last_frame, face_location) in recognized_faces.items():
        if frame_count - last_frame < card_display_frames and name in id_card_cache:
            # Scale back up the stored face location
            top, right, bottom, left = [int(coord / scale_factor) for coord in face_location]
            face_width = right - left
            face_height = bottom - top

            # Get cached ID card
            idcard_resized = cv2.resize(id_card_cache[name], (face_width, face_height))

            # Position the ID card to the right of the face
            x_start = right
            x_end = right + face_width
            y_start = top
            y_end = top + face_height

            # Ensure we don't go beyond frame boundaries
            if x_end <= frame.shape[1] and y_end <= frame.shape[0]:
                frame[y_start:y_end, x_start:x_end] = idcard_resized

    # Display performance info
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time
    fps_history.append(fps)
    if len(fps_history) > 10:
        fps_history.pop(0)

    avg_fps = sum(fps_history) / len(fps_history)
    cv2.putText(frame, f'FPS: {int(avg_fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Show frame
    cv2.imshow('Face Recognition', frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
# 🛠 Suggested Tweaks
# GPU Acceleration: Consider using dlib with CUDA or switching to face_recognition + ONNX models.
#
# Multi-threading: Move webcam capture to a separate thread to decouple UI from detection.
#
# Confidence Display: Show distance (or confidence) score under name box.
