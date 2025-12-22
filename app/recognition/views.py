import os
import cv2
import uuid
import numpy as np
import face_recognition
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from recognition.forms import StudentForm, SessionForm
from recognition.face_utils import (
    get_face_encodings, 
    annotate_frame, 
    load_known_encodings_from_db,
    matches_face_encoding
)
from recognition.models import FaceEncoding, Session, AttendanceRecord, Event, Student
from recognition.recognition_runner import run_recognition, active_recognition, frame_queue
import time

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

# ===== PERFORMANCE OPTIMIZATION =====
# Cache encodings globally with TTL of 10 minutes (avoid DB queries per frame)
ENCODING_CACHE_KEY = "known_face_encodings"
ENCODING_CACHE_TTL = 600  # 10 minutes
FRAME_SKIP_COUNTER = {}  # Track frame count per session for skipping

def get_cached_known_encodings(session=None, force_reload=False):
    """
    Get known face encodings from cache, reload from DB if expired.
    This avoids database queries on every frame upload.
    
    Args:
        session: Session object (optional). If provided, scopes encodings to class group.
        force_reload: Force cache refresh
    
    Returns:
        {'encodings': np.array, 'names': list}
    """
    # Generate cache key based on session scope
    cache_key = ENCODING_CACHE_KEY if not session else f"{ENCODING_CACHE_KEY}_session_{session.id}"
    
    if force_reload:
        cache.delete(cache_key)
    
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Cache miss: reload from database using face_utils function
    known_encodings, known_names = load_known_encodings_from_db(session=session)
    
    result = {
        'encodings': known_encodings,
        'names': known_names
    }
    cache.set(cache_key, result, ENCODING_CACHE_TTL)
    return result

