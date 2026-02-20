import os
import cv2
import io
import uuid
import json
import hashlib
import threading
import numpy as np
import face_recognition
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.db import ProgrammingError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from recognition.forms import PersonForm, SessionForm
from recognition.face_utils import (
    get_face_encodings, 
    matches_face_encoding
)
from recognition.models import (
    FaceEncoding,
    Session,
    AttendanceSummary,
    Event,
    Person,
    UnidentifiedFace,
    Roster,
    RosterAttendance,
)
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


def split_full_name(full_name):
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def get_present_records(session):
    """Get present records for a session using its Roster attendance"""
    if not session.roster:
        # Fallback to AttendanceSummary if no roster is set
        return AttendanceSummary.objects.filter(
            session=session,
            status__in=['present', 'late']
        )
    
    # Get records from the session's roster attendance
    return RosterAttendance.objects.filter(
        roster=session.roster,
        session=session,
        status__in=['present', 'late']
    ).select_related('person')



def get_expected_count(session):
    expected_links = session.expected_persons.count()
    if expected_links > 0:
        return expected_links
    return session.expected_count or 0


def decode_face_encoding(encoding_obj):
    if encoding_obj.encoding:
        try:
            return np.load(io.BytesIO(encoding_obj.encoding), allow_pickle=False)
        except Exception:
            pass

    if encoding_obj.image_path:
        for base_dir in (settings.MEDIA_ROOT, settings.BASE_DIR):
            candidate = os.path.join(str(base_dir), encoding_obj.image_path)
            if os.path.exists(candidate):
                try:
                    return np.load(candidate, allow_pickle=False)
                except Exception:
                    pass

    return None


def load_known_encodings(session=None):
    """
    Load known face encodings from the database.

    If a session is provided, scope to expected people when possible.
    """
    known_encodings = []
    known_names = []

    if session:
        people = Person.objects.filter(
            expected_sessions__session=session
        ).prefetch_related('face_encodings')
        if not people.exists():
            people = Person.objects.all().prefetch_related('face_encodings')
    else:
        people = Person.objects.all().prefetch_related('face_encodings')

    for person in people:
        for encoding_obj in person.face_encodings.all():
            encoding = decode_face_encoding(encoding_obj)
            if encoding is None:
                continue
            known_encodings.append(encoding)
            known_names.append(person.get_full_name())

    return np.array(known_encodings) if known_encodings else np.array([]), known_names

