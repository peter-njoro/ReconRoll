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
known_faces_dir = './uploads/faces/'
face_idcard_dir = './uploads/faces/cards/'
scale_factor = 0.25  # Smaller = faster
tolerance = 0.5      # Lower = stricter match
card_display_frames = 10  # Number of frames to persist card display

# === Load known faces ===
known_face_encodings = []
known_face_names = []

print("🔄 Loading known face images...")
for filename in os.listdir(known_faces_dir):
    path = os.path.join(known_faces_dir, filename)
    image = cv2.imread(path)
    if image is None:
        print(f"⚠️ Could not read image: {path}")
        continue

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_image)
    if encodings:
        known_face_encodings.append(encodings[0])
        name = os.path.splitext(filename)[0].capitalize()
        known_face_names.append(name)
        print(f"✅ Loaded: {name}")
    else:
        print(f"⚠️ No face detected in: {path}")

if not known_face_encodings:
    raise RuntimeError("❌ No known faces loaded. Please check your images.")

# === Start webcam ===
cap = cv2.VideoCapture(0)
cap_width = int(cap.get(3))
cap_height = int(cap.get(4))
print("📷 Starting webcam...")

process_this_frame = True
frame_count = 0
prev_time = time.time()
recognized_faces = {}  # name -> last seen frame index

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    frame_count += 1
    frame = cv2.flip(frame, 1)

    # Resize for performance
    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = []
    face_encodings = []
    face_names = []

    if process_this_frame:
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for face_encoding in face_encodings:
            distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance)

            name = "unknown"
            if any(matches):
                best_match_index = np.argmin(distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
                    recognized_faces[name] = frame_count  # Update last seen

            face_names.append(name)

    # Draw all faces (recognized or not)
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top, right, bottom, left = [int(coord / scale_factor) for coord in (top, right, bottom, left)]
        color = (0, 255, 0) if name != "unknown" else (0, 0, 255)

        # Draw bounding box and label
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name.split()[0], (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

        # Show ID card if recently recognized
        if name in recognized_faces and (frame_count - recognized_faces[name]) < card_display_frames:
            idcard_path = os.path.join(face_idcard_dir, f'ID_{name}.jpg')
            idcard = cv2.imread(idcard_path)
            if idcard is not None:
                face_width = right - left
                face_height = bottom - top
                idcard_resized = cv2.resize(idcard, (face_width, face_height))

                x_start = right
                x_end = min(right + face_width, cap_width)
                y_end = min(top + face_height, cap_height)

                frame[top:y_end, x_start:x_end] = idcard_resized[0:(y_end - top), 0:(x_end - right)]
            else:
                print(f"⚠️ ID card not found for {name}: {idcard_path}")

    # Display FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Show frame
    cv2.imshow('Face Recognition', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    process_this_frame = not process_this_frame

cap.release()
cv2.destroyAllWindows()

# 🛠 Suggested Tweaks
# GPU Acceleration: Consider using dlib with CUDA or switching to face_recognition + ONNX models.
#
# Multi-threading: Move webcam capture to a separate thread to decouple UI from detection.
#
# Confidence Display: Show distance (or confidence) score under name box.