@csrf_exempt
def upload_frame(request):
    """
    API endpoint for webcam_stream.py to upload frames for processing.
    OPTIMIZED for speed: caching, frame skipping, and minimal processing.
    Uses face_utils.py functions for face detection and encoding.
    """
    if request.method != "POST" or not request.FILES.get("frame"):
        return JsonResponse({"status": "error", "message": "No frame received"}, status=400)
    
    start_time = time.time()
    
    try:
        # Decode the uploaded frame
        file = request.FILES["frame"].read()
        np_arr = np.frombuffer(file, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return JsonResponse({"status": "error", "message": "Failed to decode frame"}, status=400)

        # Find active session
        active_session_id = None
        active_session = None
        for session_id, session_data in active_recognition.items():
            if session_data.get("thread") and session_data["thread"].is_alive():
                if session_data.get("mode") == "prod" or "process" not in session_data:
                    active_session_id = session_id
                    try:
                        active_session = Session.objects.get(id=session_id)
                    except Session.DoesNotExist:
                        pass
                    break

        # ===== OPTIMIZATION 1: Frame Skipping =====
        # Skip 2 out of every 3 frames (process ~33% of frames)
        # This maintains responsiveness while reducing CPU load
        if active_session_id:
            if active_session_id not in FRAME_SKIP_COUNTER:
                FRAME_SKIP_COUNTER[active_session_id] = 0
            
            FRAME_SKIP_COUNTER[active_session_id] += 1
            
            # Queue frame for background processing (don't skip queueing)
            try:
                # Queue the raw uploaded bytes (variable `file`) instead of
                # re-encoding here. The upload already contains JPEG bytes so
                # re-encoding is unnecessary and invokes extra native
                # allocations that can contribute to heap corruption when
                # combined with threaded/native libraries.
                # CRITICAL: Make a copy of bytes to ensure they remain valid
                # after the Django request context ends. The original `file`
                # bytes may reference Django's request buffer which is freed
                # when the request ends, causing memory corruption in background thread.
                if FRAME_SKIP_COUNTER[active_session_id] % PROCESS_EVERY_N_FRAMES == 0:
                    # bytes() creates a deep copy of the data
                    frame_queue.put_nowait(bytes(file))
            except Exception as e:
                print(f"[WARNING] Could not queue frame: {e}")

        # ===== Use get_cached_known_encodings with session scoping =====
        # Avoids database queries - cache for 10 minutes
        cached_data = get_cached_known_encodings(session=active_session)
        known_encodings = cached_data['encodings']
        known_names = cached_data['names']
        
        # ===== Use get_face_encodings from face_utils.py =====
        # This function handles both HOG and DNN detection with optimization
        face_locations, face_encodings = get_face_encodings(
            frame,
            model=os.environ.get('FACE_DETECTION_MODEL', 'hog'),
            scale=SCALE_FACTOR,
            min_size=MIN_FACE_SIZE,
            dnn_net=None  # Could be loaded if needed for production
        )
        
        if not face_locations or not face_encodings:
            elapsed = time.time() - start_time
            return JsonResponse({
                "status": "ok",
                "message": "No faces detected",
                "face_count": 0,
                "queued": bool(active_session_id),
                "processing_ms": round(elapsed * 1000, 1)
            })

        # ===== Use matches_face_encoding from face_utils.py =====
        # This provides consistent matching logic with session awareness
        face_names = []
        face_distances = []
        
        for face_encoding in face_encodings:
            # Use face_utils matching function for consistency with recognition_runner
            name, distance, idx, is_known = matches_face_encoding(
                face_encoding,
                known_encodings,
                known_names,
                unknown_encodings=None,  # No persistent unknown cache in HTTP context
                tolerance=TOLERANCE
            )
            
            face_names.append(name)
            face_distances.append(distance)

        # Build response
        results = [
            {
                "name": name,
                "distance": distance,
                "box": {
                    "top": int(loc[0]),
                    "right": int(loc[1]),
                    "bottom": int(loc[2]),
                    "left": int(loc[3])
                }
            }
            for name, distance, loc in zip(face_names, face_distances, face_locations)
        ]

        elapsed = time.time() - start_time
        return JsonResponse({
            "status": "ok",
            "message": f"Processed {len(face_encodings)} face(s)",
            "face_count": len(face_encodings),
            "queued": bool(active_session_id),
            "results": results,
            "processing_ms": round(elapsed * 1000, 1)  # Show processing time
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)

def index(request):
    """Home page info endpoint"""
    return JsonResponse({
        'title': 'FaceTrack Lite API',
        'message': 'Welcome to FaceTrack Lite: finally, a tool that stares back at you harder than your laptop\'s front camera during an online exam 👁️👁️. Don\'t worry, we only judge a little.',
        'version': '2.0',
        'endpoints': {
            'enroll': '/api/students/enroll/',
            'sessions': '/api/sessions/',
            'recognize': '/recognize/upload_frame/'
        }
    })

@csrf_exempt
def enroll_view(request):
    """Enroll a new student with face images"""
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        face_images = request.FILES.getlist('face_images')
        progress_key = f"enroll_progress_{request.session.session_key}"
        cache.set(progress_key, 0, timeout=600)

        # Validate uploaded images
        if not face_images:
            return JsonResponse({
                'status': 'error',
                'message': 'Please upload at least one image file.',
                'errors': {'face_images': ['At least one image is required']}
            }, status=400)

        if form.is_valid():
            ref_encoding = None
            valid_encodings = []
            total = len(face_images)
            form_errors = []
            
            for idx, image in enumerate(face_images):
                img_bytes = image.read()
                np_arr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                face_locations, encodings = get_face_encodings(img)

                if not encodings:
                    form_errors.append(f"No face detected in image: {image.name}")
                    continue
                elif len(encodings) > 1:
                    form_errors.append(f"Multiple faces detected in image: {image.name}")
                    continue

                encoding = encodings[0]

                if ref_encoding is None:
                    ref_encoding = encoding
                else:
                    matches = face_recognition.compare_faces([ref_encoding], encoding, tolerance=TOLERANCE)
                    if not matches[0]:
                        form_errors.append(f"Face in image {image.name} does not match the first face.")
                        continue

                valid_encodings.append((image.name, encodings[0]))

                # Update progress in cache
                cache.set(progress_key, int((idx + 1) / total * 100), timeout=600)

            # Only save the form if we have valid encodings AND no errors
            if valid_encodings and not form_errors:
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

                cache.set(progress_key, 100, timeout=600)
                return JsonResponse({
                    'status': 'success',
                    'message': f"Student '{student.name}' enrolled successfully with {len(valid_encodings)} encoding(s)",
                    'student': {
                        'id': student.id,
                        'name': student.name,
                        'student_id': student.student_id,
                        'encodings_count': len(valid_encodings)
                    }
                }, status=201)
            else:
                cache.set(progress_key, 100, timeout=600)
                all_errors = form_errors + [str(err) for err in form.errors.values()]
                return JsonResponse({
                    'status': 'error',
                    'message': 'Enrollment failed',
                    'errors': all_errors,
                    'valid_encodings': len(valid_encodings)
                }, status=400)
        else:
            cache.set(progress_key, 100, timeout=600)
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
    else:
        # GET request - return form fields for client
        return JsonResponse({
            'status': 'ok',
            'message': 'POST face images to this endpoint for enrollment',
            'required_fields': {
                'name': 'string (required)',
                'student_id': 'string (required)',
                'class_group': 'integer (optional)',
                'face_images': 'multiple files (required, at least 1)'
            },
            'constraints': {
                'min_images': 1,
                'all_same_person': True,
                'min_face_size': MIN_FACE_SIZE
            }
        })

def enroll_progress(request):
    progress_key = f"enroll_progress_{request.session.session_key}"
    progress = cache.get(progress_key, 0)
    return JsonResponse({'progress': progress})

def enroll_success(request):
    """Deprecated - use API endpoint instead"""
    return JsonResponse({
        'status': 'deprecated',
        'message': 'This endpoint is deprecated. Use POST /api/students/enroll/ instead.',
        'alternative': '/api/students/'
    }, status=410)

@login_required
def create_session_view(request):
    """Create a new recognition session"""
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.status = 'ready'
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f"Session '{session.subject}' created successfully!",
                'session': {
                    'id': session.id,
                    'subject': session.subject,
                    'class_group': session.class_group.id if session.class_group else None,
                    'status': session.status,
                    'created_at': session.created_at.isoformat() if session.created_at else None
                }
            }, status=201)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
    else:
        # GET request - return form schema for client
        return JsonResponse({
            'status': 'ok',
            'message': 'POST JSON data to create a new session',
            'required_fields': {
                'subject': 'string (required)',
                'class_group': 'integer (optional)'
            }
        })

