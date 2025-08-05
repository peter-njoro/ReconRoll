import cv2
import time

def start_video_capture(width=640, height=480, fps=30, buffer_size=2, device_index=0):
    """
    Initialize and return a configured cv2.VideoCapture object.
    Returns None if initialization fails.
    """
    cap = cv2.VideoCapture(device_index)  # No backend forced

    if not cap.isOpened():
        print("❌ Failed to open webcam.")
        return None

    # Try setting camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)

    # Print the actual properties to confirm
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"📷 Webcam initialized at {int(actual_width)}x{int(actual_height)} @ {actual_fps:.2f} FPS")
    return cap

def calculate_fps(prev_time, fps_history, max_history=10):
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time + 1e-8)
    fps_history.append(fps)
    if len(fps_history) > max_history:
        fps_history.pop(0)
    avg_fps = sum(fps_history) / len(fps_history)
    return avg_fps, fps_history, curr_time
