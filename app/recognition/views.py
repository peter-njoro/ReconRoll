import os
import cv2
import uuid
import threading
import numpy as np
import face_recognition
from threading import Thread
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.core.cache import cache
from recognition.forms import StudentForm, SessionForm
from recognition.face_utils import get_face_encodings
from recognition.models import FaceEncoding, Session, AttendanceRecord, Event, Student
from recognition.recognition_runner import run_recognition, active_recognition

# Constants to be transferred to settings.py or a config file
KNOWN_FACES_DIR = os.path.join(settings.BASE_DIR, 'recognition', 'uploads', 'faces')
ID_CARD_DIR = os.path.join(settings.BASE_DIR, 'recognition', 'uploads', 'faces', 'cards')
SCALE_FACTOR = 0.25
TOLERANCE = 0.55
TARGET = 0.55
TARGET_FPS = 30
PROCESS_EVERY_N_FRAMES = 3
CARD_DISPLAY_FRAMES = 10
MIN_FACE_SIZE = 100

def index(request):
    context = {
        'title': 'FaceTrack lite App', 
        'message': 'Welcome to FaceTrack Lite: finally, a tool that stares back at you harder than your laptop’s front camera during an online exam 👁️👁️. Don’t worry, we only judge a little.'
    }
    return render(request, 'recognition/index.html', context)

def enroll_view(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        face_images = request.FILES.getlist('face_images')
        progress_key = f"enroll_progress_{request.session.session_key}"
        cache.set(progress_key, 0, timeout=600)

        # Validate uploaded images
        if not face_images:
            form.add_error(None, 'Please upload at least one image file.')

        if form.is_valid():
            ref_encoding = None
            valid_encodings = []
            total = len(face_images)
            for idx, image in enumerate(face_images):
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

                # Update progress in cache
                cache.set(progress_key, int((idx + 1) / total * 100), timeout=600)

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

        # Reset progress on finish
        cache.set(progress_key, 100, timeout=600)
    else:
        form = StudentForm()
        # Reset progress on GET
        progress_key = f"enroll_progress_{request.session.session_key}"
        cache.set(progress_key, 0, timeout=600)

    context = {'form': form}
    return render(request, 'recognition/enroll.html', context)

def enroll_progress(request):
    progress_key = f"enroll_progress_{request.session.session_key}"
    progress = cache.get(progress_key, 0)
    return JsonResponse({'progress': progress})

def enroll_success(request):
    return render(request, 'recognition/enroll_success.html')

@login_required
def create_session_view(request):
    """View for creating a new session"""
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.status = 'ready'
            session.save()
            messages.success(request, f"Session '{session.subject}' created successfully!")
            return redirect('recognition:session_detail', session_id=session.id)
    else:
        form = SessionForm()

    context = {'form': form}
    return render(request, 'recognition/start_session.html', context)

def start_recognition_for_session(request, session_id, dev_mode=False):
    """Start recognition for an existing session"""
    session = get_object_or_404(Session, id=session_id)

    # Check if session is already running
    if str(session_id) in active_recognition:
        active_session = active_recognition[str(session_id)]
        if active_session.get("thread") and active_session["thread"].is_alive():
            messages.warning(request, f"Recognition is already running for session: {session.subject}")
            return redirect('recognition:session_detail', session_id=session_id)

    # Validate session state
    if session.status == 'ended':
        messages.error(request, f"Cannot start session '{session.subject}' - it has already ended.")
        return redirect('recognition:session_detail', session_id=session_id)

    # Check if we have students in the class group (for non-dev mode)
    if not dev_mode and session.class_group and session.class_group.students.count() == 0:
        messages.warning(request, f"Class group '{session.class_group.name}' has no students. Please add students first.")
        return redirect('recognition:session_detail', session_id=session_id)

    # Check if we have any face encodings in the database (for non-dev mode)
    if not dev_mode and not FaceEncoding.objects.exists():
        messages.warning(request, "No face encodings found in database. Please enroll students first.")
        return redirect('recognition:session_detail', session_id=session_id)

    stop_flag = threading.Event()
    
    try:
        # Start recognition in a separate thread
        t = Thread(
            target=run_recognition,
            args=(str(session_id),),
            kwargs={
                'dev_mode': dev_mode,
                'stop_flag': stop_flag
            },
            name=f"RecognitionThread-{session_id}-{'dev' if dev_mode else 'prod'}"
        )
        t.daemon = True
        t.start()

        # Store the thread and stop flag for management
        active_recognition[str(session_id)] = {
            "thread": t,
            "stop_flag": stop_flag,
            "started_at": timezone.now(),
            "mode": "dev" if dev_mode else "prod"
        }

        # Update session status
        session.status = 'ongoing'
        session.started_by = request.user
        session.save()

        # Log the start event
        Event.objects.create(
            session=session,
            event_type='session_started',
            severity='info',
            message=f"Session started in {'DEV' if dev_mode else 'PRODUCTION'} mode"
        )

        # Success message with appropriate mode indication
        mode_info = " (DEV MODE - using main.py)" if dev_mode else ""
        messages.success(request, f"Recognition started{mode_info} for session: {session.subject}")

        # Redirect to session detail with dev mode parameter if applicable
        if dev_mode:
            return redirect(reverse('recognition:session_detail', kwargs={'session_id': session_id}) + '?dev=1')
        else:
            return redirect('recognition:session_detail', session_id=session_id)

    except Exception as e:
        # Handle any errors during thread startup
        messages.error(request, f"Failed to start recognition: {str(e)}")
        session.status = 'ready'  # Reset status if startup failed
        session.save()
        
        # Clean up if thread was partially created
        if str(session_id) in active_recognition:
            active_recognition.pop(str(session_id))
            
        return redirect('recognition:session_detail', session_id=session_id)

@login_required
def start_session_view(request, session_id=None):
    """
    Unified view for starting recognition sessions
    If session_id is provided: start recognition for that session
    If no session_id: redirect to session creation
    """
    if session_id:
        dev_mode = request.GET.get('dev') == '1'
        return start_recognition_for_session(request, session_id, dev_mode)
    else:
        # Redirect to session creation view
        return redirect('recognition:create_session_view')

def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    # Check if this session was started in dev mode
    is_dev_mode = request.GET.get('dev') == '1' or (session.status == 'ongoing' and 'dev' in request.META.get('HTTP_REFERER', ''))

    expected_students = session.class_group.students.all() if session.class_group else Student.objects.none()

    present_records = AttendanceRecord.objects.filter(session=session)
    present_students = [record.student for record in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students])

    unidentified_faces = session.unidentified_faces.all()
    events = session.events.order_by('-timestamp')

    context = {
        'session': session,
        'present_students': present_students,
        'absent_students': absent_students,
        'unidentified_faces': unidentified_faces,
        'events': events,
        'is_dev_mode': is_dev_mode
    }
    return render(request, 'recognition/session_detail.html', context)