def session_detail(request, session_id):
    """Get detailed information about a session"""
    session = get_object_or_404(Session, id=session_id)
    
    expected_students = session.class_group.students.all() if session.class_group else Student.objects.none()
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [record.student for record in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students])
    
    events = Event.objects.filter(session=session).order_by('-timestamp')[:50]
    
    return JsonResponse({
        'status': 'ok',
        'session': {
            'id': session.id,
            'subject': session.subject,
            'class_group': session.class_group.id if session.class_group else None,
            'status': session.status,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'started_at': session.start_time.isoformat() if session.start_time else None,
            'ended_at': session.end_time.isoformat() if session.end_time else None,
            'created_by': session.created_by.username if session.created_by else None
        },
        'present_students': [
            {
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id
            }
            for student in present_students
        ],
        'absent_students': [
            {
                'id': student.id,
                'name': student.full_name,
                'student_id': student.id
            }
            for student in absent_students
        ],
        'summary': {
            'expected_count': expected_students.count(),
            'present_count': len(present_students),
            'absent_count': len(list(absent_students)),
            'attendance_percentage': round((len(present_students) / expected_students.count() * 100), 2) if expected_students.count() > 0 else 0
        },
        'events': [
            {
                'type': event.event_type,
                'severity': event.severity,
                'message': event.message,
                'timestamp': event.timestamp.isoformat() if event.timestamp else None
            }
            for event in events
        ]
    })

def session_events_partial(request, session_id):
    """Get events for a session"""
    session = get_object_or_404(Session, id=session_id)
    events = Event.objects.filter(session=session).order_by('-timestamp')[:20]
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'events': [
            {
                'type': event.event_type,
                'severity': event.severity,
                'message': event.message,
                'timestamp': event.timestamp.isoformat() if event.timestamp else None
            }
            for event in events
        ]
    })

def session_present_students_partial(request, session_id):
    """Get present students for a session"""
    session = get_object_or_404(Session, id=session_id)
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [r.student for r in present_records]
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'present_students': [
            {
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id
            }
            for student in present_students
        ],
        'count': len(present_students)
    })

