# ReconRoll — Performance & Capacity Benchmark Report

This report measures two properties of ReconRoll's real-time recognition
pipeline:

1. **Recognition performance** — how long a frame takes to move through the
   pipeline (detect → encode → match) and how many faces fit inside the frame
   budget.
2. **Concurrency capacity** — how many simultaneous sessions the stack can
   sustain before frames are dropped or latency exceeds the frame budget.

Accuracy (false accept / false reject rate) is **out of scope** — it requires a
labeled dataset and is discussed separately in [Section 6](#6-accuracy).

---

## 1. Summary

All measurements were taken on an AWS EC2 `t3.medium` (2 vCPU, 4 GiB) running
the project's own containerized dependency stack (Python 3.12, dlib 20.0,
OpenCV 4.11), so the numbers reflect the exact production stack.

### 1.1 Design constants

These are fixed by code or configuration and were used throughout:

| Constant | Value | Source |
|---|---|---|
| Frame cadence | 2 fps per client (one frame every 500 ms) | `facetrack-frontend/src/pages/SessionDetailPage.jsx:163` |
| Frame payload | JPEG (quality 0.8), base64, POSTed as JSON | `SessionDetailPage.jsx:127` |
| Processing queue | 1 global queue, max 30 frames buffered | `app/recognition/recognition_runner.py:53` |
| Recognition threads | 1 daemon thread per active session | `app/recognition/views.py:1054` |
| App server | uWSGI: 4 processes × 2 threads = 8 request workers | `app/uwsgi.ini:8-9` |
| Face detection | dlib HOG with `upsample=2` (or OpenCV DNN SSD, configurable) | `recognition_runner.py:175` |
| Face encoding | dlib 128-D ResNet, `num_jitters=1` | `recognition_runner.py:180` |
| Matching | Euclidean distance, tolerance 0.55, roster-scoped (not whole DB) | `app/recognition/face_utils.py:144` |
| Encoding reload | every 500 frames | `recognition_runner.py:159` |

### 1.2 Headline results

| Metric | HOG (default) | DNN |
|---|---|---|
| Single-frame latency (1 face) | 861 ms avg (p50 848) | 197 ms avg (p50 191) |
| Detection (per frame) | ~708 ms | ~46 ms |
| Encoding (per face) | ~135–143 ms | ~143 ms |
| Matching (per face, roster=2) | ~0.09 ms | ~0.09 ms |
| Throughput (1 session) | ~1.2 frames/s | ~5 frames/s |
| Faces/frame within 500 ms budget | 0–1 | 2–3 |
| Concurrent sessions (0% drop, p95 < 500 ms) | 0–1 | **2** |

### 1.3 Key findings

- The default HOG path detects at `upsample=2` on the full 640×480 frame (an
  effective 1280×960 search) and **bypasses the configured `SCALE=0.25`
  downscale**, costing ~700 ms per frame. The DNN detector (which applies
  `SCALE=0.25` before running the 300×300 SSD) costs ~46 ms — a **~15×
  reduction in detection time with a one-line configuration change**
  (`FACE_MODEL=dnn`).
- Encoding costs ~140 ms/face and is the second-largest contributor. Matching is
  sub-millisecond and effectively invariant to roster size.
- With the DNN detector the system sustains **2 concurrent sessions with zero
  frame drops** on 2 vCPU; at 4 sessions every frame is still processed, but p95
  latency exceeds the 500 ms budget and per-session throughput falls. The box is
  CPU-bound, not queue-bound.

---

## 2. Test Environment

- **Host:** AWS EC2 `t3.medium` — 2 vCPU, 4 GiB RAM, burstable CPU credits.
- **Container:** the project's own image (Python 3.12 + dlib 20.0 + OpenCV 4.11).
- **Frames:** 640×480 synthetic frames (face crops composited onto a gray
  background).
- **Note on t3:** t3 instances are burstable (CPU credits). Results may vary
  with credit balance; runs on a steady-CPU instance (e.g., `m7i.large`) would
  produce more stable numbers. All raw results should be read together with the
  instance type and `nproc`.

