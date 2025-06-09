import face_recognition
import cv2
# from django.core.files.base import ContentFile
import numpy as np
# import io
# from PIL import Image
import os
import face_recognition



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

known_faces_dir = './uploads/faces/'
face_idcard_dir = './uploads/faces/cards/'

known_face_image_files = os.listdir(known_faces_dir)
known_face_encoding = []

for known_face in known_face_image_files:
    image_path = os.path.join(known_faces_dir, known_face)
    image = cv2.imread(image_path)
    if image is None:
        print(f"⚠️ Could not read image: {image_path}")
        continue  # Skip this file
    known_face_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    known_face_encoding.append(face_recognition.face_encodings(known_face_image)[0])


cap = cv2.VideoCapture(0)
cap_width = int(cap.get(3))
cap_height = int(cap.get(4))

while cap.isOpened():
    success, image_original = cap.read()

    if success:
        image_original = cv2.flip(image_original, 1)
        image = cv2.cvtColor(cv2.resize(image_original, (0, 0), None, 0.25, 0.25), cv2.COLOR_BGR2RGB)

        detected_face_locations = face_recognition.face_locations(image)
        detected_face_encodings = face_recognition.face_encodings(image, detected_face_locations)

        for face_location, face_encoding, in zip(detected_face_locations, detected_face_encodings):
            matches = face_recognition.compare_faces(known_face_encoding, face_encoding)
            face_similarity_distance = face_recognition.face_distance(known_face_encoding, face_encoding)
            index_matched = np.argmin(face_similarity_distance)


            if matches[index_matched]:
                face_matched = os.path.splitext(known_face_image_files[index_matched])[0]
                first_name = face_matched.split(" ")[0]
                y1, x2, y2, x1 = face_location
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                # Draw green box around face
                cv2.rectangle(image_original, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Draw filled rectangle below the face for text background
                cv2.rectangle(image_original, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)

                # Write name on the filled rectangle
                cv2.putText(image_original, first_name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

                width = (x2 - x1)//2 
                height = (y2 - y1)
                idcard_horizontal_axis = x2 + width 
                idcard_vertical_axis = y1 + cap_height

                idcard_path = os.path.join(face_idcard_dir, f'ID_{face_matched}.jpg')
                idcard_display = cv2.imread(idcard_path)
                if idcard_display is not None:
                    idcard_display = cv2.resize(idcard_display, (width, height))
                    image_original[y1:idcard_vertical_axis, x2:idcard_horizontal_axis] = idcard_display
                else:
                    print(f"⚠️ ID card not found: {idcard_path}")


        cv2.imshow('Face detection', image_original)
        cv2.waitKey(1)
    else:
        break

cap.release()
cap.destroyAllWindows()

