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

from recognition.models import Session, AttendanceRecord, FaceEncoding, Student, UnidentifiedFace, Event
from recognition.face_utils import (
    get_face_encodings, matches_face_encoding,
    annotate_frame, safe_load_dnn_model,
    load_known_encodings_from_db, save_unidentified_faces
)

# Parse args
parser = argparse.ArgumentParser(description='Start face recognition for a session')
parser.add_argument('--session-id', type=str, required=True, help='UUID of the session to use')
parser.add_argument('--video', type=str, help='Path to video file (optional, for the recorded video)')
args = parser.parse_args()

# Load session
try:
    session = Session.objects.get(id=args.session_id)
    print(f"Loaded session: {session.subject} | Group: {session.class_group}")
except Session.DoesNotExist:
    print(f"Session with id {args.session_id} not found.")
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

def main():
    try:
        # Load encodings
        known_face_encodings, known_face_names = load_known_encodings_from_db()
        print(f"✅ Loaded {len(known_face_encodings)} known encodings")

        # Load detector
        try:
            net = safe_load_dnn_model()
        except Exception:
            net = None
            print("⚠ Falling back to HOG")

        cap = start_video_capture(fps=target_fps)
        if not cap.isOpened():
            print("❌ Failed to open camera")
            return

        frame_count = 0
        prev_time = time.time()
        fps_history = []
        recognition_history = deque(maxlen=10)

        print("🎥 Webcam started - Press 'q' to quit...")

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
                                student = Student.objects.filter(full_name=name).first()
                                if student and not AttendanceRecord.objects.filter(session=session, student=student).exists():
                                    AttendanceRecord.objects.create(session=session, student=student)
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
    main()