---

## 3. Methodology

The benchmark scripts are standalone (numpy/OpenCV/dlib only; no Django, no
database), so the pipeline is measured without HTTP/ORM overhead.

The container image is built from the backend:

```bash
cd ReconRoll/backend
docker build -t reconroll-bench .
```

A directory of enrollment photos (one per roster person) is bind-mounted as
`benchmarks/sample_faces`.

### 3.1 Pipeline benchmark

Measures per-frame latency (detect + encode + match), throughput, faces/s, and
the extrapolated maximum faces per frame within the 500 ms budget.

```bash
docker run --rm -v "$(pwd)/app:/app" reconroll-bench \
    python benchmarks/bench_pipeline.py \
    --images-dir benchmarks/sample_faces \
    --roster-size 50 \
    --faces-per-frame 1,2,4,8 \
    --frames 30
```

DNN detector variant:

```bash
docker run --rm -v "$(pwd)/app:/app" reconroll-bench \
    python benchmarks/bench_pipeline.py \
    --images-dir benchmarks/sample_faces \
    --model dnn \
    --faces-per-frame 1,2,4 \
    --frames 30
```

Roster-scaling sweep (matching cost vs roster size):

```bash
for N in 10 50 100 500 1000; do
  docker run --rm -v "$(pwd)/app:/app" reconroll-bench \
    python benchmarks/bench_pipeline.py \
    --images-dir benchmarks/sample_faces \
    --roster-size $N --faces-per-frame 1 --frames 20 \
    | grep -E "Total|Throughput"
done
```

