# Memory Corruption Fix: "munmap_chunk(): invalid pointer"

## Problem
When running recognition in production mode, the server crashes with:
```
munmap_chunk(): invalid pointer
```

This is a **heap memory corruption error** from the C/OpenCV libraries, indicating that memory management went wrong during frame processing.

## Root Cause Analysis

The issue stemmed from **unsafe numpy memory ownership** in the frame processing pipeline:

### Memory Flow (Before Fix)
```
1. webcam_stream.py: Frame → cv2.imencode() → JPEG bytes (owned by buf)
2. views.py: bytes → np.frombuffer() → frame_array (READ-ONLY VIEW, doesn't own data!)
3. recognition_runner.py: frame_queue → np.frombuffer() → frame_array (read-only view)
4. cv2.imdecode(frame_array) → frame (potentially references frame_array's memory)
5. OpenCV operations on frame → C libraries get read-only/shared buffer
6. Garbage collection → Tries to free memory it doesn't own → CRASH!
```

### Why It Happens

1. **`np.frombuffer()` creates a read-only view** - it doesn't copy data, just creates a numpy wrapper
2. **`cv2.imdecode()` may return a view** - if the JPEG decoder optimization returns memory views instead of owned arrays
3. **OpenCV is a C extension** - it may expect to manage memory directly
4. **Threading amplifies the issue** - multiple threads touching shared memory buffers causes race conditions in memory management
5. **Garbage collection timing** - Python GC tries to free buffers in unpredictable order, and C code crashes when it encounters freed memory it thought it still owned

## Solution

### Fix 1: Own the Data Before Decode (recognition_runner.py)

**Changed:**
```python
frame_array = np.frombuffer(frame_bytes, np.uint8)
frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
```

**To:**
```python
# Convert frombuffer to owned array to avoid memory corruption
# frombuffer creates a read-only view; we need owned data for OpenCV
frame_array = np.frombuffer(frame_bytes, np.uint8).copy()
frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

# Ensure frame is owned data (imdecode should return owned data, but be explicit)
if frame is not None and not frame.flags['OWNDATA']:
    frame = frame.copy()
```

**Why:** 
- `.copy()` creates a new array that owns its data
- OpenCV operations now work with owned memory, not shared views
- Even if imdecode returns a view, we copy it to ensure ownership

### Fix 2: Use Consistent Frame Reference (recognition_runner.py)

**Changed:**
```python
cropped_path, full_path, saved_encoding = save_unidentified_faces(
    frame,  # <- Wrong! frame might be a view
    face_locations[i],
    ...
)
```

**To:**
```python
cropped_path, full_path, saved_encoding = save_unidentified_faces(
    frame_copy,  # <- Correct! frame_copy is owned
    face_locations[i],
    ...
)
```

**Why:** Ensures all C extension calls use the same owned frame copy, not mixed views

## Files Modified

- `app/recognition/recognition_runner.py`: Added explicit `.copy()` and ownership checks

## Testing

1. Start Django server in production mode
2. Create a test session via admin
3. Start recognition via `session/<uuid>/start/`
4. Monitor logs - should see no crashes, proper error handling
5. Multiple frames should process without "munmap_chunk" errors

## Key Takeaways for Future Development

1. **Always own numpy array data when passing to C extensions** - use `.copy()` after `np.frombuffer()`
2. **Check `array.flags['OWNDATA']`** - verify arrays own their memory before C operations
3. **Thread-safe memory** - C extensions are particularly vulnerable to shared memory across threads
4. **Profile memory** - use memory profilers to detect buffer leaks and ownership issues
5. **Test threaded code** - memory issues often appear under concurrent load, not in single-threaded tests

## Related Code Patterns to Avoid

```python
# ❌ BAD - Creates read-only view
arr = np.frombuffer(bytes_data, dtype=np.uint8)
result = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # May return view into arr

# ✅ GOOD - Creates owned array
arr = np.frombuffer(bytes_data, dtype=np.uint8).copy()
result = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # Safe to use
```

## Performance Impact

- **Minimal** - One extra `.copy()` call per frame in a background thread
- **Memory** - Temporary ~2.5x memory usage for frame (original bytes + copied array + decoded frame)
- **Trade-off** - Worth it to prevent server crashes with memory corruption

## References

- NumPy frombuffer: https://numpy.org/doc/stable/reference/generated/numpy.frombuffer.html
- OpenCV imdecode: https://docs.opencv.org/master/d4/da8/group__imgcodecs.html#ga288b8b3da0892bd651fac30d719b92aa
- Python Memory Model: https://docs.python.org/3/c-api/memory.html