def session_absent_students_partial(request, session_id):
    """Get absent students for a session"""
    session = get_object_or_404(Session, id=session_id)
    expected_students = session.class_group.students.all() if session.class_group else []
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [r.student for r in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students]) if expected_students else []
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'absent_students': [
            {
                'id': student.id,
                'name': student.name,
                'student_id': student.student_id
            }
            for student in absent_students
        ],
        'count': len(list(absent_students))
    })

def session_unidentified_faces_partial(request, session_id):
    """Get unidentified faces for a session"""
    from recognition.models import UnidentifiedFace
    
    session = get_object_or_404(Session, id=session_id)
    
    try:
        unidentified_faces = UnidentifiedFace.objects.filter(session=session)
    except:
        unidentified_faces = []
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'unidentified_faces': [
            {
                'image_url': face.image.url if face.image else None,
                'confidence': face.confidence if hasattr(face, 'confidence') else None,
                'timestamp': face.timestamp.isoformat() if hasattr(face, 'timestamp') and face.timestamp else None
            }
            for face in unidentified_faces
        ],
        'count': len(list(unidentified_faces))
    })

def record_event(session, message, event_type='info'):
    Event.objects.create(session=session, message=message, event_type=event_type)

def recognition_progress_partial(request, session_id):
    """Get real-time recognition progress for a session"""
    session = get_object_or_404(Session, id=session_id)
    total_expected = session.class_group.students.count() if session.class_group else 0
    present_count = AttendanceRecord.objects.filter(session=session).count()
    
    try:
        unknown_count = UnidentifiedFace.objects.filter(session=session).count()
    except:
        unknown_count = 0
    
    active_data = active_recognition.get(str(session_id), {})
    is_running = active_data.get("thread") and active_data["thread"].is_alive()
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'progress': {
            'present_count': present_count,
            'total_expected': total_expected,
            'unknown_count': unknown_count,
            'attendance_percentage': round((present_count / total_expected * 100), 2) if total_expected > 0 else 0,
            'is_running': is_running,
            'mode': active_data.get('mode', 'none')
        }
    })

def end_session_view(request, session_id):
    """End a recognition session"""
    session = get_object_or_404(Session, id=session_id)

    # Stop running thread/process if exists
    active = active_recognition.get(str(session_id))
    if active:
        if active.get("stop_flag"):
            active["stop_flag"].set()

        # Also terminate subprocess if running in dev mode
        if "process" in active and active["process"]:
            active["process"].terminate()

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
            message="Session ended via API"
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Session '{session.subject}' ended successfully",
            'session': {
                'id': session.id,
                'subject': session.subject,
                'status': session.status,
                'ended_at': session.end_time.isoformat() if session.end_time else None
            }
        })
    else:
        return JsonResponse({
            'status': 'info',
            'message': f"Session '{session.subject}' was already ended",
            'session': {
                'id': session.id,
                'subject': session.subject,
                'status': session.status
            }
        })

def sessions_list(request):
    """Get all sessions with their status"""
    sessions = Session.objects.all().order_by('-created_at')
    
    sessions_data = []
    for session in sessions:
        active_data = active_recognition.get(str(session.id), {})
        is_running = active_data.get("thread") and active_data["thread"].is_alive()
        
        present_count = AttendanceRecord.objects.filter(session=session).count()
        expected_count = session.class_group.students.count() if session.class_group else 0
        
        sessions_data.append({
            'id': session.id,
            'subject': session.subject,
            'class_group': session.class_group.name if session.class_group else None,
            'status': session.status,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'ended_at': session.end_time.isoformat() if session.end_time else None,
            'created_by': session.created_by.username if session.created_by else None,
            'recognition': {
                'is_running': is_running,
                'mode': active_data.get('mode', 'none'),
                'present_count': present_count,
                'expected_count': expected_count,
                'attendance_percentage': round((present_count / expected_count * 100), 2) if expected_count > 0 else 0
            }
        })
    
    return JsonResponse({
        'status': 'ok',
        'count': len(sessions_data),
        'sessions': sessions_data
    })

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