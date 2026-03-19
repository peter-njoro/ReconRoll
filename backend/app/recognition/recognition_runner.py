import os
import sys
import cv2
import numpy as np
import django
import subprocess
import threading
import queue
import io
import time
import logging
import face_recognition
from dotenv import load_dotenv
from django.utils import timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Load env vars & config safely
face_model = os.getenv('FACE_MODEL', 'hog')
scale = float(os.getenv('SCALE', '0.25'))
min_size = int(os.getenv('MIN_FACE_SIZE', '100'))
tolerance = float(os.getenv('TOLERANCE', '0.55'))

logger.info(f"Using model={face_model}, scale={scale}, min_size={min_size}, tolerance={tolerance}")

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from recognition.models import Session, Person, AttendanceSummary, UnidentifiedFace, Event
from recognition.face_utils import (
    get_face_encodings, matches_face_encoding,
    save_unidentified_faces, load_known_encodings_from_db,
    annotate_frame, safe_load_dnn_model
)

from threading import Event as StopEvent
active_recognition = {}  # e.g., {session_id: {"thread": thread, "stop_flag": StopEvent()}}

# Global queue for frames being processed in production mode
frame_queue = queue.Queue(maxsize=30)  # Keep last 30 frames


def split_full_name(full_name):
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def resolve_person_from_name(name):
    first_name, last_name = split_full_name(name)
    if not first_name:
        return None

    person = Person.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name
    ).first()
    if person:
        return person

    if not last_name:
        return Person.objects.filter(first_name__iexact=first_name).first()

    return None


def run_recognition(session_id, video=None, dev_mode=False, stop_flag=None):
    logger.info(f"Starting recognition for session {session_id} | dev_mode={dev_mode}")

    if dev_mode:
        # Run main.py in dev mode
        return run_main_py_dev_mode(session_id, stop_flag)

    # Production mode: process frames from upload_frame endpoint
    return run_recognition_from_queue(session_id, stop_flag)


