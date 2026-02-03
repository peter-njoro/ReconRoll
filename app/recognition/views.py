import os
import cv2
import uuid
import json
import threading
import numpy as np
import face_recognition
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
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

# Import face recognition constants from settings
KNOWN_FACES_DIR = settings.FACE_RECOGNITION_DIR
ID_CARD_DIR = settings.ID_CARD_DIR
SCALE_FACTOR = settings.FACE_SCALE_FACTOR
TOLERANCE = settings.FACE_TOLERANCE
TARGET = settings.FACE_TARGET
TARGET_FPS = settings.TARGET_FPS
PROCESS_EVERY_N_FRAMES = settings.PROCESS_EVERY_N_FRAMES
CARD_DISPLAY_FRAMES = settings.CARD_DISPLAY_FRAMES
MIN_FACE_SIZE = settings.MIN_FACE_SIZE
ENCODING_CACHE_KEY = settings.ENCODING_CACHE_KEY
ENCODING_CACHE_TTL = settings.ENCODING_CACHE_TTL

# ===== PERFORMANCE OPTIMIZATION =====
# Runtime tracking variable (not a constant)
FRAME_SKIP_COUNTER = {}  # Track frame count per session for skipping


def isoformat_or_none(dt):
    """Helper function to convert datetime to ISO format or return None"""
    return dt.isoformat() if dt is not None else None

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

@api_view(['GET'])
def index(request):
    """Home page info endpoint"""
    return Response({
        'title': 'FaceTrack Lite API',
        'message': 'Welcome to FaceTrack Lite: finally, a tool that stares back at you harder than your laptop\'s front camera during an online exam 👁️👁️. Don\'t worry, we only judge a little.',
        'version': '2.0',
        'endpoints': {
            'enroll': '/api/enroll/',
            'sessions': '/api/sessions/'
        }
    })

