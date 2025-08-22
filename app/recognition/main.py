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


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
    print("Django setup successful")
except Exception as e:
    print(f"Django setup failed: {e}")
    traceback.print_exc()
    exit(1)

from recognition.models import Session, AttendanceRecord, FaceEncoding, Student, UnidentifiedFace, Event

# Parse args
parser = argparse.ArgumentParser(description='Start face recognition for a session')
parser.add_argument('--session-id', type=str, required=True, help='UUID of the session to use')
parser.add_argument('--video', type=str, help='Path to video file (optional, for the recorded video)')

args = parser.parse_args()

# Load the session
try:
    session = Session.objects.get(id=args.session_id)
    print(f"Loaded session: {session.subject} | Group: {session.class_group}")
except Session.DoesNotExist:
    print(f"Session with id {args.session_id} not found.")
    exit(1)
except Exception as e:
    print(f"Error loading session: {e}")
    traceback.print_exc()
    exit(1)

try:
    from recognition.face_utils import (
        get_face_encodings, matches_face_encoding,
        annotate_frame, safe_load_dnn_model,
        load_known_encodings_from_db, save_unidentified_faces
    )
    print("Successfully imported face_utils")
except ImportError as e:
    print(f"Failed to import face_utils: {e}")
    traceback.print_exc()
    exit(1)

try:
    from video_utils import start_video_capture, calculate_fps
    print("Successfully imported video_utils")
except ImportError as e:
    print(f"Failed to import video_utils: {e}")
    # Fallback to basic video capture
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

from collections import deque

# -----------------------------
# ✅ Config
# -----------------------------
scale_factor = 0.25
tolerance = 0.6
target_fps = 30
process_every_n_frames = 3
min_face_size = 60
min_confidence = 0.5

def main():
    try:
        # -----------------------------
        # ✅ Load known face encodings
        # -----------------------------
        print("Loading known face encodings from database...")
        try:
            known_face_encodings, known_face_names = load_known_encodings_from_db()
            print(f"Loaded {len(known_face_encodings)} encodings for {len(set(known_face_names))} students")
        except Exception as e:
            print(f"Failed to load known encodings: {e}")
            traceback.print_exc()
            known_face_encodings, known_face_names = np.array([]), []

        # -----------------------------
        # ✅ Load DNN face detector
        # -----------------------------
        try:
            net = safe_load_dnn_model()
            print("DNN model loaded successfully")
        except Exception as e:
            print(f"Failed to load DNN model: {e}")
            print("Falling back to HOG model")
            net = None

        # -----------------------------
        # ✅ Start Webcam
        # -----------------------------
        print("Starting webcam...")
        cap = start_video_capture(fps=target_fps)
        if cap is None or not cap.isOpened():
            print("Unable to access webcam. Trying default camera...")
            cap = cv2.VideoCapture(0)
            
        if not cap.isOpened():
            print("Failed to open any video source.")
            return

        frame_count = 0
        prev_time = time.time()
        fps_history = []
        recognition_history = deque(maxlen=10)

        print("Webcam started - Press 'q' to quit...")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Failed to read from webcam.")
                break

            frame_count += 1
            frame = cv2.flip(frame, 1)
            process_this_frame = frame_count % process_every_n_frames == 0

            face_locations = []
            face_names = []
            face_encodings_display = []

            if process_this_frame:
                try:
                    # Use DNN if available, otherwise use HOG
                    if net:
                        face_locations = detect_faces_dnn(frame, net, conf_threshold=min_confidence)
                    else:
                        # Fallback to HOG
                        small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
                        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        face_locations = face_recognition.face_locations(rgb_small_frame, model='hog')
                        # Scale back to original coordinates
                        face_locations = [(int(top/scale_factor), int(right/scale_factor), 
                                         int(bottom/scale_factor), int(left/scale_factor)) 
                                        for (top, right, bottom, left) in face_locations]

                    if face_locations:
                        print(f"Detected {len(face_locations)} faces in frame {frame_count}")
                        _, face_encodings = get_face_encodings(
                            frame, 
                            model='hog', 
                            scale=scale_factor, 
                            min_size=min_face_size
                        )

                        if face_encodings:
                            recognition_frame_info = []
                            for i, face_encoding in enumerate(face_encodings):
                                name, distance, _ = matches_face_encoding(
                                    face_encoding, known_face_encodings, known_face_names, tolerance
                                )
                                recognition_frame_info.append((name, face_encoding))
                                print(f"[{time.strftime('%H:%M:%S')}] Detected: {name} | Distance: {distance:.4f}")

                                if name != "unknown":
                                    try:
                                        student = Student.objects.filter(full_name=name).first()
                                        if student:
                                            # Check if attendance already recorded
                                            if not AttendanceRecord.objects.filter(session=session, student=student).exists():
                                                AttendanceRecord.objects.create(session=session, student=student)
                                                Event.objects.create(
                                                    session=session,
                                                    event_type='face_recognized',
                                                    severity='info',
                                                    message=f"Student recognized: {student.full_name}"
                                                )
                                                print(f"Attendance marked for {student.full_name}")
                                    except Exception as e:
                                        print(f"Error saving attendance for {name}: {e}")
                                else:
                                    try:
                                        # Save unidentified face
                                        cropped_path, full_path = save_unidentified_faces(frame, face_locations[i])
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
                                            print("Unidentified face saved & event logged")
                                    except Exception as e:
                                        print(f"Error saving unidentified face: {e}")

                            recognition_history.appendleft(recognition_frame_info)

                except Exception as e:
                    print(f"Error processing frame: {e}")
                    traceback.print_exc()

            # Display frame with annotations if we have face locations
            if face_locations:
                try:
                    frame = annotate_frame(
                        frame,
                        face_locations,
                        [name for name, _ in recognition_frame_info] if 'recognition_frame_info' in locals() else [],
                        face_encodings=face_encodings_display,
                        scale=1.0  # Already in original coordinates
                    )
                except Exception as e:
                    print(f"Error annotating frame: {e}")

            # FPS calculation
            try:
                fps, fps_history, prev_time = calculate_fps(prev_time, fps_history)
                cv2.putText(frame, f'FPS: {int(fps)}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f'Faces: {len(face_locations)}', (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            except Exception as e:
                print(f"Error displaying FPS: {e}")

            # Display the frame
            try:
                cv2.imshow('Face Recognition - Webcam Feed', frame)
            except Exception as e:
                print(f"Error displaying frame: {e}")

            # Check for quit command
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quit requested by user")
                break

    except Exception as e:
        print(f"Critical error in main loop: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()

        # End session properly
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
            print("Session ended & logged.")
        except Exception as e:
            print(f"Error ending session: {e}")
            traceback.print_exc()

# -----------------------------
# ✅ DNN Face Detection Function
# -----------------------------
def detect_faces_dnn(image, net, conf_threshold=0.5):
    try:
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
                (startX, startY, endX, endY) = box.astype("int")
                # Ensure coordinates are within image bounds
                startX, startY = max(0, startX), max(0, startY)
                endX, endY = min(w, endX), min(h, endY)
                face_locations.append((startY, endX, endY, startX))
        return face_locations
    except Exception as e:
        print(f"Error in DNN face detection: {e}")
        return []

if __name__ == "__main__":
    main()