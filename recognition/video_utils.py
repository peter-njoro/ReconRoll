import cv2
import time

def start_video_capture(width=640, height=480, fps=30, buffer_size=2):
    """
    Set up and return a cv2.VideoCapture object
    """
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
    return cap

def calculate_fps(prev_time, fps_history, max_history=10):
    """
    Calculate and return FPS metrics
    Returns: new_fps, updated_history, new_time
    """
    curr_time = time.time()
    new_fps = 1 / (curr_time - prev_time)
    updated_history = fps_history + [new_fps]
    if len(updated_history) > max_history:
        updated_history.pop(0)
    return new_fps, updated_history, curr_time