def get_cached_known_encodings(session=None, force_reload=False):
    """
    Get known face encodings from cache, reload from DB if expired.
    This avoids database queries on every frame upload.
    
    Args:
        session: Session object (optional). If provided, scopes encodings to expected people.
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
    
    # Cache miss: reload from database
    known_encodings, known_names = load_known_encodings(session=session)
    
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
def get_people_with_encodings(request):
    """Get all people who have face encodings in the database"""
    people = Person.objects.filter(
        face_encodings__isnull=False
    ).distinct().order_by('first_name', 'last_name')
    
    people_data = [
        {
            'id': person.id,
            'name': person.get_full_name(),
            'identification_number': person.identification_number,
            'email': person.email,
            'phone': person.phone,
            'status': person.status,
            'encoding_count': person.face_encodings.count()
        }
        for person in people
    ]
    
    return Response({
        'status': 'ok',
        'count': len(people_data),
        'people': people_data
    })


@api_view(['GET'])
def get_person_detail(request, person_id):
    """Get detailed information about a specific person"""
    person = get_object_or_404(Person, id=person_id)
    
    return Response({
        'status': 'ok',
        'person': {
            'id': person.id,
            'first_name': person.first_name,
            'last_name': person.last_name,
            'full_name': person.get_full_name(),
            'identification_number': person.identification_number,
            'email': person.email,
            'phone': person.phone,
            'status': person.status,
            'date_of_birth': person.date_of_birth.isoformat() if person.date_of_birth else None,
            'notes': person.notes,
            'encoding_count': person.face_encodings.count(),
            'created_at': isoformat_or_none(person.created_at),
            'updated_at': isoformat_or_none(person.updated_at)
        }
    })


@api_view(['GET'])
def list_rosters(request):
    """Get all rosters with their people count"""
    try:
        rosters = Roster.objects.all().order_by('-created_at')
        
        roster_data = [
            {
                'id': str(roster.id),
                'name': roster.name,
                'description': roster.description,
                'people_count': roster.people.count(),
                'created_at': isoformat_or_none(roster.created_at),
                'created_by': roster.created_by.username if roster.created_by else None
            }
            for roster in rosters
        ]
        
        return Response({
            'status': 'ok',
            'count': len(roster_data),
            'rosters': roster_data
        })
    except ProgrammingError:
        # Table doesn't exist yet - migrations haven't been run
        return Response({
            'status': 'ok',
            'count': 0,
            'rosters': [],
            'message': 'rosters table not yet initialized - run migrations'
        })


@csrf_exempt
@api_view(['POST'])
def create_roster(request):
    """
    Create a new roster with a set of people.
    
    Request body:
    {
        'name': 'string (required)',
        'description': 'string (optional)',
        'person_ids': ['uuid1', 'uuid2', ...] (optional)
    }
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            'status': 'error',
            'message': 'Request body is not valid JSON'
        }, status=400)
    
    try:
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        person_ids = data.get('person_ids', [])
        
        if not name:
            return JsonResponse({
                'status': 'error',
                'message': 'roster name is required'
            }, status=400)
        
        # Check if roster with this name already exists
        if Roster.objects.filter(name=name).exists():
            return JsonResponse({
                'status': 'error',
                'message': f'Roster with name "{name}" already exists'
            }, status=400)
        
        if not isinstance(person_ids, list):
            return JsonResponse({
                'status': 'error',
                'message': 'person_ids must be a list'
            }, status=400)
        
        # Validate all person IDs exist
        unique_ids = list(dict.fromkeys(person_ids))
        people = Person.objects.filter(id__in=unique_ids)
        
        if len(unique_ids) != people.count():
            return JsonResponse({
                'status': 'error',
                'message': 'One or more person_ids were not found'
            }, status=400)
        
        # Create roster
        roster = Roster.objects.create(
            name=name,
            description=description,
            created_by=request.user if request.user.is_authenticated else None
        )
        
        # Add people to roster
        if people:
            roster.people.set(people)
        
        return Response({
            'status': 'success',
            'message': f'Roster "{name}" created successfully',
            'roster': {
                'id': str(roster.id),
                'name': roster.name,
                'description': roster.description,
                'people_count': roster.people.count(),
                'created_at': isoformat_or_none(roster.created_at)
            }
        }, status=201)
    except ProgrammingError:
        return JsonResponse({
            'status': 'error',
            'message': 'Rosters table not initialized - run migrations first'
        }, status=500)


@api_view(['GET'])
def get_roster_detail(request, roster_id):
    """Get detailed information about a roster including its people"""
    try:
        roster = get_object_or_404(Roster, id=roster_id)
    except ProgrammingError:
        return Response({
            'status': 'error',
            'message': 'Rosters table not initialized - run migrations first'
        }, status=500)
    
    people = roster.people.all()
    
    return Response({
        'status': 'ok',
        'roster': {
            'id': str(roster.id),
            'name': roster.name,
            'description': roster.description,
            'created_at': isoformat_or_none(roster.created_at),
            'created_by': roster.created_by.username if roster.created_by else None,
            'people_count': people.count()
        },
        'people': [
            {
                'id': str(person.id),
                'name': person.get_full_name(),
                'identification_number': person.identification_number,
                'email': person.email,
                'status': person.status
            }
            for person in people
        ]
    })


@csrf_exempt
@api_view(['POST', 'PUT'])
def update_roster(request, roster_id):
    """
    Update an existing roster.
    
    Request body:
    {
        'name': 'string (optional)',
        'description': 'string (optional)',
        'person_ids': ['uuid1', 'uuid2', ...] (optional),
        'replace_people': true/false (default: true - replace all, false - merge)
    }
    """
    try:
        roster = get_object_or_404(Roster, id=roster_id)
        
        data = json.loads(request.body)
        
        # Update name if provided
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return JsonResponse({
                    'status': 'error',
                    'message': 'name cannot be empty'
                }, status=400)
            
            # Check if another roster with this name exists
            if Roster.objects.filter(name=name).exclude(id=roster_id).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f'Roster with name "{name}" already exists'
                }, status=400)
            
            roster.name = name
        
        # Update description if provided
        if 'description' in data:
            roster.description = data['description']
        
        # Update people if provided
        if 'person_ids' in data:
            person_ids = data['person_ids']
            if not isinstance(person_ids, list):
                return JsonResponse({
                    'status': 'error',
                    'message': 'person_ids must be a list'
                }, status=400)
            
            unique_ids = list(dict.fromkeys(person_ids))
            people = Person.objects.filter(id__in=unique_ids)
            
            if len(unique_ids) != people.count():
                return JsonResponse({
                    'status': 'error',
                    'message': 'One or more person_ids were not found'
                }, status=400)
            
            replace_people = data.get('replace_people', True)
            
            if replace_people:
                roster.people.set(people)
            else:
                roster.people.add(*people)
        
        roster.save()
        
        return Response({
            'status': 'success',
            'message': f'Roster "{roster.name}" updated successfully',
            'roster': {
                'id': str(roster.id),
                'name': roster.name,
                'description': roster.description,
                'people_count': roster.people.count(),
                'updated_at': isoformat_or_none(roster.updated_at)
            }
        })
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            'status': 'error',
            'message': 'Request body is not valid JSON'
        }, status=400)
    except ProgrammingError:
        return JsonResponse({
            'status': 'error',
            'message': 'Rosters table not initialized - run migrations first'
        }, status=500)