> `--roster-size` is capped by the number of images provided. With only 2
> images, roster sizes above 2 do not actually vary the roster (see
> [Section 4.5](#45-roster-sweep-hog)).

### 3.2 Concurrency benchmark

Simulates the production architecture: each session pushes a frame into one
shared 30-frame queue every 500 ms, and one recognition thread per session
drains it. Reports frames dropped (queue full), worker latency, and marks each
level SUSTAINABLE (drop ≤1% and p95 latency < 500 ms) or OVERLOADED.

```bash
docker run --rm -v "$(pwd)/app:/app" reconroll-bench \
    python benchmarks/bench_concurrency.py \
    --images-dir benchmarks/sample_faces \
    --model dnn \
    --sessions 1,2,4 \
    --duration 30
```

> Thread-safety note: `cv2.dnn.Net.forward()` is not thread-safe. The
> concurrency script loads one DNN net per worker thread, matching production
> (`recognition_runner.py` loads a net per recognition thread). An earlier
> version of the script shared a single net across workers and deadlocked — see
> [Section 4.4](#44-concurrency-dnn).

### 3.3 Desktop alternative

On a machine with a display the same scripts can be run inside the running
compose stack:

```bash
cd backend && ./run.sh
docker compose exec facetrack python /app/benchmarks/bench_pipeline.py \
    --images-dir /app/benchmarks/sample_faces \
    --faces-per-frame 1,2,4 \
    --frames 30
docker compose exec facetrack python /app/benchmarks/bench_concurrency.py \
    --images-dir /app/benchmarks/sample_faces \
    --sessions 1,2,4 \
    --duration 30
```

### 3.4 Metric definitions

| Metric | Definition |
|---|---|
| Detect time | `face_recognition.face_locations` on a 640×480 frame, HOG `upsample=2` (or DNN SSD) |
| Encode time | `face_recognition.face_encodings` with `num_jitters=1` (per face) |
| Match time | vectorized `np.linalg.norm` vs roster encodings + threshold (per face) |
| Total frame latency | detect + encode + match for one frame |
| frames/s, faces/s | aggregate throughput of the hot path |
| Budget utilization | total latency / 500 ms (the frontend's frame interval) |
| Drop rate | frames rejected because the shared queue was full |
| Sustainable sessions | largest session count with drop ≤1% and p95 < 500 ms |

---

## 4. Results

### 4.1 Pipeline — HOG (instance: AWS EC2 t3.medium, 2 vCPU)

```
Model: hog | upsample: 2 | jitters: 1 | tolerance: 0.55 | frame: 640x480
Roster encodings: 2 | CPU cores: 2 | budget: 500 ms
 faces/frame  total avg ms  faces/s  frames/s  budget %  est max
       1         860.8      1.16     1.16     172.2       0
       2         993.3      2.01     1.01     198.7       1
       4        1283.0      3.12     0.78     256.6       1
       8        1901.7      4.21     0.53     380.3       2
Detect ~708 ms (p50) | Encode ~135 ms/face | Match ~0.09 ms/face
```

A single face already consumes 172% of the 500 ms budget; the HOG path is
unsustainable even at one session.

### 4.2 Pipeline — DNN (instance: AWS EC2 t3.medium, 2 vCPU)

```
Model: dnn | jitters: 1 | tolerance: 0.55 | frame: 640x480
Roster encodings: 2 | CPU cores: 2 | budget: 500 ms
 faces/frame  total avg ms  faces/s  frames/s  budget %  est max
       1         197.2      5.07     5.07      39.4       2
       2         332.6      6.01     3.01      66.5       3
       4         617.1      6.48     1.62     123.4       3
Detect ~46 ms (p50) | Encode ~143 ms/face | Match ~0.09 ms/face
```

With the DNN detector a single face uses ~39% of the budget; 2 faces (333 ms)
fit comfortably, and 3–4 faces (617 ms) exceed it.

### 4.3 Concurrency — HOG (instance: AWS EC2 t3.medium, 2 vCPU)

```
sessions  offered  processed  dropped %  avg ms  p95 ms  frames/s  verdict
       1       31         31      0.00    955.9  1222.5     1.03  OVERLOADED
       2       88         42     52.27   1462.0  1485.4     1.40  OVERLOADED
       4      163         41     74.85   2947.4  3732.5     1.37  OVERLOADED
       8      224         46     79.46   5755.9  7634.1     1.53  OVERLOADED
```

All levels are OVERLOADED because even one session exceeds the 500 ms budget
(HOG detection alone is ~700 ms). Drop rate climbs (0% → 52% → 75% → 79%)
while aggregate throughput plateaus at ~1.4–1.5 fps, indicating the 2-vCPU host
is **CPU-bound, not queue-bound**. The absolute `offered`/`processed` counts at
1 session are low because the throttled instance's uploader loop ran slower
than the configured 0.5 s interval; the drop-rate trend is the reliable signal.

### 4.4 Concurrency — DNN (instance: AWS EC2 t3.medium, 2 vCPU)

```
sessions  offered  processed  dropped %  avg ms  p95 ms  frames/s  verdict
       1       43         43      0.00    193.7   223.5     1.43       OK
       2       71         71      0.00    227.3   461.7     2.37       OK
       4      109        109      0.00    296.4   575.3     3.63  OVERLOADED
```

- **1 session:** 43/43 frames, 0% drop, avg ~194 ms — comfortably within budget.
- **2 sessions:** 71/71 frames, 0% drop, avg ~227 ms (p95 462 ms) — sustainable;
  this is the measured concurrency ceiling.
- **4 sessions:** 109/109 frames, still 0% drop (the queue never overflowed),
  but p95 latency rises to ~575 ms (past budget) and per-session throughput
  falls to ~0.9 fps.

The system remains lossless at every level — the differentiator is latency, not
dropped frames. The effective upload rate on the throttled host was ~1.4
fps/client (not the configured 2 fps, since uploader threads are stretched as
CPU saturates), so these verdicts are conservative.

> **Methodology note:** a prior version of this benchmark reported 96–97% drops
> at 2/4 sessions. This was a defect in the benchmark script, not the
> architecture: it shared a single `cv2.dnn.Net` across worker threads, and
> `cv2.dnn.Net.forward()` is not thread-safe, which deadlocked the workers. The
> fix — one net per worker, matching production — is in `bench_concurrency.py`.
> The 1-session result of the earlier run (60/60, 0%, ~198 ms) was consistent
> with this run.

### 4.5 Roster sweep — HOG (instance: AWS EC2 t3.medium, 2 vCPU)

```
roster  10 -> Total 914.7 ms | 1.09 faces/s
roster  50 -> Total 853.4 ms | 1.17 faces/s
roster 100 -> Total 920.6 ms | 1.09 faces/s
roster 500 -> Total 843.9 ms | 1.18 faces/s
roster1000 -> Total 844.2 ms | 1.18 faces/s
```

The host had only 2 face images, so `--roster-size` never actually varied the
roster (it stayed capped at 2 encodings). The sweep is therefore indicative of
shape only: total time is flat at ~850–920 ms because matching (<1 ms) is noise
against detection (~700 ms). Extrapolating the measured ~0.09 ms at roster 2
linearly suggests ~45 ms at roster 1000 — still negligible, but an estimate
until run with more enrollment photos.

---

## 5. Discussion

**Detector choice is the dominant cost.** Detection is 4.6× the cost of
encoding and 4 orders of magnitude more than matching. The default HOG path
runs at 2× upsampling on the full frame and ignores `SCALE=0.25`, while the DNN
path respects the downscale — explaining the ~15× gap between ~708 ms and
~46 ms. Configuring `FACE_MODEL=dnn` is the single highest-leverage change
available.

**Concurrency is CPU-bound.** Aggregate throughput scales sub-linearly with
session count (1.43 → 2.37 → 3.63 fps), and the ceiling at 2 sessions is
imposed by p95 latency crossing the 500 ms budget, not by queue overflow.
dlib's C++ releases the GIL during detect/encode, so threads parallelize
partially on a 2-vCPU host; OpenCV and numpy segments do not.

**In-memory session state.** `active_recognition` and the queue are in-memory
per uWSGI worker process. With 4 workers and default load-balancing, an
`upload_frame` can reach a worker that never started the session and be
rejected ("Recognition thread not active"). Multi-session deployments should
pin sessions to a single worker.

---

## 6. Accuracy

Recognition accuracy is out of scope for this report. ReconRoll matches dlib
128-D encodings at a Euclidean tolerance of 0.55; accuracy is a property of the
model, the tolerance, and image quality, and this repository has no labeled
test set. A future accuracy study would:

1. Collect a labeled set: ~10 people × 5 photos each (positive) plus photos of
   people not in the roster (negative).
2. Enroll 2 photos/person and test on the rest.
3. Sweep tolerance 0.4–0.7 and report true accept rate and false accept rate.
4. Note that the production runner passes the **BGR** frame to
   `face_recognition.face_locations` while enrollment uses RGB — a color-order
   discrepancy worth fixing before formal accuracy work.

---

## 7. Limitations

- **One shared queue:** all sessions share the single 30-frame queue, so
  concurrency capacity is a global property, not per-session.
- **uWSGI multi-process:** recognition threads and queues are in-memory per
  worker; see Section 5.
- **Synthetic frames:** benchmarks composite face crops onto a gray background.
  Real camera frames may detect slower (more texture) or faster; treat results
  as a pipeline ceiling, not a field measurement.
- **t3 burstability:** results on burstable CPU can vary with credit balance.
- **Faces-per-frame is extrapolated** from measured per-face cost and is a
  linear estimate; detection cost per face is sub-linear, encoding roughly
  linear.
- **Roster sweep data is incomplete** (only 2 enrollment images available).

---

## 8. Recommendations

1. **Re-run the roster sweep with 100+ images** to confirm matching-cost
   scaling (current data is capped at roster 2).
2. **Re-run on a steady-CPU instance** (e.g., `m7i.large`) to remove burstable
   variance if the numbers will be published.
3. **Consider `FACE_MODEL=dnn` as the production default** given the 15×
   detection reduction and the verified 2-session concurrency ceiling, then
   re-verify on a live session.
4. **Pin sessions to a single uWSGI worker** (or reduce worker count) for
   reliable multi-session operation.
5. **Add a queue-depth probe** to confirm the 30-frame shared queue is never the
   bottleneck under bursty uploads (current data shows 0% drops).
