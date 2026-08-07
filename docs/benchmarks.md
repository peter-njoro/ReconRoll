# ReconRoll — Testing & Benchmark Plan

The goal of this document is to produce **defensible numbers**. Two things are measured:

1. **Recognition performance** — how fast a frame moves through the pipeline
   (detect → encode → match) and how many faces fit inside the frame budget.
2. **Concurrency capacity** — how many users/sessions the stack handles at once
   before frames start being dropped.

Accuracy (false accept / false reject rate) is **not** measured here — it needs a
labeled dataset and is covered separately at the end of this document.

---

## TL;DR — the numbers you can attach to the project

Two categories:

### A. Design constants (fixed by code/config — safe to quote today)

| Constant | Value | Source |
|---|---|---|
| Frame cadence | **2 fps per client** (one frame every 500 ms) | `facetrack-frontend/src/pages/SessionDetailPage.jsx:163` |
| Frame payload | JPEG (quality 0.8), base64, POSTed as JSON | `SessionDetailPage.jsx:127` |
| Processing queue | **1 global queue, max 30 frames buffered** | `app/recognition/recognition_runner.py:53` |
| Recognition threads | **1 daemon thread per active session** | `app/recognition/views.py:1054` |
| App server | **uWSGI: 4 processes × 2 threads = 8 request workers** | `app/uwsgi.ini:8-9` |
| Face detection | dlib **HOG** with `upsample=2` (or OpenCV **DNN SSD**, configurable) | `recognition_runner.py:175` |
| Face encoding | dlib **128-D ResNet**, `num_jitters=1` | `recognition_runner.py:180` |
| Matching | **Euclidean distance**, tolerance 0.55, **roster-scoped** (not whole DB) | `app/recognition/face_utils.py:144` |
| Encoding reload | every 500 frames | `recognition_runner.py:159` |

### B. Measured numbers (run the scripts below, then fill in)

| Metric | t3.medium result | Notes |
|---|---|---|
| Single-frame recognition latency (1 face) | *to fill* ms | avg over ≥30 frames |
| Faces per frame within the 500 ms budget | *to fill* | 1–2 expected on 2 vCPU |
| Roster size before matching degrades | *to fill* | latency vs roster sweep |
| Max concurrent sessions, <1% frame drop | *to fill* | 2–4 expected on 2 vCPU |
| Aggregate throughput at max concurrency | *to fill* faces/s | |

> Expected ballpark on a t3.medium (2 vCPU, ~3.0–3.3 GHz, no AVX2 turbo
> guarantees): HOG detect ~30–80 ms, 128-D encode ~120–300 ms/face, matching
> <1 ms per 1000 encodings → **~200–450 ms per single-face frame**. These are
> *estimates to sanity-check against*, not measurements.

---

## Environment

- **Target host:** AWS EC2 `t3.medium` (2 vCPU, 4 GiB RAM, Burstable CPU).
- **Container:** the project's own image (Python 3.12 + dlib 20.0 + OpenCV 4.11),
  so numbers reflect the exact production dependency stack.
- Always record `nproc` and the instance type next to results — they are not
  transferable across hardware.
- For a stable t3.medium baseline, consider a `c`-family or `c7g` instance if the
  number is going on a resume; otherwise disclose that t3 is burstable (CPU
  credits). A quick alternative is an `m7i.large` (2 vCPU, steady) and label the
  result with that instance type instead.

---

## Setup on AWS

The benchmark scripts are **standalone** (numpy/OpenCV/dlib only; no Django, no
database). The container already has these deps baked in.

```bash
cd ReconRoll
cd backend
docker build -t reconroll-bench .

# Drop 10–30 face photos here so the bind mount exposes them to the container
mkdir -p app/benchmarks/sample_faces
#   ... copy face images (one per roster person, e.g. from your enrollment photos) ...
```

> `run.sh` also works on a desktop (it wires up webcam + X11/Wayland display).
> On headless EC2 those device/display mounts don't exist, so use the
> `docker build` / `docker run` path above. Both run the exact same image.

---

## Running the benchmarks

### 1. Pipeline (per-frame latency, faces-per-frame, roster scaling)

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

> `--roster-size` is capped by the number of images you provide. If you have 20
> photos you can only test roster sizes ≤ 20; for a 1000-person sweep, reuse the
> same encodings by generating many slightly different crops, or state the roster
> size you did test and scale the (already negligible) matching term linearly.

### 2. Concurrency (max simultaneous users)

