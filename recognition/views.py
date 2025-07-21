from django.shortcuts import render, redirect
from face_recognition import face_encodings
from .forms import PersonForm
import io
import pickle
import os
from django.conf import settings
import time
import cv2
from collections import defaultdict, deque
from django.http import StreamingHttpResponse
from .video_utils import start_video_capture, calculate_fps
from .face_utils import (
    load_known_faces, get_face_encodings, matches_face_encoding, annotate_frame, overlay_id_cards
)

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
    # to get multiple images for enrollment in json formart or CSV formart as python script needs to be written here for this.
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
                for face_encoding, face_location in zip(face_encogdings, face_locations):
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
        overlay_id_cards(frame, recognized_faces, id_card_cache, scale=SCALE_FACTOR, display_duration=CARD_DISPLAY_FRAMES)

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
    

