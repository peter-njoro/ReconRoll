# recognition/recognition_runner.py

import os
import sys
import cv2
import uuid
import numpy as np
import django
from datetime import datetime

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from recognition.models import Session, Student, AttendanceRecord, UnidentifiedFace, Event
from recognition.face_utils import (
    get_face_encodings, matches_face_encoding,
    save_unidentified_face, load_known_encodings_from_db,
    annotate_frame
)

# 🔥 Store active recognition sessions
from threading import Event as StopEvent
active_recognition = {}  # e.g., {session_id: {"thread": thread, "stop_flag": StopEvent()}}

def run_recognition(session_id, video=None, dev_mode=False, stop_flag=None):
    print(f"🚀 Starting recognition for session {session_id} | dev_mode={dev_mode}")

    session = Session.objects.get(id=session_id)
    known_face_encodings, known_face_names = load_known_encodings_from_db()
    print(f"✅ Loaded {len(known_face_encodings)} encodings")

    cap = cv2.VideoCapture(video if video else 0)
    if not cap.isOpened():
        print("❌ Failed to open video source.")
        return

    process_every_n_frames = 3
    frame_count = 0

    while cap.isOpened():
        if stop_flag and stop_flag.is_set():
            print(f"🛑 Stop requested for session {session_id}")
            break

        ret, frame = cap.read()
        if not ret:
            print("❌ Frame read failed or end of video.")
            break

        frame_count += 1
        if frame_count % process_every_n_frames != 0:
            continue

        # 🔍 Get face encodings
        face_locations, face_encodings = get_face_encodings(frame, model=face_model, scale=0.5, min_size=60)
        print(f"[DEBUG] Frame {frame_count}: found {len(face_locations)} locations, {len(face_encodings)} encodings")

        # Prepare list to store matches for dev_mode visualization
        recognition_results = []

        for i, face_encoding in enumerate(face_encodings):
            name, distance, _ = matches_face_encoding(
                face_encoding, known_face_encodings, known_face_names, tolerance=0.6
            )
            recognition_results.append((name, distance))
            print(f"[INFO] Detected: {name} | Distance: {distance:.4f}")

            if name != "unknown":
                if not dev_mode:
                    student = Student.objects.filter(full_name=name).first()
                    if student and not AttendanceRecord.objects.filter(session=session, student=student).exists():
                        AttendanceRecord.objects.create(session=session, student=student)
                        Event.objects.create(
                            session=session,
                            student=student,
                            event_type='face_recognized',
                            severity='info',
                            message=f"Student recognized: {student.full_name}"
                        )
                        print(f"✅ Attendance marked for {student.full_name}")
                else:
                    print(f"[DEV MODE] Would mark attendance for {name}")
            else:
                if not dev_mode:
                    saved_path = save_unidentified_face(frame, face_locations[i])
                    if saved_path:
                        UnidentifiedFace.objects.create(session=session, image_path=saved_path)
                        Event.objects.create(
                            session=session,
                            event_type='unknown_face',
                            severity='warning',
                            message="Unidentified face captured"
                        )
                        print("⚠ Unidentified face saved & event logged")
                else:
                    print("[DEV MODE] Would save unidentified face")

        face_locations, face_encodings = get_face_encodings(frame, model=face_model, scale=0.5, min_size=60)
        print(f"[DEBUG] Frame {frame_count}: found {len(face_locations)} locations, {len(face_encodings)} encodings")

        recognition_results = []
        for i, face_encoding in enumerate(face_encodings):
            name, distance, _ = matches_face_encoding(
                face_encoding, known_face_encodings, known_face_names, tolerance=0.6
            )
            recognition_results.append((name, distance))
            print(f"[INFO] Detected: {name} | Distance: {distance:.4f}")
            # recognition / attendance / events logic...

        # Only show annotated frame in dev_mode
        if dev_mode and face_locations:
            face_names = [name for name, distance in recognition_results]
            annotated = annotate_frame(
                frame.copy(), face_locations, face_names,
                face_encodings=face_encodings, scale=0.5
            )
            cv2.imshow('🛠 Debug - Webcam View', annotated)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("🛑 Quit requested by user.")
            break


    cap.release()
    cv2.destroyAllWindows()

    if not dev_mode:
        session.status = 'ended'
        session.end_time = datetime.now()
        session.save()
        Event.objects.create(
            session=session,
            event_type='session_ended',
            severity='info',
            message="Session ended (auto)"
        )
        print("🛑 Session ended & logged.")
    else:
        print("[DEV MODE] Would end session & log event")

    print("🎉 Recognition finished.")
