# recognition/webcam_stream.py
import cv2
import requests
import threading
import time
import os
import sys
from datetime import datetime

def start_stream():
    """Continuously capture frames from webcam and post to Django server"""
    
    # Get the server URL from environment or use default
    server_url = os.environ.get('FRAME_SERVER_URL', 'http://127.0.0.1:8000')
    upload_url = f"{server_url}/api/upload_frame/"
    
    print(f"[{datetime.now()}] Attempting to connect to {upload_url}")
    
    # Try different video devices
    device_index = None
    for idx in range(5):  # Try video0 through video4
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                print(f"[{datetime.now()}] ✓ Successfully opened video device {idx}")
                device_index = idx
                break
            cap.release()
        except Exception as e:
            print(f"[{datetime.now()}] Error opening device {idx}: {e}")
            continue
    
    if device_index is None:
        print(f"[{datetime.now()}] ✗ ERROR: Could not open any video device")
        sys.exit(1)
    
    cap = cv2.VideoCapture(device_index)
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    frame_count = 0
    error_count = 0
    max_errors = 10
    
    print(f"[{datetime.now()}] Starting frame capture loop...")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print(f"[{datetime.now()}] ⚠ Failed to grab frame")
                error_count += 1
                if error_count > max_errors:
                    print(f"[{datetime.now()}] Too many errors, reinitializing camera...")
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(device_index)
                    error_count = 0
                continue
            
            error_count = 0
            frame_count += 1
            
            try:
                _, buf = cv2.imencode(".jpg", frame)
                files = {"frame": ("frame.jpg", buf.tobytes(), "image/jpeg")}
                
                response = requests.post(upload_url, files=files, timeout=2)
                
                if frame_count % 30 == 0:  # Log every 30 frames
                    print(f"[{datetime.now()}] Frame {frame_count}: Status {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                print(f"[{datetime.now()}] ⚠ Connection error: Cannot reach {upload_url}")
                time.sleep(2)
            except requests.exceptions.Timeout:
                print(f"[{datetime.now()}] ⚠ Timeout uploading frame")
            except Exception as e:
                print(f"[{datetime.now()}] ⚠ Error uploading frame: {e}")
    
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Stream interrupted by user")
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
            print(f"[{datetime.now()}] Camera released")

if __name__ == "__main__":
    start_stream()