@csrf_exempt
def enroll_view(request):
    """Enroll a new student with face images"""
    if request.method == 'POST':
        # Handle both form field names and API field names for compatibility
        post_data = request.POST.copy()
        
        # Map 'name' to 'full_name' if present
        if 'name' in post_data and 'full_name' not in post_data:
            post_data['full_name'] = post_data.pop('name')
        
        # Map 'student_id' to 'registration_number' if present
        if 'student_id' in post_data and 'registration_number' not in post_data:
            post_data['registration_number'] = post_data.pop('student_id')
        
        form = StudentForm(post_data, request.FILES)
        face_images = request.FILES.getlist('face_images')
        progress_key = f"enroll_progress_{request.session.session_key}"
        cache.set(progress_key, 0, timeout=600)

        # Validate uploaded images
        if not face_images:
            return JsonResponse({
                'status': 'error',
                'message': 'Please upload at least one image file.',
                'errors': ['At least one face image is required']
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
                    form_errors.append(f"❌ {image.name}: No face detected. Make sure the image clearly shows a face.")
                    continue
                elif len(encodings) > 1:
                    form_errors.append(f"❌ {image.name}: Multiple faces detected. Upload images with only one person per image.")
                    continue

                encoding = encodings[0]

                if ref_encoding is None:
                    ref_encoding = encoding
                else:
                    matches = face_recognition.compare_faces([ref_encoding], encoding, tolerance=TOLERANCE)
                    if not matches[0]:
                        form_errors.append(f"❌ {image.name}: Face does not match the first image. Make sure all images are of the same person.")
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
                    'message': f"Student '{student.full_name}' enrolled successfully with {len(valid_encodings)} encoding(s)",
                    'student': {
                        'id': student.id,
                        'name': student.full_name,
                        'student_id': student.registration_number,
                        'encodings_count': len(valid_encodings)
                    }
                }, status=201)
            else:
                cache.set(progress_key, 100, timeout=600)
                all_errors = form_errors + [str(err) for err in form.errors.values()]
                return JsonResponse({
                    'status': 'error',
                    'message': 'Enrollment failed - please check the errors below',
                    'errors': all_errors,
                    'valid_encodings': len(valid_encodings)
                }, status=400)
        else:
            cache.set(progress_key, 100, timeout=600)
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data - please check the required fields',
                'errors': [f"{field}: {', '.join(msgs) if isinstance(msgs, list) else msgs}" for field, msgs in form.errors.items()]
            }, status=400)
    else:
        # GET request - return form fields for client
        return JsonResponse({
            'status': 'ok',
            'message': 'POST face images to this endpoint for enrollment',
            'required_fields': {
                'full_name': 'string (required)',
                'registration_number': 'string (required)',
                'email': 'string (optional)',
                'course': 'string (optional)',
                'year_of_study': 'integer (optional, default: 1)',
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
@csrf_exempt
def create_session_view(request):
    """Create a new recognition session"""
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.status = 'ongoing'  # Only valid values: 'ongoing' or 'ended'
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

def sessions_list(request):
    """Get all sessions with their status"""
    sessions = Session.objects.all().order_by('-created_at')
    
    sessions_data = []
    for session in sessions:
        active_data = active_recognition.get(str(session.id), {})
        is_running = active_data.get("thread") and active_data["thread"].is_alive()

        # Per-session counts for attendance summary
        expected_count = session.class_group.students.count() if session.class_group else 0
        present_count = AttendanceRecord.objects.filter(session=session).count()
        attendance_percentage = round((present_count / expected_count * 100), 2) if expected_count > 0 else 0

        sessions_data.append({
            'id': session.id,
            'subject': session.subject,
            'class_group': session.class_group.name if session.class_group else None,
            'status': session.status,
            'created_at': isoformat_or_none(session.created_at),
            'started_at': isoformat_or_none(session.start_time),
            'ended_at': isoformat_or_none(session.end_time),
            'created_by': session.created_by.username if session.created_by else None,
            'recognition': {
                'is_running': bool(is_running),
                'mode': active_data.get('mode', 'none'),
                'present_count': present_count,
                'expected_count': expected_count,
                'attendance_percentage': attendance_percentage
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


def session_detail(request, session_id):
    """Get detailed information about a session"""
    session = get_object_or_404(Session, id=session_id)
    
    expected_students = session.class_group.students.all() if session.class_group else Student.objects.none()
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [record.student for record in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students])

    # Load events for this session to include in the response
    events = Event.objects.filter(session=session).order_by('-timestamp')[:50]
    
    return JsonResponse({
        'status': 'ok',
        'session': {
            'id': session.id,
            'subject': session.subject,
            'class_group': session.class_group.id if session.class_group else None,
            'status': session.status,
            'created_at': isoformat_or_none(session.created_at),
            'started_at': isoformat_or_none(session.start_time),
            'ended_at': isoformat_or_none(session.end_time),
            'created_by': session.created_by.username if session.created_by else None
        },
        'present_students': [
            {
                'student_id': student.id,
                'name': student.full_name,
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

@require_http_methods(["POST"])
def start_session_view(request, session_id):
    """
    Start the recognition thread for a session.

    Mirrors the logic in SessionViewSet.start() so that the traditional
    Django URL can be called from the React frontend without going through
    the DRF router.

    Query params:
        dev_mode  – 'true' | 'false'  (default 'false')
    """
    session = get_object_or_404(Session, id=session_id)
    dev_mode = request.GET.get('dev_mode', 'false').lower() == 'true'

    # ------------------------------------------------------------------
    # 1. Guard: thread already running for this session
    # ------------------------------------------------------------------
    if str(session_id) in active_recognition:
        existing = active_recognition[str(session_id)]
        if existing.get("thread") and existing["thread"].is_alive():
            return JsonResponse({
                'status': 'error',
                'message': f'Recognition is already running for session: {session.subject}'
            }, status=400)

    # ------------------------------------------------------------------
    # 2. Guard: session already ended
    # ------------------------------------------------------------------
    if session.status == 'ended':
        return JsonResponse({
            'status': 'error',
            'message': 'Cannot start session – it has already ended'
        }, status=400)

    # ------------------------------------------------------------------
    # 3. Guard: class group has no students (prod mode only)
    # ------------------------------------------------------------------
    if not dev_mode and session.class_group and session.class_group.students.count() == 0:
        return JsonResponse({
            'status': 'error',
            'message': 'Class group has no students. Please add students first.'
        }, status=400)

    # ------------------------------------------------------------------
    # 4. Guard: no face encodings enrolled yet (prod mode only)
    # ------------------------------------------------------------------
    if not dev_mode and not FaceEncoding.objects.exists():
        return JsonResponse({
            'status': 'error',
            'message': 'No face encodings found in database. Please enroll students first.'
        }, status=400)

    # ------------------------------------------------------------------
    # 5. Spawn the recognition thread
    # ------------------------------------------------------------------
    stop_flag = threading.Event()

    try:
        t = threading.Thread(
            target=run_recognition,
            args=(str(session_id),),
            kwargs={
                'dev_mode': dev_mode,
                'stop_flag': stop_flag,
            },
            name=f"RecognitionThread-{session_id}-{'dev' if dev_mode else 'prod'}",
        )
        t.daemon = True
        t.start()

        # Register in the global dict so stop / status can find it later
        active_recognition[str(session_id)] = {
            "thread": t,
            "stop_flag": stop_flag,
            "started_at": timezone.now(),
            "mode": "dev" if dev_mode else "prod",
        }

        # ------------------------------------------------------------------
        # 6. Persist status change
        # ------------------------------------------------------------------
        session.status = 'ongoing'
        session.start_time = timezone.now()
        if request.user.is_authenticated:
            session.created_by = request.user
        session.save()

        Event.objects.create(
            session=session,
            event_type='session_started',
            severity='info',
            message=f"Session started in {'DEV' if dev_mode else 'PRODUCTION'} mode"
        )

        return JsonResponse({
            'status': 'started',
            'session_id': str(session_id),
            'subject': session.subject,
            'mode': 'dev' if dev_mode else 'prod',
            'message': f"Recognition started in {'DEV' if dev_mode else 'PRODUCTION'} mode"
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to start recognition: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def end_session_view(request, session_id):
    """
    End a recognition session

    URL: /recognition/session/<uuid:session_id>/stop/
    Method: POST

    Returns JSON response with session status
    """
    session = get_object_or_404(Session, id=session_id)

    # Stop running thread/process if exists
    active = active_recognition.get(str(session_id))
    if active:
        if active.get("stop_flag"):
            active["stop_flag"].set()

        # Also terminate subprocess if running in dev mode
        if "process" in active and active["process"]:
            try:
                active["process"].terminate()
            except Exception:
                pass

        # Clean up
        active_recognition.pop(str(session_id), None)

    if session.status != 'ended':
        session.status = 'ended'
        session.end_time = timezone.now()
        session.save()

        # Log an event for session end (fail silently if Event creation fails)
        try:
            Event.objects.create(
                session=session,
                event_type='session_ended',
                severity='info',
                message=f"Session '{session.subject}' ended via traditional view"
            )
        except Exception:
            pass

        return JsonResponse({
            'status': 'success',
            'message': f"Session '{session.subject}' ended successfully",
            'session': {
                'id': str(session.id),
                'subject': session.subject,
                'status': session.status,
                'ended_at': isoformat_or_none(session.end_time)
            }
        })
    else:
        return JsonResponse({
            'status': 'info',
            'message': f"Session '{session.subject}' was already ended",
            'session': {
                'id': str(session.id),
                'subject': session.subject,
                'status': session.status,
                'ended_at': isoformat_or_none(session.end_time)
            }
        })


@require_http_methods(["POST"])
def stop_all_sessions_view(request):
    """
    Stop all active recognition sessions (emergency stop)

    URL: /recognition/session/stop-all/
    Method: POST

    Returns JSON response with count of stopped sessions
    """
    stopped_count = 0
    stopped_sessions = []

    # Iterate through all active recognition sessions
    for session_id, session_data in list(active_recognition.items()):
        try:
            session = Session.objects.get(id=session_id)

            # Stop the thread/process
            if session_data.get("stop_flag"):
                session_data["stop_flag"].set()

            # Terminate subprocess if in dev mode
            if "process" in session_data and session_data["process"]:
                try:
                    session_data["process"].terminate()
                except Exception:
                    pass

            # Update session status if still ongoing
            if session.status == 'ongoing':
                session.status = 'ended'
                session.end_time = timezone.now()
                session.save()

                # Log event
                try:
                    Event.objects.create(
                        session=session,
                        event_type='session_ended',
                        severity='warning',
                        message="Session stopped by emergency stop-all command"
                    )
                except Exception:
                    pass

                stopped_sessions.append({
                    'id': str(session.id),
                    'subject': session.subject
                })
                stopped_count += 1

        except Session.DoesNotExist:
            pass

        # Clean up from active_recognition dict
        active_recognition.pop(session_id, None)

    return JsonResponse({
        'status': 'success',
        'stopped_count': stopped_count,
        'message': f"Successfully stopped {stopped_count} session(s)",
        'stopped_sessions': stopped_sessions
    })


@require_http_methods(["POST", "PATCH", "PUT"])
def update_session_view(request, session_id):
    """
    Update a session (full or partial update)

    URL: /recognition/session/<uuid:session_id>/update/
    Method: POST, PATCH, or PUT

    Accepts JSON body with fields to update:
    - subject: string
    - class_group: UUID or null
    - status: 'scheduled', 'ongoing', or 'ended'

    Returns JSON response with updated session
    """
    session = get_object_or_404(Session, id=session_id)

    try:
        # Parse JSON body
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        # Validate and update allowed fields
        updated_fields = []

        if 'subject' in data:
            session.subject = data['subject']
            updated_fields.append('subject')

        if 'class_group' in data:
            if data['class_group']:
                from .models import ClassGroup
                try:
                    class_group = ClassGroup.objects.get(id=data['class_group'])
                    session.class_group = class_group
                    updated_fields.append('class_group')
                except ClassGroup.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Class group with id {data['class_group']} not found"
                    }, status=400)
            else:
                session.class_group = None
                updated_fields.append('class_group')

        if 'status' in data:
            valid_statuses = ['scheduled', 'ongoing', 'ended']
            if data['status'] in valid_statuses:
                old_status = session.status
                session.status = data['status']
                updated_fields.append('status')

                # If manually ending session, set end_time
                if data['status'] == 'ended' and old_status != 'ended':
                    session.end_time = timezone.now()

                    # Also stop recognition if running
                    active = active_recognition.get(str(session_id))
                    if active:
                        if active.get("stop_flag"):
                            active["stop_flag"].set()
                        active_recognition.pop(str(session_id), None)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Invalid status. Must be one of: {valid_statuses}"
                }, status=400)

        # Save changes
        if updated_fields:
            session.save()

            # Log update event
            try:
                Event.objects.create(
                    session=session,
                    event_type='session_updated',
                    severity='info',
                    message=f"Session updated: {', '.join(updated_fields)}"
                )
            except Exception:
                pass

            return JsonResponse({
                'status': 'success',
                'message': f"Session updated successfully",
                'updated_fields': updated_fields,
                'session': {
                    'id': str(session.id),
                    'subject': session.subject,
                    'class_group': str(session.class_group.id) if session.class_group else None,
                    'class_group_name': session.class_group.name if session.class_group else None,
                    'status': session.status,
                    'created_at': isoformat_or_none(session.created_at),
                    'start_time': isoformat_or_none(session.start_time),
                    'end_time': isoformat_or_none(session.end_time),
                }
            })
        else:
            return JsonResponse({
                'status': 'info',
                'message': 'No fields to update',
                'session': {
                    'id': str(session.id),
                    'subject': session.subject,
                    'status': session.status,
                }
            })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error updating session: {str(e)}'
        }, status=500)

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
    expected_students = session.class_group.students.all() if session.class_group else Student.objects.none()
    present_records = AttendanceRecord.objects.filter(session=session).select_related('student')
    present_students = [r.student for r in present_records]
    absent_students = expected_students.exclude(id__in=[s.id for s in present_students])
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'absent_students': [
            {
                'id': student.id,
                'name': student.full_name,
                'student_id': student.id
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
    
    # Build a safe list of unidentified faces with robust attribute checks
    faces_list = []
    for face in unidentified_faces:
        image_url = None

        # Preferred: Django FileField named 'image'
        if hasattr(face, 'image'):
            try:
                img_field = getattr(face, 'image')
                if img_field:
                    try:
                        image_url = img_field.url
                    except Exception:
                        # Fallback to using stored name/path if url() not available
                        img_name = getattr(img_field, 'name', None)
                        if img_name:
                            image_url = os.path.join(settings.MEDIA_URL, img_name)
            except Exception:
                image_url = None

        # Alternate attribute names that may exist on the model
        elif hasattr(face, 'image_url'):
            image_url = getattr(face, 'image_url', None)
        elif hasattr(face, 'file_path'):
            file_path = getattr(face, 'file_path', None)
            if file_path:
                image_url = os.path.join(settings.MEDIA_URL, file_path)

        # Confidence and timestamp with safe getattr usage
        confidence = getattr(face, 'confidence', None)
        ts = getattr(face, 'timestamp', None)
        timestamp = ts.isoformat() if ts else None

        faces_list.append({
            'image_url': image_url,
            'confidence': confidence,
            'timestamp': timestamp
        })

    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'unidentified_faces': faces_list,
        'count': len(faces_list)
    })

def record_event(session, message, event_type='info'):
    Event.objects.create(session=session, message=message, event_type=event_type)

def recognition_progress_partial(request, session_id):
    """Get real-time recognition progress for a session"""
    session = get_object_or_404(Session, id=session_id)
    total_expected = session.class_group.students.count() if session.class_group else 0
    present_count = AttendanceRecord.objects.filter(session=session).count()
    
    # Import UnidentifiedFace here to avoid NameError when the model is not in global scope
    try:
        from recognition.models import UnidentifiedFace
        unknown_count = UnidentifiedFace.objects.filter(session=session).count()
    except Exception:
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
