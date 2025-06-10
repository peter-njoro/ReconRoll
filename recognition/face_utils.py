import face_recognition
import cv2
# from django.core.files.base import ContentFile
import numpy as np
# import io
# from PIL import Image
import os
import face_recognition

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
known_faces_dir = './uploads/faces/'
face_idcard_dir = './uploads/faces/cards/'
scale_factor = 0.25  # 0.25 = 1/4 size; use 0.5 or 1.0 if needed
tolerance = 0.5  # Lower = stricter matching (default is 0.6)

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

while cap.isOpened():
    success, frame = cap.read()

    if not success:
        print("❌ Failed to read from webcam.")
        break

    frame = cv2.flip(frame, 1)
    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    print(f"🧠 Detected {len(face_encodings)} face(s) in frame.")

    for face_location, face_encoding in zip(face_locations, face_encodings):
        distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=tolerance)

        print(f"🔍 Distances: {distances}")
        print(f"✅ Matches: {matches}")

        if any(matches):
            best_match_index = np.argmin(distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
                first_name = name.split(" ")[0]

                # Scale back up face location
                y1, x2, y2, x1 = [int(coord / scale_factor) for coord in face_location]

                # Draw face box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(frame, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                cv2.putText(frame, first_name, (x1 + 6, y2 - 6),
                            cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

                # Show ID card
                idcard_path = os.path.join(face_idcard_dir, f'ID_{name}.jpg')
                idcard = cv2.imread(idcard_path)
                if idcard is not None:
                    face_width = x2 - x1
                    face_height = y2 - y1
                    idcard_resized = cv2.resize(idcard, (face_width, face_height))
                    y_end = min(y1 + face_height, cap_height)
                    x_start = x2
                    x_end = min(x2 + face_width, cap_width)

                    frame[y1:y_end, x_start:x_end] = idcard_resized[0:(y_end - y1), 0:(x_end - x2)]
                    print(f"{name} is identified succesfully!")
                else:
                    print(f"⚠️ ID card not found for {name}: {idcard_path}")
        else:
            print("🚫 No known face match.")

    cv2.imshow('Face Recognition', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
