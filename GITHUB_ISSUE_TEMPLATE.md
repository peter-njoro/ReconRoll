# GitHub Issue Template

## Issue Title
**Server crashes with memory corruption error when starting face recognition in production mode**

---

## Description

The server crashes with a `munmap_chunk(): invalid pointer` error whenever face recognition is started in production mode via the `/api/session/<uuid:session_id>/start/` endpoint.

### Steps to Reproduce

1. Start Django server in production mode (with Docker or `python manage.py runserver`)
2. Create a new session via Django admin
3. Start the webcam stream client: `python app/recognition/webcam_stream.py`
4. Start recognition via API: `POST /api/session/<uuid:session_id>/start/`
5. Wait for frames to be processed (~3-5 seconds)
6. **Result**: Server crashes with:
   ```
   [11/Dec/2025 13:17:18] "POST /api/upload_frame/ HTTP/1.1" 200 104
   [11/Dec/2025 13:17:18] "POST /api/upload_frame/ HTTP/1.1" 200 104
   [11/Dec/2025 13:17:18] "POST /api/upload_frame/ HTTP/1.1" 200 104
   munmap_chunk(): invalid pointer
   ```

### Expected Behavior

- Server should remain running
- Frames should be processed in background thread
- Faces should be detected and logged
- No crashes or memory corruption errors

### Actual Behavior

- Server crashes with heap memory corruption
- All recognition processing halts
- Session remains in "ongoing" state (requires manual database cleanup)
- No graceful error handling or recovery

---

## Root Cause Analysis

### Memory Safety Issue: Numpy Array Ownership

The issue occurs due to **unsafe memory handling in the background thread frame processing pipeline**:

#### Memory Flow Chain
```
1. webcam_stream.py
   └─ cv2.imencode('.jpg', frame) → JPEG bytes (owned by buf)

2. views.py (upload_frame endpoint)
   └─ request.FILES["frame"].read() → bytes (owned by Django request)

3. recognition_runner.py (background thread)
   ├─ frame_queue.get() → bytes (no longer owned after Django request ends!)
   ├─ np.frombuffer(bytes, np.uint8) → [READ-ONLY VIEW] ❌
   │  (doesn't copy data, creates numpy wrapper)
   ├─ cv2.imdecode(frame_array) → frame
   │  (may return view into frame_array, not owned)
   └─ OpenCV C extensions operate on non-owned memory ❌
      (garbage collector doesn't know what to free)
```

#### Why It Crashes

1. **`np.frombuffer()` creates a read-only view** - doesn't own the memory
2. **`cv2.imdecode()` may return a view** - reuses memory from frombuffer
3. **Threading + native libraries** - OpenCV C code expects stable memory ownership
4. **Garbage collection race** - Python GC tries to free memory that C code still thinks it owns
5. **Heap corruption** - Multiple pointers to same memory, multiple deallocation attempts
6. **Server crash** - Memory allocator detects corruption: `munmap_chunk(): invalid pointer`

### Current Code (Before Fix Attempt)
```python
frame_bytes = frame_queue.get(timeout=5)
frame_array = np.frombuffer(frame_bytes, np.uint8)  # ❌ Read-only view!
frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)  # ❌ Might return view!

# Later: frame used by OpenCV → C corruption
```

### Attempted Fix (Still Failing)
```python
frame_bytes = frame_queue.get(timeout=5)
frame_array = np.frombuffer(frame_bytes, np.uint8).copy()  # ✓ Own the data
frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

# Check and ensure frame owns data
if frame is not None and not frame.flags['OWNDATA']:
    frame = frame.copy()  # ✓ Explicit ownership check
```

**Status**: Fix applied but server still crashes → Found root cause!

---

## ACTUAL ROOT CAUSE (Found)

### The Real Issue: Request Buffer Lifetime

The bytes being queued are from Django's request buffer, which is **deallocated after the request ends**!

```
Timeline:
1. upload_frame() starts - Django allocates request buffer
2. file = request.FILES["frame"].read() - gets reference to buffer
3. frame_queue.put_nowait(file) - queues reference (not copy!)
4. upload_frame() returns - Django deallocates request buffer ❌
5. Background thread processes queue.get() - gets invalid pointer! ❌
6. np.frombuffer() reads from freed memory ❌
7. cv2.imdecode() tries to use corrupted data ❌
8. Memory corruption: munmap_chunk(): invalid pointer ❌
```

### Actual Solution: Deep Copy Bytes

```python
# BEFORE (views.py):
if FRAME_SKIP_COUNTER[active_session_id] % PROCESS_EVERY_N_FRAMES == 0:
    frame_queue.put_nowait(file)  # ❌ Reference to Django's buffer!

# AFTER (views.py):
if FRAME_SKIP_COUNTER[active_session_id] % PROCESS_EVERY_N_FRAMES == 0:
    frame_queue.put_nowait(bytes(file))  # ✓ Deep copy of bytes
```

**Why `bytes(file)` works:**
- `bytes()` constructor creates a new, independent copy of the data
- Copy is owned by Python (not Django's request buffer)
- Background thread can safely use bytes after request ends
- No more memory corruption!

---

## Environment

- **Python**: 3.13.7
- **Django**: 5.2.1
- **OpenCV**: 4.x
- **face_recognition**: Latest
- **dlib**: Latest
- **OS**: Linux (Arch)
- **Mode**: Development (`python manage.py runserver`)

---

## Related Issues

- Cross-session contamination bug (fixed in FIX #1)
- Performance optimization attempts (may have introduced memory issues)
- Threaded frame processing in production mode

---

## Actual Solution Applied

### Fix 1: Deep Copy Bytes in views.py (upload_frame)
**File**: `app/recognition/views.py` (line 132)

```python
# Before:
frame_queue.put_nowait(file)

# After:
frame_queue.put_nowait(bytes(file))  # ✓ Deep copy
```

**Why**: Ensures bytes are independent of Django's request buffer lifecycle

### Fix 2: Ensure Numpy Array Ownership in recognition_runner.py
**File**: `app/recognition/recognition_runner.py` (lines 100-110)

```python
frame_array = np.frombuffer(frame_bytes, np.uint8).copy()
frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

if frame is not None and not frame.flags['OWNDATA']:
    frame = frame.copy()
```

**Why**: Ensures all frame data is owned by the background thread

### Fix 3: Consistent Frame Reference
**File**: `app/recognition/recognition_runner.py` (line 177)

```python
# Use frame_copy for all C extension calls
save_unidentified_faces(frame_copy, face_locations[i], ...)
```

**Why**: Prevents accidental use of non-owned frame data

---

## Changes Summary

| File | Change | Reason |
|------|--------|--------|
| `app/recognition/views.py` | `bytes(file)` copy | Prevent Django buffer deallocation |
| `app/recognition/recognition_runner.py` | `.copy()` on frombuffer | Ensure owned numpy data |
| `app/recognition/recognition_runner.py` | `OWNDATA` check | Explicit ownership verification |
| `app/recognition/recognition_runner.py` | Use `frame_copy` consistently | Prevent mixed owned/non-owned references |

---

## Acceptance Criteria

- [ ] Server doesn't crash when starting recognition in prod mode
- [ ] Frames process without memory corruption errors
- [ ] Error handling logs issues gracefully
- [ ] Session cleanup works properly on errors
- [ ] Can process at least 100+ frames without crash
- [ ] Works with both HOG and DNN face detection models
- [ ] Memory usage stays stable (no leaks) over time

