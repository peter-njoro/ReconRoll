# recognition/webcam_stream.py
import cv2
import requests
import threading

def start_stream():
    url = "http://localhost:8000/api/upload_frame/"  # Django inside Docker
    
    # Try different video devices
    for device_index in range(2):  # Try both video0 and video1
        cap = cv2.VideoCapture(device_index)
        if cap.isOpened():
            print(f"Successfully opened video device {device_index}")
            break
    else:
        raise RuntimeError("Could not open any video device")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            # Try to reinitialize the camera
            cap.release()
            cap = cv2.VideoCapture(device_index)
            continue

        _, buf = cv2.imencode(".jpg", frame)
        files = {"frame": ("frame.jpg", buf.tobytes(), "image/jpeg")}
        try:
            r = requests.post(url, files=files, timeout=2)
            print(r.json())
        except Exception as e:
            print("Upload failed:", e)
