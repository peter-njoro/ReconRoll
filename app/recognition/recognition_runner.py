import os
import sys
import cv2
import numpy as np
import django
import subprocess
import threading
import queue
import time
import face_recognition
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Load env vars & config safely
face_model = os.getenv('FACE_MODEL', 'hog')
scale = float(os.getenv('SCALE', '0.25'))
min_size = int(os.getenv('MIN_FACE_SIZE', '100'))
tolerance = float(os.getenv('TOLERANCE', '0.55'))

print(f"Using model={face_model}, scale={scale}, min_size={min_size}, tolerance={tolerance}")

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


def run_recognition(session_id, video=None, dev_mode=False, stop_flag=None):
    print(f"Starting recognition for session {session_id} | dev_mode={dev_mode}")

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
    print(f"Production mode: Processing frames from upload queue for session {session_id}")
    
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
        # FIX #1: Pass session to scope encodings to class_group only
        known_face_encodings, known_face_names = load_known_encodings_from_db(session=session)
        print(f"Loaded {len(known_face_encodings)} encodings for background processing")

        # Cache for previously seen unknown encodings in THIS session
        unknown_encodings = []
        frame_count = 0
        recognized_count = 0
        unknown_count = 0
        
        # Encoding cache (avoid re-encoding same face)
        recent_encodings_cache = {}
        
        while True:
            if stop_flag and stop_flag.is_set():
                print(f"Stop requested for session {session_id}")
                break

            try:
                # Wait for frames from the queue with timeout
                # Frames are encoded as JPEG bytes (from upload endpoint). Decode
                # here to obtain an owned numpy array. Using bytes avoids passing
                # shared numpy memory across threads which can trigger memory
                # corruption in native libraries.
                frame_bytes = frame_queue.get(timeout=5)
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
                # FIX #1: Pass session to reload only students in this class_group
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
                        student = Person.objects.filter(full_name=name).first()
                        if student:
                            record, created = AttendanceSummary.objects.get_or_create(session=session, student=student)
                            if created:
                                recognized_count += 1
                                Event.objects.create(
                                    session=session,
                                    student=student,
                                    event_type='face_recognized',
                                    severity='info',
                                    message=f"Student recognized: {student.full_name}"
                                )
                                print(f"✓ Attendance marked for {student.full_name} ({recognized_count} total)")

                    else:
                        if idx == -1:
                            cropped_path, full_path, saved_encoding = save_unidentified_faces(
                                frame_copy, face_locations[i], session=session, base_dir='uploads/unidentified/', encoding=face_encoding
                            )
                            if cropped_path and full_path:
                                unknown_count += 1
                                UnidentifiedFace.objects.create(
                                    session=session,
                                    cropped_face=cropped_path,
                                    full_frame=full_path
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
                # Check if session was ended
                session.refresh_from_db()
                if session.status == 'ended':
                    print(f"Session {session_id} has been ended externally")
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
        if session.status != 'ended':
            session.status = 'ended'
            session.end_time = datetime.now()
            session.save()
            Event.objects.create(
                session=session,
                event_type='session_ended',
                severity='info',
                message=f"Session ended (production mode): {recognized_count} recognized, {unknown_count} unknown"
            )
            print("✓ Session ended & logged.")
        else:
            print("Session already ended")

        print(f"✓ Recognition finished. Processed {frame_count} frames. Recognized: {recognized_count}, Unknown: {unknown_count}")
        
    except Exception as e:
        # Catch all unhandled exceptions in the background thread
        print(f"[CRITICAL ERROR] Recognition thread crashed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to mark session as ended to prevent it from hanging
        try:
            session = Session.objects.get(id=session_id)
            if session.status == 'ongoing':
                session.status = 'ended'
                session.end_time = datetime.now()
                session.save()
                Event.objects.create(
                    session=session,
                    event_type='session_ended',
                    severity='error',
                    message=f"Session ended due to critical error: {str(e)}"
                )
                print(f"[INFO] Marked session {session_id} as ended due to error")
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