```bash
docker run --rm -v "$(pwd)/app:/app" reconroll-bench \
    python benchmarks/bench_concurrency.py \
    --images-dir benchmarks/sample_faces \
    --sessions 1,2,4,8 \
    --duration 30
```

This simulates the real architecture: each session pushes a frame into **one
shared 30-frame queue** every 500 ms, and **one recognition thread per session**
drains it. It reports frames dropped (queue full), worker latency, and marks each
level SUSTAINABLE (drop ≤1% and p95 latency < frame interval) or OVERLOADED.

### 3. On a desktop via `run.sh`

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

### 4. Full end-to-end (optional, needs DB + a running session)

Not covered by the standalone scripts. To measure "frame POST → attendance row
written":

1. Start the stack (`./run.sh`).
2. Create a session with a roster, start it (prod mode).
3. POST frames with `curl` from the host at 2 fps for 60 s.
4. Time the round-trip (`upload_frame` response) and check the `Event` table
   timestamps for recognition latency.

---

## Metric definitions

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

## How to phrase the numbers (fill in the blanks)

> ReconRoll is a Django + React real-time facial-recognition attendance system.
> On an AWS t3.medium (2 vCPU) it processes a full recognition frame —
> dlib HOG detection, 128-D encoding, and matching against a **X-person roster** —
> in **~Y ms**, sustaining **Z fps**. It handles **N concurrent sessions** (one
> recognition thread each, 2 fps per client) with **<1% frame drop**, behind a
> uWSGI server (4 processes × 2 threads) with a 30-frame processing buffer.

Recruiter-friendly bullets once you have numbers:

- "Processes recognition in under **Y ms** per frame on a **t3.medium** (2 vCPU)."
- "Recognizes up to **K faces per frame** while keeping latency inside the
  **500 ms** frame budget."
- "Supports **N simultaneous users/sessions**, each streaming 2 fps."
- "Matching is **roster-scoped**, so latency scales with expected attendees, not
  the whole database."
- "1 recognition thread per session; 8 uWSGI request workers; 30-frame buffer."

---

## Accuracy (why it isn't in this benchmark)

ReconRoll's matching uses `dlib`'s 128-D encodings with a Euclidean tolerance of
0.55. Recognition accuracy is a property of the dlib model + your tolerance +
image quality — this repo has **no labeled test set**, so a project-specific
accuracy number can't be honestly produced without building one.

To get one later (e.g., for v5 "Toshi" which already plans accuracy benchmarks):

1. Collect a labeled set: ~10 people × 5 photos each (positive) + photos of
   people not in the roster (negative).
2. Enroll 2 photos/person, test on the rest.
3. Sweep tolerance 0.4–0.7; report true accept rate and false accept rate at each.
4. Note: HOG detection in the production runner passes the **BGR** frame to
   `face_recognition.face_locations` (accuracy-relevant quirk), while enrollment
   uses RGB — worth fixing before formal accuracy work.

---

## Limitations & honesty notes

- **One shared queue**: all sessions share the single 30-frame queue, so
  concurrency capacity is a global property, not per-session. This is the real
  ceiling the concurrency benchmark measures.
- **uWSGI multi-process**: `active_recognition` and the queue are **in-memory per
  worker process**. With 4 workers and default load-balancing, an `upload_frame`
  can hit a worker that never started that session and get rejected ("Recognition
  thread not active"). For reliable multi-session operation, pin a session to one
  worker (e.g., a single uWSGI worker) — worth stating if asked.
- **GIL**: dlib's C++ releases the GIL during detect/encode, so 2 threads
  genuinely parallelize on a 2-vCPU box; OpenCV and numpy segments do not.
- **Synthetic frames**: benchmarks paste face crops onto a gray background.
  Real camera frames may detect slower (more texture) or faster (fewer/more
  faces); treat results as a pipeline ceiling, not a field measurement.
- **t3 burstability**: t3.medium is burstable (CPU credits). For stable/resume
  numbers run on a steady-CPU instance type and record which you used.
- **Faces-per-frame is extrapolated** from the measured per-face cost and is a
  linear estimate; detection cost per face is sub-linear, encoding is roughly
  linear.

---

## Results log

Paste the tables from each run here with the host/instance noted.

### Run 1 — pipeline (instance: _____, date: _____)

```
(replace with bench_pipeline.py output)
```

### Run 2 — concurrency (instance: _____, date: _____)

```
(replace with bench_concurrency.py output)
```