def session_events_partial(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    events = session.events.order_by('-timestamp')[:20]
    html = render_to_string('recognition/partials/_events_list.html', {'events': events})
    return HttpResponse(html)

def session_present_students_partial(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [r.student for r in present_records]
    html = render_to_string('recognition/partials/_present_students.html', {'present_students': present_students})
    return HttpResponse(html)

def session_absent_students_partial(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    expected_students = session.class_group.students.all() if session.class_group else []
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [r.student for r in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students]) if expected_students else []
    html = render_to_string('recognition/partials/_absent_students.html', {'absent_students': absent_students})
    return HttpResponse(html)

def session_unidentified_faces_partial(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    unidentified_faces = session.unidentified_faces.all()
    html = render_to_string('recognition/partials/_unidentified_faces.html', {'unidentified_faces': unidentified_faces})
    return HttpResponse(html)

def record_event(session, message, event_type='info'):
    Event.objects.create(session=session, message=message, event_type=event_type)

def recognition_progress_partial(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    total_expected = session.class_group.students.count() if session.class_group else 0
    present_count = session.attendance_records.count()
    unknown_count = session.unidentified_faces.count()
    return JsonResponse({
        "present_count": present_count,
        "total_expected": total_expected,
        "unknown_count": unknown_count,
    })

def end_session_view(request, session_id):
    session = get_object_or_404(Session, id=session_id)

    # Stop running thread/process if exists
    active = active_recognition.get(str(session_id))
    if active:
        active["stop_flag"].set()

        # Also terminate subprocess if running in dev mode
        if "process" in active and active["process"]:
            active["process"].terminate()

        print(f"Sent stop signal to recognition for session {session_id}")

        # Clean up
        active_recognition.pop(str(session_id), None)

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

def sessions_list(request):
    sessions = Session.objects.all().order_by('-start_time')
    
    # Get active session information
    active_session_info = {}
    for session_id, session_data in active_recognition.items():
        try:
            session_obj = Session.objects.get(id=session_id)
            active_session_info[str(session_id)] = {
                'is_active': session_data.get("thread") and session_data["thread"].is_alive(),
                'mode': session_data.get("mode", "unknown")
            }
        except (Session.DoesNotExist, ValueError):
            # Clean up invalid entries
            active_recognition.pop(session_id, None)
    
    context = {
        'sessions': sessions,
        'active_session_info': active_session_info
    }
    return render(request, 'recognition/session_list.html', context)

def get_active_sessions(request):
    """Get list of currently active sessions"""
    active_sessions = []
    for session_id, session_data in active_recognition.items():
        try:
            session = Session.objects.get(id=session_id)
            active_sessions.append({
                'session': session,
                'thread_alive': session_data.get("thread", None) and session_data["thread"].is_alive(),
                'mode': session_data.get("mode", "unknown"),
                'started_at': session_data.get("started_at", timezone.now())
            })
        except Session.DoesNotExist:
            # Clean up non-existent sessions
            active_recognition.pop(session_id, None)
    
    return active_sessions

def stop_all_sessions(request):
    """Stop all active recognition sessions (admin function)"""
    stopped_count = 0
    for session_id, session_data in active_recognition.items():
        try:
            session = Session.objects.get(id=session_id)
            if session_data.get("stop_flag"):
                session_data["stop_flag"].set()
                
            # Update session status
            if session.status == 'ongoing':
                session.status = 'ended'
                session.end_time = timezone.now()
                session.save()
                
                Event.objects.create(
                    session=session,
                    event_type='session_ended',
                    severity='info',
                    message="Session stopped by admin"
                )
                
            stopped_count += 1
            
        except Session.DoesNotExist:
            pass
        
        # Clean up
        active_recognition.pop(session_id, None)
    
    messages.info(request, f"Stopped {stopped_count} active sessions")
    return redirect('recognition:sessions_list')

def session_status_api(request, session_id):
    """API endpoint to check session status"""
    session = get_object_or_404(Session, id=session_id)
    
    active_data = active_recognition.get(str(session_id), {})
    thread_alive = active_data.get("thread") and active_data["thread"].is_alive()
    
    return JsonResponse({
        'session_id': session_id,
        'status': session.status,
        'thread_alive': thread_alive,
        'mode': active_data.get("mode", "none"),
        'started_at': active_data.get("started_at", None),
        'present_count': session.attendance_records.count(),
        'unknown_count': session.unidentified_faces.count()
    })