@api_view(['DELETE'])
def delete_roster(request, roster_id):
    """Delete a roster"""
    try:
        roster = get_object_or_404(Roster, id=roster_id)
        roster_name = roster.name
        roster.delete()
        
        return Response({
            'status': 'success',
            'message': f'Roster "{roster_name}" deleted successfully'
        })
    except ProgrammingError:
        return Response({
            'status': 'error',
            'message': 'Rosters table not initialized - run migrations first'
        }, status=500)



@api_view(['GET'])
def index(request):
    """Home page info endpoint"""
    return Response({
        'title': 'FaceTrack Lite API',
        'message': 'Welcome to FaceTrack Lite: a system that recognizes faces and keeps sessions organized.',
        'version': '2.0',
        'endpoints': {
            'enroll': '/api/enroll/',
            'sessions': '/api/sessions/'
        }
    })

@csrf_exempt
def enroll_view(request):
    """Enroll a new person with face images"""
    if request.method == 'POST':
        # Handle both form field names and API field names for compatibility
        post_data = request.POST.copy()
        
        # Map 'name' to 'full_name' if present
        if 'name' in post_data and 'full_name' not in post_data:
            post_data['full_name'] = post_data.pop('name')

        # Map 'full_name' to first/last name if present
        if 'full_name' in post_data and ('first_name' not in post_data or 'last_name' not in post_data):
            first_name, last_name = split_full_name(post_data.get('full_name', ''))
            post_data.setdefault('first_name', first_name)
            post_data.setdefault('last_name', last_name)
            post_data.pop('full_name', None)
        
        # Map legacy identifiers to identification_number
        if 'registration_number' in post_data and 'identification_number' not in post_data:
            post_data['identification_number'] = post_data.pop('registration_number')
        
        form = PersonForm(post_data, request.FILES)
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

                valid_encodings.append((image.name, encodings[0], img_bytes))

                # Update progress in cache
                cache.set(progress_key, int((idx + 1) / total * 100), timeout=600)

            # Only save the form if we have valid encodings AND no errors
            if valid_encodings and not form_errors:
                person = form.save()
                for idx, (image_name, encoding, image_bytes) in enumerate(valid_encodings):
                    ext = os.path.splitext(image_name)[1] or '.jpg'
                    image_filename = f"{uuid.uuid4()}{ext}"
                    relative_image_path = os.path.join('recognition', 'uploads', 'faces', image_filename)
                    absolute_image_path = os.path.join(str(settings.MEDIA_ROOT), relative_image_path)
                    os.makedirs(os.path.dirname(absolute_image_path), exist_ok=True)

                    with open(absolute_image_path, 'wb') as image_file:
                        image_file.write(image_bytes)

                    encoding_buffer = io.BytesIO()
                    np.save(encoding_buffer, encoding)
                    encoding_bytes = encoding_buffer.getvalue()
                    image_hash = hashlib.sha256(image_bytes).hexdigest()

                    FaceEncoding.objects.create(
                        person=person,
                        encoding=encoding_bytes,
                        image_path=relative_image_path,
                        image_hash=image_hash,
                        is_primary=(idx == 0)
                    )

                cache.set(progress_key, 100, timeout=600)
                return JsonResponse({
                    'status': 'success',
                    'message': f"Person '{person.get_full_name()}' enrolled successfully with {len(valid_encodings)} encoding(s)",
                    'person': {
                        'id': person.id,
                        'name': person.get_full_name(),
                        'identification_number': person.identification_number,
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
                'first_name': 'string (required)',
                'last_name': 'string (required)',
                'identification_number': 'string (required)',
                'email': 'string (optional)',
                'phone': 'string (optional)',
                'date_of_birth': 'date (optional)',
                'status': 'string (optional, default: active)',
                'notes': 'string (optional)',
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
        'message': 'This endpoint is deprecated. Use POST /api/people/enroll/ instead.',
        'alternative': '/api/people/'
    }, status=410)

@login_required
@csrf_exempt
def create_session_view(request):
    """Create a new recognition session"""
    if request.method == 'POST':
        # axios (and every other JSON client) sends Content-Type:
        # application/json.  Django only populates request.POST for
        # application/x-www-form-urlencoded bodies, so request.POST
        # is an empty QueryDict here.  Parse the raw body instead.
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Request body is not valid JSON'
            }, status=400)

        if 'subject' in data and 'name' not in data:
            data['name'] = data.pop('subject')

        form = SessionForm(data)
        if form.is_valid():
            session = form.save(commit=False)
            session.created_by = request.user
            session.save()
            
            # If a roster was selected, populate expected_persons from roster
            if session.roster:
                # Clear any existing expected persons
                SessionExpectedPerson.objects.filter(session=session).delete()
                
                # Add all people from the roster as expected persons
                for person in session.roster.people.all():
                    SessionExpectedPerson.objects.create(session=session, person=person)

            return JsonResponse({
                'status': 'success',
                'message': f"Session '{session.name}' created successfully!",
                'session': {
                    'id': str(session.id),
                    'name': session.name,
                    'description': session.description,
                    'roster_id': str(session.roster.id) if session.roster else None,
                    'roster_name': session.roster.name if session.roster else None,
                    'session_type': session.session_type,
                    'expected_count': get_expected_count(session),
                    'status': session.status,
                    'created_at': isoformat_or_none(session.created_at),
                    'start_time': isoformat_or_none(session.start_time),
                    'end_time': isoformat_or_none(session.end_time)
                }
            }, status=201)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid form data',
                'errors': form.errors
            }, status=400)
    else:
        # GET – return the expected shape so clients know what to send
        try:
            available_rosters = list(Roster.objects.all().values('id', 'name'))
        except ProgrammingError:
            # Table doesn't exist yet - migrations haven't been run
            available_rosters = []
        
        return JsonResponse({
            'status': 'ok',
            'message': 'POST JSON data to create a new session',
            'required_fields': {
                'name': 'string (required)',
                'description': 'string (optional)',
                'roster': 'uuid (optional) - select a roster of expected people',
                'session_type': 'string (optional, deprecated)',
                'start_time': 'datetime (required)',
                'end_time': 'datetime (optional)',
                'expected_count': 'integer (optional)',
                'status': 'scheduled | in_progress | completed | cancelled (optional)'
            },
            'available_rosters': available_rosters
        })

