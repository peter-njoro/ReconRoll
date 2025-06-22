import cv2
import time


def start_video_capture(width=640, height=480, fps=30, buffer_size=1, device_index=0):
    """Optimized video capture initialization"""
    # Try different backends
    for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
        cap = cv2.VideoCapture(device_index, backend)
        if cap.isOpened():
            break

    if not cap.isOpened():
        return None

    # Set properties more efficiently
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    return cap

def calculate_fps(prev_time, fps_history, max_history=10):
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time + 1e-8)
    fps_history.append(fps)
    if len(fps_history) > max_history:
        fps_history.pop(0)
    avg_fps = sum(fps_history) / len(fps_history)
    return avg_fps, fps_history, curr_time
