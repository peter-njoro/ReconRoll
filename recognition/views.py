import os
import cv2
import uuid
import numpy as np
import face_recognition
from django.conf import settings
from django.contrib import messages
from django.core.signals import request_started
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from .forms import StudentForm, SessionForm
from .face_utils import get_face_encodings
from .models import FaceEncoding, Session, AttendanceRecord, Event
from threading import Thread
from recognition.recognition_runner import run_recognition

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


def start_session_view(request):
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.save()
            # redirect to session detail page or list
            return redirect('recognition:session_detail', session_id=session.id)
    else:
        form = SessionForm()

        context = {
            'form': form,
        }
    return render(request, 'recognition/start_session.html', context)

def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    if session.class_group:
        expected_students = session.class_group.students.all()
    else:
        from recognition.models import Student
        expected_students = Student.objects.none()

    present_records = AttendanceRecord.objects.filter(session=session)
    present_students = [record.student for record in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students])

    unidentified_faces = session.unidentified_faces.all()
    events = session.events.order_by('-timestamp')

    context = {
        'session': session,
        'present_Students': present_students,
        'absent_students': absent_students,
        'unidentified_faces': unidentified_faces,
        'events': events,
    }
    return render(request, 'recognition/session_detail.html', context)

def record_event(session, message, event_type='info'):
    Event.objects.create(session=session, message=message, event_type=event_type)

def start_recognition_view(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    # Mark session as ongoing
    session.status = 'ongoing'
    session.save()

    # Log event
    Event.objects.create(
        session=session,
        event_type='session_started',
        severity='info',
        message="Session started"
    )

    # Start recognition loop in the background thread
    dev_mode = request.GET.get('dev') == '1'
    t = Thread(target=run_recognition, args=(str(session_id),), kwargs={'dev_mode': dev_mode})
    t.start()

    messages.success(request, f"Recognition started for session: {session.subject}")
    return redirect('recognition:session_detail', session_id=session_id)

def end_session_view(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    if session.status != 'ended':
        session.status = 'ended'
        session.end_time = timezone.now()
        session.save()

        Event.objects.create(
            session=session,
            event_type='session_ended',
            severity='info',
            message="Session manually ended from Django UI"
        )

        messages.success(request, f"Session '{session.subject}' ended.")
    else:
        messages.info(request, f"Session '{session.subject}' was already ended.")

    return redirect('recognition:session_detail', session_id=session_id)