def sessions_list(request):
    """Get all sessions with their status"""
    sessions = Session.objects.all().order_by('-created_at')
    
    sessions_data = []
    for session in sessions:
        active_data = active_recognition.get(str(session.id), {})
        is_running = active_data.get("thread") and active_data["thread"].is_alive()

        # Per-session counts for attendance summary
        expected_count = get_expected_count(session)
        present_count = get_present_records(session).count()
        attendance_percentage = round((present_count / expected_count * 100), 2) if expected_count > 0 else 0

        sessions_data.append({
            'id': session.id,
            'name': session.name,
            'description': session.description,
            'roster_id': str(session.roster.id) if session.roster else None,
            'roster_name': session.roster.name if session.roster else None,
            'session_type': session.session_type,
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
    
    expected_people = Person.objects.filter(
        expected_sessions__session=session
    )
    present_records = get_present_records(session).select_related('person')
    present_people = [record.person for record in present_records]
    absent_people = expected_people.exclude(id__in=[p.id for p in present_people])
    expected_count = get_expected_count(session)
    present_count = len(present_people)
    absent_count = max(expected_count - present_count, 0)

    # Load events for this session to include in the response
    events = Event.objects.filter(session=session).order_by('-timestamp')[:50]
    
    return JsonResponse({
        'status': 'ok',
        'session': {
            'id': session.id,
            'name': session.name,
            'description': session.description,
            'roster_id': str(session.roster.id) if session.roster else None,
            'roster_name': session.roster.name if session.roster else None,
            'session_type': session.session_type,
            'expected_count': expected_count,
            'status': session.status,
            'created_at': isoformat_or_none(session.created_at),
            'started_at': isoformat_or_none(session.start_time),
            'ended_at': isoformat_or_none(session.end_time),
            'created_by': session.created_by.username if session.created_by else None
        },
        'present_people': [
            {
                'id': person.id,
                'name': person.get_full_name(),
                'identification_number': person.identification_number
            }
            for person in present_people
        ],
        'absent_people': [
            {
                'id': person.id,
                'name': person.get_full_name(),
                'identification_number': person.identification_number
            }
            for person in absent_people
        ],
        'summary': {
            'expected_count': expected_count,
            'present_count': present_count,
            'absent_count': absent_count,
            'attendance_percentage': round((present_count / expected_count * 100), 2) if expected_count > 0 else 0
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

@require_http_methods(["GET", "POST", "DELETE"])
def session_expected_people_view(request, session_id):
    """Manage expected people for a session"""
    session = get_object_or_404(Session, id=session_id)

    if request.method == "GET":
        expected_people = Person.objects.filter(expected_sessions__session=session)
        return JsonResponse({
            'status': 'ok',
            'session_id': session_id,
            'expected_people': [
                {
                    'id': person.id,
                    'name': person.get_full_name(),
                    'identification_number': person.identification_number
                }
                for person in expected_people
            ],
            'count': expected_people.count()
        })

    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            'status': 'error',
            'message': 'Request body is not valid JSON'
        }, status=400)

    person_ids = data.get('person_ids', [])
    if not isinstance(person_ids, list):
        return JsonResponse({
            'status': 'error',
            'message': 'person_ids must be a list'
        }, status=400)

    unique_ids = list(dict.fromkeys(person_ids))
    people = Person.objects.filter(id__in=unique_ids)
    if len(unique_ids) != people.count():
        return JsonResponse({
            'status': 'error',
            'message': 'One or more person_ids were not found'
        }, status=400)

    if request.method == "POST":
        if data.get('replace'):
            SessionExpectedPerson.objects.filter(session=session).delete()

        created_count = 0
        for person in people:
            _, created = SessionExpectedPerson.objects.get_or_create(
                session=session,
                person=person
            )
            if created:
                created_count += 1

        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'created_count': created_count,
            'expected_count': get_expected_count(session)
        })

    deleted_count, _ = SessionExpectedPerson.objects.filter(
        session=session,
        person__in=people
    ).delete()

    return JsonResponse({
        'status': 'success',
        'session_id': session_id,
        'deleted_count': deleted_count,
        'expected_count': get_expected_count(session)
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
                'message': f'Recognition is already running for session: {session.name}'
            }, status=400)

    # ------------------------------------------------------------------
    # 2. Guard: session already completed or cancelled
    # ------------------------------------------------------------------
    if session.status in ['completed', 'cancelled']:
        return JsonResponse({
            'status': 'error',
            'message': 'Cannot start session – it is already completed or cancelled'
        }, status=400)

    # ------------------------------------------------------------------
    # 3. Guard: no expected people (prod mode only)
    # ------------------------------------------------------------------
    if not dev_mode and get_expected_count(session) == 0:
        return JsonResponse({
            'status': 'error',
            'message': 'No expected people set for this session. Please add them first.'
        }, status=400)

    # ------------------------------------------------------------------
    # 4. Guard: no face encodings enrolled yet (prod mode only)
    # ------------------------------------------------------------------
    if not dev_mode and not FaceEncoding.objects.exists():
        return JsonResponse({
            'status': 'error',
            'message': 'No face encodings found in database. Please enroll people first.'
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
        session.status = 'in_progress'
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
            'name': session.name,
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

    if session.status not in ['completed', 'cancelled']:
        session.status = 'completed'
        session.end_time = timezone.now()
        session.save()

        # Log an event for session end (fail silently if Event creation fails)
        try:
            Event.objects.create(
                session=session,
                event_type='session_ended',
                severity='info',
                message=f"Session '{session.name}' ended via traditional view"
            )
        except Exception:
            pass

        return JsonResponse({
            'status': 'success',
            'message': f"Session '{session.name}' ended successfully",
            'session': {
                'id': str(session.id),
                'name': session.name,
                'status': session.status,
                'ended_at': isoformat_or_none(session.end_time)
            }
        })
    else:
        return JsonResponse({
            'status': 'info',
            'message': f"Session '{session.name}' was already ended",
            'session': {
                'id': str(session.id),
                'name': session.name,
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

            # Update session status if still in progress
            if session.status == 'in_progress':
                session.status = 'cancelled'
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
                    'name': session.name
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
    - name | subject: string
    - description: string
    - session_type: string
    - start_time: datetime
    - end_time: datetime
    - expected_count: integer
    - status: 'scheduled', 'in_progress', 'completed', or 'cancelled'

    Returns JSON response with updated session
    """
    session = get_object_or_404(Session, id=session_id)

    try:
        # Parse JSON body
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        if 'name' not in data and 'subject' in data:
            data['name'] = data.pop('subject')

        # Validate and update allowed fields
        updated_fields = []

        field_map = {
            'name': 'name',
            'description': 'description',
            'session_type': 'session_type',
            'start_time': 'start_time',
            'end_time': 'end_time',
            'expected_count': 'expected_count',
        }

        for key, attr in field_map.items():
            if key not in data:
                continue
            value = data[key]
            if attr in ['start_time', 'end_time'] and isinstance(value, str):
                parsed = parse_datetime(value)
                if parsed is None:
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Invalid datetime format for {attr}"
                    }, status=400)
                value = parsed

            setattr(session, attr, value)
            updated_fields.append(attr)

        if 'status' in data:
            valid_statuses = [choice[0] for choice in Session.STATUS_CHOICES]
            if data['status'] in valid_statuses:
                old_status = session.status
                session.status = data['status']
                updated_fields.append('status')

                # If manually ending session, set end_time and stop recognition
                if data['status'] in ['completed', 'cancelled'] and old_status not in ['completed', 'cancelled']:
                    if not session.end_time:
                        session.end_time = timezone.now()

                    active = active_recognition.get(str(session_id))
                    if active:
                        if active.get("stop_flag"):
                            active["stop_flag"].set()
                        active_recognition.pop(str(session_id), None)

                if data['status'] == 'in_progress' and not session.start_time:
                    session.start_time = timezone.now()
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
                    event_type='manual_override',
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
                    'name': session.name,
                    'description': session.description,
                    'session_type': session.session_type,
                    'expected_count': get_expected_count(session),
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
                    'name': session.name,
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

def session_present_people_partial(request, session_id):
    """Get present people for a session"""
    session = get_object_or_404(Session, id=session_id)
    present_records = list(get_present_records(session).select_related('person'))

    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'present_people': [
            {
                'id': record.person.id,
                'name': record.person.get_full_name(),
                'identification_number': record.person.identification_number,
                'status': record.status
            }
            for record in present_records
        ],
        'count': len(present_records)
    })

def session_absent_people_partial(request, session_id):
    """Get absent people for a session"""
    session = get_object_or_404(Session, id=session_id)
    expected_people = Person.objects.filter(expected_sessions__session=session)
    present_records = list(get_present_records(session).select_related('person'))
    present_ids = [record.person.id for record in present_records]
    absent_people = expected_people.exclude(id__in=present_ids)
    
    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'absent_people': [
            {
                'id': person.id,
                'name': person.get_full_name(),
                'identification_number': person.identification_number
            }
            for person in absent_people
        ],
        'count': absent_people.count()
    })

def session_unidentified_faces_partial(request, session_id):
    """Get unidentified faces for a session"""
    session = get_object_or_404(Session, id=session_id)
    unidentified_faces = UnidentifiedFace.objects.filter(session=session)

    faces_list = []
    for face in unidentified_faces:
        cropped_url = None
        full_url = None

        if face.cropped_face:
            try:
                cropped_url = request.build_absolute_uri(face.cropped_face.url)
            except Exception:
                cropped_url = os.path.join(settings.MEDIA_URL, face.cropped_face.name)

        if face.full_frame:
            try:
                full_url = request.build_absolute_uri(face.full_frame.url)
            except Exception:
                full_url = os.path.join(settings.MEDIA_URL, face.full_frame.name)

        faces_list.append({
            'id': face.id,
            'cropped_face': cropped_url,
            'full_frame': full_url,
            'confidence': face.confidence,
            'timestamp': isoformat_or_none(face.timestamp)
        })

    return JsonResponse({
        'status': 'ok',
        'session_id': session_id,
        'unidentified_faces': faces_list,
        'count': len(faces_list)
    })

def record_event(session, message, event_type='manual_override', severity='info'):
    Event.objects.create(
        session=session,
        message=message,
        event_type=event_type,
        severity=severity
    )

def recognition_progress_partial(request, session_id):
    """Get real-time recognition progress for a session"""
    session = get_object_or_404(Session, id=session_id)
    total_expected = get_expected_count(session)
    present_count = get_present_records(session).count()
    unknown_count = UnidentifiedFace.objects.filter(session=session).count()
    
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
