import os
import cv2
import uuid
import numpy as np
import django
import sys
from datetime import datetime

# Setup Django (needed if run outside manage.py context)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from recognition.models import Session, Student, AttendanceRecord, UnidentifiedFace, Event
from recognition.face_utils import (
    get_face_encodings, matches_face_encoding,
    save_unidentified_face, load_known_encodings_from_db
)

def run_recognition(session_id, video=None, dev_mode=False):
    """
    session_id: UUID of session
    video: path to video file (or None for webcam)
    dev_mode: if True, skip DB writes & just print
    """
    print(f"🚀 Starting recognition for session {session_id} | dev_mode={dev_mode}")

    # Load session
    session = Session.objects.get(id=session_id)

    # Load known encodings
    known_face_encodings, known_face_names = load_known_encodings_from_db()
    print(f"✅ Loaded {len(known_face_encodings)} encodings")

    # Open video or webcam
    cap = cv2.VideoCapture(video if video else 0)
    if not cap.isOpened():
        print("❌ Failed to open video source.")
        return

    process_every_n_frames = 3
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("❌ Frame read failed or end of video.")
            break

        frame_count += 1
        if frame_count % process_every_n_frames != 0:
            continue

        face_locations, face_encodings = get_face_encodings(frame)

        for i, face_encoding in enumerate(face_encodings):
            name, distance, _ = matches_face_encoding(
                face_encoding, known_face_encodings, known_face_names, tolerance=0.6
            )
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

        # OPTIONAL: Add cv2.imshow() if you want live window (remove in prod)

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
            message="Session ended"
        )
        print("🛑 Session ended & logged.")
    else:
        print("[DEV MODE] Would end session & log event")

    print("🎉 Recognition finished.")
