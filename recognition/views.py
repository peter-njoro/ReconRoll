from django.shortcuts import render, redirect
from face_recognition import face_encodings

from .forms import PersonForm
from .face_utils import  encode_face
import io
import pickle
from django.http import StreamingHttpResponse
import cv2
from .face_utils import detect_faces_from_frame
import os
import face_recognition
from django.http import StreamingHttpResponse
from django.conf import settings
from django.views.decorators import gzip




# Create your views here.

def index(request):
    context = {
        'title': 'FaceTrack lite App', 
        'message': 'Welcome to the Recognition App!'
        }
    return render(request, 'recognition/index.html', context)

def enroll_view(request):
    if request.method == 'POST':
        form = PersonForm(request.POST, request.FILES)
        if form.is_valid():
            person = form.save(commit=False)
            image_path = request.FILES['image'].temporary_file_path() \
                if hasattr(request.FILES['image'], 'temporary_file_path') else None

            if not image_path:
                # use BytesIO to handle in-memory files
                img_bytes = request.FILES['image'].read()
                image_path = io.BytesIO(img_bytes)

            encoding = encode_face(image_path)

            if encoding is not None:
                person.encoding = pickle.dumps(encoding)
                person.save()
                return redirect('recognition:enroll_success')
            else:
                form.add_error(None, 'No face detected. Try another image.')

    else:
        form = PersonForm()

    context = {
        'form':form
    }
    return render(request, 'recognition/enroll.html', context)

def enroll_success(request):
    return render(request, 'recognition/enroll_success.html')

def gen_frames():
    cap = cv2.VideoCapture(0)

    while True:
        success, frame = cap.read()
        if not success:
            break

        faces = detect_faces_from_frame(frame)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # Encode the frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        cap.release()

def face_detection_stream(request):
    return StreamingHttpResponse(gen_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

def face_detection_page(request):
    return render(request, 'recognition/face_detection.html')

def load_known_faces():
    faces_dir = os.path.join(settings.BASE_DIR, 'recognition', 'uploads', 'faces')
    known_encodings = []
    known_names = []

    for filename in os.listdir(faces_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(faces_dir, filename)
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_encodings.append(encodings[0])
                known_names.append(os.path.splitext(filename)[0])

    return known_encodings, known_names

def generate_live_feed():
    known_encodings, known_names = load_known_faces()
    try:
        cap = cv2.VideoCapture(0)
    except Exception as e:
        print("Error:", e)
        return None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]

        # Recognize faces
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"

            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = face_distances.argmin()
                if matches[best_match_index]:
                    name = known_names[best_match_index]

            # Scale back face locations since frame was resized
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.rectangle(frame, (left, bottom - 20), (right, bottom), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, name, (left + 2, bottom - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        _, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n\r\n')

    cap.release()

@gzip.gzip_page
def live_recognition_stream(request):
    return StreamingHttpResponse(generate_live_feed(), content_type='multipart/x-mixed-replace; boundary=frame')

def live_recognition_page(request):
    return render(request, 'recognition/live_recognition.html')



