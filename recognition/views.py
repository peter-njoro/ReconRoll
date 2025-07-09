import os
import time
import cv2
import uuid
import numpy as np
import io
import pickle
import face_recognition
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from .forms import StudentForm
from .video_utils import start_video_capture, calculate_fps
from .face_utils import (
    load_known_faces, get_face_encodings, matches_face_encoding, annotate_frame
)
from .models import FaceEncoding
from face_recognition import face_encodings
from collections import defaultdict, deque


# Constants to be transfered to settings.py or a config file
KNOWN_FACES_DIR = os.path.join(settings.BASE_DIR, 'recognition', 'uploads', 'faces')
ID_CARD_DIR = os.path.join(settings.BASE_DIR, 'recognition', 'uploads', 'faces', 'cards')
SCALE_FACTOR = 0.25
TOLERANCE = 0.55
TARGET = 0.55
TARGET_FPS = 30
PROCESS_EVERY_N_FRAMES = 3
CARD_DISPLAY_FRAMES = 10
MIN_FACE_SIZE = 100

# Preload known data once at startup

# Create your views here.

def index(request):
    context = {
        'title': 'FaceTrack lite App', 
        'message': 'Welcome to the Recognition App!'
        }
    return render(request, 'recognition/index.html', context)

def enroll_view(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        face_images = request.FILES.getlist('face_images')

        # Validate uploaded images
        if not face_images:
            form.add_error(None, 'Please upload at least one image file.')

        if form.is_valid():
            ref_encoding = None
            valid_encodings = []

            for image in face_images:
                img_bytes = image.read()
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                face_locations, encodings = get_face_encodings(img)

                if not encodings:
                    form.add_error(None, f"No face detected in image: {image.name}")
                    continue
                elif len(encodings) > 1:
                    form.add_error(None, f"Multiple faces detected in image: {image.name}")
                    continue

                encoding = encodings[0]

                if ref_encoding is None:
                    ref_encoding = encoding
                else:
                    matches = face_recognition.compare_faces([ref_encoding], encoding, tolerance=TOLERANCE)
                    if not matches[0]:
                        form.add_error(None, f"Face in image {image.name} does not match the first face.")
                        continue

                valid_encodings.append((image.name, encodings[0]))

            # Only save the form if we have valid encodings AND no errors
            if valid_encodings and not form.errors:
                student = form.save()
                for image_name, encoding in valid_encodings:
                    filename = f"{uuid.uuid4()}.npy"
                    path = os.path.join('recognition/uploads/faces', filename)
                    abs_path = os.path.join(settings.BASE_DIR, path)
                    np.save(abs_path, encoding)

                    FaceEncoding.objects.create(
                        student=student,
                        file_path=path,
                        notes=f"Encoding from {image_name}"
                    )

                return redirect('recognition:enroll_success')
            else:
                if not valid_encodings:
                    form.add_error(None, 'No valid encodings were saved.')

    else:
        form = StudentForm()

    context = {
        'form': form,
    }
    return render(request, 'recognition/enroll.html', context)

def enroll_success(request):
    return render(request, 'recognition/enroll_success.html')


def face_detection_page(request):
    return render(request, 'recognition/face_detection.html')

    # SHOW THE CARD IN THE WEB BROWSER, THE CAMERA LIVE FEED OPTION TO BE COMPLETELY OPTIONAl


def live_recognition_page(request):
    return render(request, 'recognition/live_recognition.html')


def generate_face_stream():
    cap = start_video_capture(fps=TARGET_FPS)
    frame_count = 0
    prev_time = time.time()
    fps_history = []
    recognized_faces = {}  # name -> (last seen frame index, face location)
    recent_matches = defaultdict(lambda: deque(maxlen=5))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        frame = cv2.flip(frame, 1)
        process_this_frame = frame_count % PROCESS_EVERY_N_FRAMES == 0

        face_locations, face_names = [], []

        if process_this_frame:
            face_loactions, face_encodings = get_face_encodings(
                frame,
                model='hog',
                scale=SCALE_FACTOR,
                min_size=MIN_FACE_SIZE
            )

            if face_encodings:
                for face_encoding, face_location in zip(face_encodings, face_locations):
                    name, distance, _ = matches_face_encoding(
                        face_encoding,
                        known_face_encodings,
                        known_face_names,
                        tolerance=TOLERANCE
                    )

                    if name != "unknown":
                        recognized_faces[name] = (frame_count, face_location)
                        recent_matches[name].append(frame_count)

                    face_names.append(name)

        # Annotate frame with face boxes and names
        frame = annotate_frame(frame, face_locations, face_names, scale=SCALE_FACTOR)

        # Display FPS AND FACE COUNT
        fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)
        cv2.putText(frame, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # eNCODE FRAME TO JPEG
        _, jpeg = cv2.imencode('.jpg', frame)
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        
    cap.release()

def live_face_recognition_stream(request):
    return StreamingHttpResponse(generate_face_stream(), content_type='multipart/x-mixed-replace; boundary=frame')

def live_face_recognition_page(request):
    return render(request, 'recognition/live_recognition.html')
    

