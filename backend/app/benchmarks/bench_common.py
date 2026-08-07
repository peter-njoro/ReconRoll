"""Shared helpers for the ReconRoll benchmark scripts.

Standalone: depends only on numpy, OpenCV and the face_recognition package.
No Django, no database access. Intended to run inside the project container
so the measured timings use the exact dlib/OpenCV builds from requirements.txt.

The pipeline stages mirror the production hot path in
app/recognition/recognition_runner.py:
    HOG detect (upsample=2) -> 128-D encode (num_jitters=1) ->
    Euclidean match against roster-scoped encodings (tolerance 0.55).
"""

import math
import os
import time

import cv2
import face_recognition
import numpy as np

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def load_face_images(images_dir, limit=None):
    paths = []
    if not os.path.isdir(images_dir):
        raise SystemExit(f"Images directory not found: {images_dir}")
    for name in sorted(os.listdir(images_dir)):
        if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
            paths.append(os.path.join(images_dir, name))
    if not paths:
        raise SystemExit(
            f"No face images (*.jpg/*.jpeg/*.png/*.bmp) found in {images_dir}"
        )
    if limit:
        paths = paths[:limit]
    return paths


def load_known_encodings(images_dir, limit=None, num_jitters=1):
    encodings = []
    names = []
    times = []
    for path in load_face_images(images_dir, limit):
        image = cv2.imread(path)
        if image is None:
            continue
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        start = time.perf_counter()
        locs = face_recognition.face_locations(
            rgb, number_of_times_to_upsample=1, model="hog"
        )
        encs = face_recognition.face_encodings(rgb, locs, num_jitters=num_jitters)
        times.append((time.perf_counter() - start) * 1000)
        for enc in encs:
            encodings.append(enc)
            names.append(os.path.splitext(os.path.basename(path))[0])
    known = np.array(encodings) if encodings else np.empty((0, 128))
    return known, names, times


def build_test_frame(images, faces_per_frame, frame_size=(640, 480)):
    width, height = frame_size
    canvas = np.full((height, width, 3), 127, dtype=np.uint8)
    if faces_per_frame < 1:
        return canvas
    cols = math.ceil(math.sqrt(faces_per_frame))
    rows = math.ceil(faces_per_frame / cols)
    cell_w = width // cols
    cell_h = height // rows
    face_size = max(min(cell_w, cell_h) - 12, 60)
    for i in range(faces_per_frame):
        img = images[i % len(images)]
        h, w = img.shape[:2]
        side = max(h, w)
        top = max((h - side) // 2, 0)
        left = max((w - side) // 2, 0)
        crop = img[top:top + side, left:left + side]
        crop = cv2.resize(crop, (face_size, face_size))
        cx = (i % cols) * cell_w + cell_w // 2 - face_size // 2
        cy = (i // cols) * cell_h + cell_h // 2 - face_size // 2
        cy = max(0, min(cy, height - face_size))
        cx = max(0, min(cx, width - face_size))
        canvas[cy:cy + face_size, cx:cx + face_size] = crop
    return canvas


def detect_faces(frame, model="hog", upsample=2, dnn_net=None):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if model == "dnn" and dnn_net is not None:
        (h, w) = rgb.shape[:2]
        blob = cv2.dnn.blobFromImage(rgb, 1.0, (300, 300), (104.0, 177.0, 123.0))
        dnn_net.setInput(blob)
        detections = dnn_net.forward()
        face_locations = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (left, top, right, bottom) = box.astype("int")
                face_locations.append((top, right, bottom, left))
        return face_locations, rgb
    face_locations = face_recognition.face_locations(
        rgb, number_of_times_to_upsample=upsample, model="hog"
    )
    return face_locations, rgb


def encode_faces(rgb, face_locations, num_jitters=1):
    if not face_locations:
        return []
    return face_recognition.face_encodings(rgb, face_locations, num_jitters=num_jitters)


def match_encoding(encoding, known_encodings, known_names, tolerance=0.55):
    distances = np.linalg.norm(known_encodings - encoding, axis=1)
    idx = np.argmin(distances)
    if distances[idx] <= tolerance:
        return known_names[idx], distances[idx]
    return "unknown", distances[idx]
