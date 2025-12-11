# Server crashes with memory corruption in production mode

## 🐛 Bug Report

**Title**: Server crashes with `munmap_chunk(): invalid pointer` when starting face recognition in production mode

### 📝 Description

The server crashes with a heap memory corruption error whenever face recognition is started via the `/api/session/<uuid:session_id>/start/` endpoint. The crash occurs after processing a few frames (~3-5 seconds).

### 🔄 Steps to Reproduce

1. Start Django server: `python manage.py runserver`
2. Create a session via Django admin
3. Run webcam stream: `python app/recognition/webcam_stream.py`
4. Start recognition: `POST /api/session/<uuid>/start/`
5. **Expected**: Frames process, faces detected
6. **Actual**: Server crashes with:
```
munmap_chunk(): invalid pointer
```

### 🎯 Root Cause

**Cross-thread Django buffer deallocation:**

The frame bytes are queued from Django's request buffer, which is deallocated after the HTTP request completes. The background thread then tries to decode these freed bytes, causing memory corruption:

```
Timeline:
1. upload_frame() receives request → Django allocates buffer
2. file = request.FILES["frame"].read() → references buffer
3. frame_queue.put_nowait(file) → queues reference (not copy!)
4. HTTP response sent, request ends → Django frees buffer
5. Background thread calls frame_queue.get() → receives invalid pointer
6. Memory access → CRASH
```

### ✅ Solution

Deep copy the frame bytes when queueing to ensure they remain valid after the request ends:

**File: `app/recognition/views.py` (line 132)**

```python
# Before (WRONG - references Django's buffer):
frame_queue.put_nowait(file)

# After (CORRECT - deep copy):
frame_queue.put_nowait(bytes(file))
```

Also ensure numpy arrays own their data:

**File: `app/recognition/recognition_runner.py` (lines 100-110)**

```python
frame_array = np.frombuffer(frame_bytes, np.uint8).copy()  # Own the data
frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

# Verify ownership
if frame is not None and not frame.flags['OWNDATA']:
    frame = frame.copy()
```

### 📦 Environment

- Python: 3.13.7
- Django: 5.2.1
- OpenCV: 4.x
- face_recognition: Latest
- OS: Linux (Arch)

### 🏷️ Labels

- Type: Bug
- Priority: Critical (blocks production mode)
- Component: Face Recognition
- Memory-Safety

### 🔗 Related

- Previous FIX #1: Cross-session contamination (now resolved)
- Performance optimization attempts
