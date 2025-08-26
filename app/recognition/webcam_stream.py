# recognition/webcam_stream.py
import cv2
import requests
import threading

def start_stream():
    url = "http://localhost:8000/api/upload_frame/"  # Django inside Docker
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        _, buf = cv2.imencode(".jpg", frame)
        files = {"frame": ("frame.jpg", buf.tobytes(), "image/jpeg")}
        try:
            r = requests.post(url, files=files, timeout=2)
            print(r.json())
        except Exception as e:
            print("Upload failed:", e)