def run_recognition_from_queue(session_id, stop_flag):
    """
    Production mode: Process frames uploaded via webcam_stream.py
    OPTIMIZED for accuracy: use full num_jitters=2 for encoding, batch processing
    """
    logger.info(f"Production mode: Processing frames from upload queue for session {session_id}")
    logger.debug(f"Frame queue object ID: {id(frame_queue)}, initial size: {frame_queue.qsize()}")
    
    try:
        # Load DNN model if using DNN face detection
        dnn_net = None
        if face_model == 'dnn':
            try:
                dnn_net = safe_load_dnn_model()
                print("[INFO] DNN model loaded successfully")
            except Exception as e:
                print(f"[ERROR] Failed to load DNN model: {e}. Falling back to HOG.")
                print("[WARNING] Using HOG model instead of DNN")

        session = Session.objects.get(id=session_id)
        # Scope encodings to expected people for the session when possible
        known_face_encodings, known_face_names = load_known_encodings_from_db(session=session)
        logger.info(f"Loaded {len(known_face_encodings)} encodings for background processing")

        # Cache for previously seen unknown encodings in THIS session
        unknown_encodings = []
        frame_count = 0
        recognized_count = 0
        unknown_count = 0
        
        # Encoding cache (avoid re-encoding same face)
        recent_encodings_cache = {}
        
        while True:
            if stop_flag and stop_flag.is_set():
                logger.info(f"Stop requested for session {session_id}")
                break

            try:
                # Wait for frames from the queue with timeout
                # Frames are encoded as JPEG bytes (from upload endpoint). Decode
                # here to obtain an owned numpy array. Using bytes avoids passing
                # shared numpy memory across threads which can trigger memory
                # corruption in native libraries.
                logger.debug(f"Waiting for frame from queue... (queue size: {frame_queue.qsize()})")
                frame_bytes = frame_queue.get(timeout=5)
                logger.info(f"Got frame from queue! Queue size now: {frame_queue.qsize()}")
                # Convert frombuffer to owned array to avoid memory corruption
                # frombuffer creates a read-only view; we need owned data for OpenCV
                frame_array = np.frombuffer(frame_bytes, np.uint8).copy()
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                # Ensure frame is owned data (imdecode should return owned data, but be explicit)
                if frame is not None and not frame.flags['OWNDATA']:
                    frame = frame.copy()

                if frame is None:
                    print(f"[WARNING] Failed to decode frame from queue")
                    continue

                frame_count += 1

                # ===== OPTIMIZATION: Reload encodings every 500 frames (lazy reload) =====
                # This keeps accuracy high without excessive database queries
                # Reload encodings for expected people in this session
                if frame_count % 500 == 0:
                    known_face_encodings, known_face_names = load_known_encodings_from_db(session=session)
                    print(f"[INFO] Reloaded {len(known_face_encodings)} encodings (frame {frame_count})")
                    recent_encodings_cache.clear()  # Clear stale cache

                # Detect faces & get encodings with FULL accuracy settings
                # In background thread, we can afford num_jitters=2 for better accuracy
                # Make a copy of the frame so downstream C extensions operate on
                # memory owned by this function.
                frame_copy = frame.copy()
                if face_model == 'dnn':
                    face_locations, face_encodings = get_face_encodings(
                        frame_copy, model=face_model, scale=scale, min_size=min_size, dnn_net=dnn_net
                    )
                else:
                    # Use HOG but with upsampling for better accuracy in background thread
                    face_locations = face_recognition.face_locations(
                        frame_copy,
                        number_of_times_to_upsample=2,  # More accurate (slower, but okay for background)
                        model='hog'
                    )
                    face_encodings = face_recognition.face_encodings(
                        frame_copy,
                        face_locations,
                        num_jitters=1  
                    )

                if not face_locations:
                    continue

                print(f"[DEBUG] Frame {frame_count}: {len(face_locations)} faces detected")

                recognition_results = []
                for i, face_encoding in enumerate(face_encodings):
                    # Updated to 4-return version
                    name, distance, idx, is_known = matches_face_encoding(
                        face_encoding, known_face_encodings, known_face_names,
                        unknown_encodings, tolerance=tolerance
                    )
                    recognition_results.append((name, distance))
                    print(f"[INFO] Detected: {name} | Distance: {distance:.4f}")

                    if is_known and name != "unknown":
                        person = resolve_person_from_name(name)
                        if person:
                            recognized_at = timezone.now()
                            is_late = bool(session.start_time and recognized_at > session.start_time)
                            status_value = 'late' if is_late else 'present'

                            # Use RosterAttendance if session has a roster, otherwise AttendanceSummary
                            if session.roster:
                                from recognition.models import RosterAttendance
                                record, created = RosterAttendance.objects.get_or_create(
                                    roster=session.roster,
                                    session=session,
                                    person=person,
                                    defaults={
                                        'status': status_value,
                                        'marked_at': recognized_at
                                    }
                                )
                            else:
                                record, created = AttendanceSummary.objects.get_or_create(
                                    session=session,
                                    person=person,
                                    defaults={
                                        'status': status_value,
                                        'marked_at': recognized_at
                                    }
                                )
                            
                            status_changed = False
                            if not created and (record.status != status_value or record.marked_at is None):
                                record.status = status_value
                                record.marked_at = recognized_at
                                record.save(update_fields=['status', 'marked_at', 'updated_at'])
                                status_changed = True

                            if created or status_changed:
                                recognized_count += 1
                                Event.objects.create(
                                    session=session,
                                    student=person,
                                    event_type='face_recognized',
                                    severity='info',
                                    message=f"Person recognized: {person.get_full_name()}"
                                )
                                logger.info(f"✓ Attendance marked for {person.get_full_name()} ({recognized_count} total)")

                    else:
                        if idx == -1:
                            cropped_path, full_path, saved_encoding = save_unidentified_faces(
                                frame_copy, face_locations[i], session=session, base_dir='uploads/unidentified/', encoding=face_encoding
                            )
                            if cropped_path and full_path:
                                encoding_bytes = None
                                if saved_encoding is not None:
                                    buffer = io.BytesIO()
                                    np.save(buffer, saved_encoding)
                                    encoding_bytes = buffer.getvalue()

                                unknown_count += 1
                                UnidentifiedFace.objects.create(
                                    session=session,
                                    cropped_face=cropped_path,
                                    full_frame=full_path,
                                    encoding=encoding_bytes
                                )
                                Event.objects.create(
                                    session=session,
                                    event_type='unknown_face',
                                    severity='warning',
                                    message="Unidentified face captured"
                                )
                                print(f"⚠ Unidentified face saved & event logged ({unknown_count} total)")
                                if saved_encoding is not None:
                                    unknown_encodings.append(saved_encoding)
                        else:
                            print("Unknown face already saved, skipping duplicate.")

            except queue.Empty:
                # No frames in queue for 5 seconds
                print(f"[DEBUG] Idle: no frames for 5 seconds (session {session_id})")
                # Check if session was completed or cancelled
                session.refresh_from_db()
                if session.status in ['completed', 'cancelled']:
                    print(f"Session {session_id} has been completed or cancelled externally")
                    break
                # Otherwise, continue waiting
                continue

            except Exception as e:
                print(f"[ERROR] Error processing frame: {e}")
                import traceback
                traceback.print_exc()
                continue

        # Session end logic
        session.refresh_from_db()
        if session.status not in ['completed', 'cancelled']:
            session.status = 'completed'
            session.end_time = timezone.now()
            session.save()
            Event.objects.create(
                session=session,
                event_type='session_ended',
                severity='info',
                message=f"Session completed (production mode): {recognized_count} recognized, {unknown_count} unknown"
            )
            print("✓ Session completed & logged.")
        else:
            print("Session already completed or cancelled")

        print(f"✓ Recognition finished. Processed {frame_count} frames. Recognized: {recognized_count}, Unknown: {unknown_count}")
        
    except Exception as e:
        # Catch all unhandled exceptions in the background thread
        print(f"[CRITICAL ERROR] Recognition thread crashed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to mark session as cancelled to prevent it from hanging
        try:
            session = Session.objects.get(id=session_id)
            if session.status == 'in_progress':
                session.status = 'cancelled'
                session.end_time = timezone.now()
                session.save()
                Event.objects.create(
                    session=session,
                    event_type='session_ended',
                    severity='error',
                    message=f"Session ended due to critical error: {str(e)}"
                )
                print(f"[INFO] Marked session {session_id} as cancelled due to error")
        except Exception as cleanup_error:
            print(f"[ERROR] Failed to cleanup session on error: {cleanup_error}")


def run_main_py_dev_mode(session_id, stop_flag):
    """Run main.py as a subprocess for dev mode with native OpenCV window"""
    print(f"Starting main.py in dev mode for session {session_id}")

    # Build command to run main.py
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), 'main.py'),
        '--session-id', str(session_id)
    ]

    # Start the subprocess without piping stdout/stderr
    process = subprocess.Popen(
        cmd,
        stdout=None,
        stderr=None,
        stdin=None
    )

    # Store process reference for stopping
    if str(session_id) not in active_recognition:
        active_recognition[str(session_id)] = {}
    active_recognition[str(session_id)]["process"] = process

    # Monitor the process and stop flag
    def monitor_process():
        while True:
            if stop_flag and stop_flag.is_set():
                print(f"Stopping main.py process for session {session_id}")
                process.terminate()
                break

            if process.poll() is not None:
                print(f"main.py process ended with return code: {process.returncode}")
                break

            threading.Event().wait(0.5)

        if str(session_id) in active_recognition:
            active_recognition[str(session_id)].pop("process", None)

    monitor_thread = threading.Thread(target=monitor_process)
    monitor_thread.daemon = True
    monitor_thread.start()

    return process
