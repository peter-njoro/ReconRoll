import os
import sys
import uuid
import cv2
import time
import argparse
import django
import face_recognition
import numpy as np
import traceback
from datetime import datetime
from collections import deque

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
    print("Django setup successful")
except Exception as e:
    print(f"Django setup failed: {e}")
    traceback.print_exc()
    exit(1)

from recognition.models import Session, AttendanceSummary, FaceEncoding, Person, UnidentifiedFace, Event
from recognition.face_utils import (
    get_face_encodings, matches_face_encoding,
    annotate_frame, safe_load_dnn_model,
    load_known_encodings_from_db, save_unidentified_faces
)

# Parse args
parser = argparse.ArgumentParser(description='Start face recognition for a session')
parser.add_argument('--session-id', type=str, help='UUID of the session to use')
parser.add_argument('--video', type=str, help='Path to video file (optional, for the recorded video)')
parser.add_argument('--test-webcam', action='store_true', help='Test webcam access and device info (no display)')
parser.add_argument('--test-devices', action='store_true', help='List all available video devices')
args = parser.parse_args()

# Load session
session = None
try:
    session = Session.objects.get(id=args.session_id)
    print(f"Loaded session: {session.name} | Group: {session.class_group}")
except Session.DoesNotExist:
    print(f"Session with id {args.session_id} not found.")
    exit(1)
except Exception as e:
    print(f"[ERROR] Failed to connect to database: {e}")
    print("[ERROR] This usually means the database is not accessible.")
    print("[ERROR] Make sure you're running this from within Docker or the database is running.")
    print("[HELP] To test webcam without database, use: python main.py --test-webcam")
    print("[HELP] To use in Docker, run: docker-compose exec recognition python recognition/main.py --session-id <ID>")
    exit(1)

# Fallback video utils
def start_video_capture(fps=30):
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FPS, fps)
    return cap

def calculate_fps(prev_time, fps_history, max_history=10):
    current_time = time.time()
    fps = 1.0 / (current_time - prev_time)
    fps_history.append(fps)
    if len(fps_history) > max_history:
        fps_history.pop(0)
    avg_fps = sum(fps_history) / len(fps_history) if fps_history else fps
    return avg_fps, fps_history, current_time

# Config
scale_factor = 0.25
tolerance = 0.6
target_fps = 30
process_every_n_frames = 3
min_face_size = 60
min_confidence = 0.5
unknown_encodings = []

def test_webcam_devices():
    """Test available webcam devices and their accessibility"""
    print("\n=== WEBCAM DEVICE TEST ===")
    print(f"Testing up to 5 video devices...\n")
    
    found_devices = []
    for device_index in range(5):
        try:
            cap = cv2.VideoCapture(device_index)
            if cap.isOpened():
                # Get device properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                
                print(f"✓ /dev/video{device_index} - ACCESSIBLE")
                print(f"  Resolution: {width}x{height}, FPS: {fps}")
                
                # Try to grab a frame
                ret, frame = cap.read()
                if ret:
                    print(f"  ✓ Frame captured successfully ({frame.shape})")
                    found_devices.append(device_index)
                else:
                    print(f"  ⚠ Could not grab frame")
                
                cap.release()
            else:
                print(f"✗ /dev/video{device_index} - Not accessible or doesn't exist")
        except Exception as e:
            print(f"✗ /dev/video{device_index} - Error: {e}")
    
    print(f"\n✓ Found {len(found_devices)} working device(s): {found_devices}")
    return len(found_devices) > 0

def main():
    try:
        # Load encodings - FIX #1: Pass session to scope encodings to class_group only
        known_face_encodings, known_face_names = load_known_encodings_from_db(session=session)
        print(f"Loaded {len(known_face_encodings)} known encodings for session")

        # Load detector
        try:
            net = safe_load_dnn_model()
        except Exception as e:
            net = None
            print(f"Falling back to HOG: {e}")

        cap = start_video_capture(fps=target_fps)
        if not cap.isOpened():
            print("Failed to open camera")
            return

        frame_count = 0
        prev_time = time.time()
        fps_history = []
        recognition_history = deque(maxlen=10)

        print("Webcam started - Press 'q' to quit...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            frame = cv2.flip(frame, 1)
            process_this_frame = frame_count % process_every_n_frames == 0

            face_locations, face_encodings = [], []
            if process_this_frame:
                try:
                    if net:
                        face_locations = detect_faces_dnn(frame, net, conf_threshold=min_confidence)
                    else:
                        small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
                        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_small, model='hog')
                        face_locations = [(int(t/scale_factor), int(r/scale_factor),
                                           int(b/scale_factor), int(l/scale_factor))
                                          for (t, r, b, l) in face_locations]

                    if face_locations:
                        _, face_encodings = get_face_encodings(
                            frame, model='hog', scale=scale_factor, min_size=min_face_size
                        )

                        recognition_frame_info = []
                        for i, face_encoding in enumerate(face_encodings):
                            name, distance, idx, is_known = matches_face_encoding(
                                face_encoding, known_face_encodings, known_face_names,
                                unknown_encodings, tolerance=tolerance
                            )
                            recognition_frame_info.append((name, face_encoding))
                            print(f"[{time.strftime('%H:%M:%S')}] {name} ({distance:.3f})")

                            if name != "unknown":
                                student = Person.objects.filter(full_name=name).first()
                                if student and not AttendanceSummary.objects.filter(session=session, student=student).exists():
                                    AttendanceSummary.objects.create(session=session, student=student)
                                    Event.objects.create(
                                        session=session,
                                        event_type='face_recognized',
                                        severity='info',
                                        message=f"Student recognized: {student.full_name}"
                                    )
                            else:
                                cropped_path, full_path, saved_encoding = save_unidentified_faces(
                                    frame, face_locations[i], session=session, encoding=face_encoding
                                )
                                if cropped_path and full_path:
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
                                    print("⚠ Unidentified face saved & event logged")
                                    if saved_encoding is not None:
                                        unknown_encodings.append(saved_encoding)

                        recognition_history.appendleft(recognition_frame_info)

                except Exception as e:
                    print(f"Error processing frame: {e}")
                    traceback.print_exc()

            if face_locations:
                try:
                    frame = annotate_frame(
                        frame, face_locations,
                        [n for n, _ in recognition_frame_info] if 'recognition_frame_info' in locals() else []
                    )
                except Exception as e:
                    print(f"Error annotating: {e}")

            fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)
            cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Face Recognition - Webcam Feed', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
        try:
            if session:  # Ensure session was successfully loaded
                session.status = 'ended'
                session.end_time = datetime.now()
                session.save()
                Event.objects.create(
                    session=session,
                    event_type='session_ended',
                    severity='info',
                    message="Session ended from main.py"
                )
        except Exception as e:
            print(f"Error ending session: {e}")

def detect_faces_dnn(image, net, conf_threshold=0.5):
    h, w = image.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                 (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()
    face_locations = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            face_locations.append((y1, x2, y2, x1))
    return face_locations

if __name__ == "__main__":
    # Handle test modes
    if args.test_devices or args.test_webcam:
        test_webcam_devices()
        exit(0)
    
    # Require session-id for normal operation
    if not args.session_id:
        parser.error("--session-id is required for normal operation. Use --test-webcam or --test-devices to test without a session.")
    
    main()
