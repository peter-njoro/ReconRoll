---

# **ReconRoll — Intelligent Facial Recognition Attendance System**

<p align="center">
  <img src="docs/logo.svg" width="420">
</p>

<p align="center">
  <strong>Fast · Modular · Real-Time Facial Recognition Attendance System</strong><br/>
  Built with Django, OpenCV, and Deep Learning–Based Face Encodings
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/status-active-brightgreen?style=flat-square" /></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square" /></a>
  <a href="#"><img src="https://img.shields.io/badge/framework-Django-darkgreen?style=flat-square" /></a>
  <a href="#"><img src="https://img.shields.io/badge/vision-OpenCV-critical?style=flat-square" /></a>
  <a href="#"><img src="https://img.shields.io/badge/license-GPLv3-orange?style=flat-square" /></a>
</p>

---

## Overview

**ReconRoll** is a real-time facial recognition attendance system. A user starts a session, points a webcam at a room, and the system automatically identifies people, marks them present or absent, captures unidentified faces for review, and produces a full attendance summary when the session ends.

The system is roster-based — each session is scoped to a specific list of expected people, so recognition only runs against the faces that are actually supposed to be there. This keeps matching fast and reduces false positives.

It was originally built as *FaceTrack Lite* and has since been rewritten with a proper REST API, a React frontend, and a containerized deployment stack.

---

## Tech Stack

| Technology           | Purpose                                          |
| -------------------- | ------------------------------------------------ |
| **Python 3.10+**     | Core backend language                            |
| **Django 5**         | Web framework, ORM, admin                        |
| **Django REST Framework** | API layer, token authentication, viewsets   |
| **dlib / face_recognition** | 128D face encoding and matching         |
| **OpenCV**           | Frame decoding, face detection (HOG + DNN), image I/O |
| **PostgreSQL**       | Primary database                                 |
| **React + Vite**     | Frontend SPA                                     |
| **nginx**            | Reverse proxy, HTTPS termination, media serving  |
| **uWSGI**            | WSGI application server                          |
| **Docker**           | Containerized deployment                         |

---

## System Architecture

The backend is a Django application served by uWSGI, sitting behind an nginx reverse proxy. The React frontend communicates with it over HTTPS via a REST API authenticated with DRF token auth.

### Recognition Pipeline

When a session is started, the backend spawns a background thread (`recognition_runner.py`) and registers it in an in-memory `active_recognition` dict keyed by session ID. The thread blocks on a `queue.Queue`, waiting for frames.

The frontend captures webcam frames via `canvas.toDataURL`, converts them to JPEG blobs, and POSTs them as multipart form data to `/api/sessions/<id>/upload_frame/` every 500ms. The `SessionViewSet.upload_frame` action validates the session state, checks that the recognition thread is active, and drops the frame bytes into the queue (max 30 frames buffered).

The background thread pulls frames from the queue and runs:

1. **Face detection** — HOG model by default (configurable to DNN via `FACE_MODEL=dnn`). Frames are scaled down by `SCALE` (default 0.25) before detection for speed. Faces smaller than `MIN_FACE_SIZE` pixels are ignored.
2. **Face encoding** — dlib's 128D face encoding via the `face_recognition` library. The background thread uses `number_of_times_to_upsample=2` for better accuracy since it's not on the hot path.
3. **Matching** — Euclidean distance comparison against known encodings loaded from the database. Match threshold is controlled by `TOLERANCE` (default 0.55). Encodings are scoped to the session's roster — only the expected people are loaded, not the entire database.
4. **Attendance recording** — On a match, a `RosterAttendance` record is created or updated with status `present` or `late` (late if recognition time is after `session.start_time`). Events are logged to the `Event` table.
5. **Unknown faces** — Faces that don't match any known encoding and haven't been seen before in this session are saved to disk (cropped face + full annotated frame) and recorded in `UnidentifiedFace`. Duplicate unknowns are suppressed by comparing against a session-local encoding cache.

The thread self-terminates when the stop flag is set or when it detects the session has been marked `completed` or `cancelled` in the database.

### Enrollment

People are enrolled via `POST /api/enroll/` with one or more face images. The backend:

- Detects and encodes each image
- Rejects images with no face or multiple faces
- Cross-checks all images against the first to confirm they're the same person
- Deduplicates using SHA-256 hashes of the raw image bytes
- Stores the 128D encoding as a serialized numpy array (`BinaryField`) in `FaceEncoding`, linked to a `Person` record

### Session Lifecycle

Sessions move through four states: `scheduled → in_progress → completed / cancelled`.

- `POST /api/session/<id>/start/` — registers the recognition thread in `active_recognition` before setting the DB status to `in_progress`, avoiding a race condition where the frontend polls for `in_progress` and immediately fires frames before the thread is ready
- `POST /api/session/<id>/stop/` — sets the stop flag, waits for the thread to exit, marks the session `completed`
- If the thread crashes, it catches the exception, marks the session `cancelled`, and logs an error event

### Data Models

| Model | Purpose |
|---|---|
| `Person` | Enrolled individual with identification number |
| `FaceEncoding` | 128D numpy encoding stored as binary, linked to a Person |
| `Roster` | Reusable list of expected people |
| `Session` | A single attendance session, optionally linked to a Roster |
| `RosterAttendance` | Per-person attendance status for a session (present/absent/late) |
| `AttendanceSummary` | Fallback attendance table for sessions without a roster |
| `UnidentifiedFace` | Cropped face + full frame for unrecognized detections |
| `Event` | Audit log of recognition events, session start/stop, errors |

### Media & File Storage

Enrolled face images and unidentified face captures are written to `MEDIA_ROOT` (`/vol/media` in Docker), which is a named volume shared between the Django container and nginx. nginx serves `/media/` directly from this volume without proxying through Django.

---

## API Documentation

A full API reference is available in [`docs/api.md`](docs/api.md). An OpenAPI 3.0 spec is also available at [`docs/openapi.yaml`](docs/openapi.yaml) — load it into Swagger UI, Redoc, or Postman to browse and test endpoints interactively.

## Releases & Roadmap

[`docs/releases.md`](docs/releases.md) tracks the full release history and planned versions. Releases follow the Demon Slayer Corps ranking system (Mizunoto → Hashira). Each entry covers what changed, what was dropped, and what the next version is targeting.

---

## Benchmarks

Measured on an AWS EC2 t3.medium (2 vCPU, 4 GiB) with the project's own containerized stack. Full methodology, raw results, and limitation notes: [`docs/benchmarks.md`](docs/benchmarks.md).

| Metric | HOG (default) | DNN |
|---|---|---|
| Frame latency, 1 face (detect + encode + match) | ~860 ms | **~200 ms** |
| Face detection (per frame) | ~708 ms | **~46 ms** |
| 128-D encoding (per face) | ~140 ms | ~140 ms |
| Throughput (1 session) | ~1.2 frames/s | **~5 frames/s** |
| Faces/frame within 500 ms budget | 0–1 | **2–3** |
| Concurrent sessions, 0% drop | 0–1 | **2** |

**Takeaways:**

- The bundled **DNN detector is ~15× faster** than the default HOG path (46 ms vs 708 ms per frame) — switch with `FACE_MODEL=dnn`.
- Matching is **roster-scoped and sub-millisecond**, so frame latency barely grows with the number of enrolled people.
- Sustains **2 concurrent sessions with zero frame drops** on a 2-vCPU box; 4 sessions still process every frame but cross the 500 ms latency budget.

---

## Deployment

### Docker (Recommended)

Requires a Linux host with Docker and a connected webcam.

```bash
git clone https://github.com/peter-njoro/ReconRoll.git
cd ReconRoll/backend
cp .env.example .env   # fill in your values
chmod +x scripts/scripts.sh
docker compose -f docker-compose.linux.yml up --build
```

The app will be available at `https://<your-host-ip>`. nginx handles HTTPS termination using a self-signed certificate (replace with a real cert for production).

On startup, the entrypoint script runs migrations, collects static files, and optionally starts `webcam_stream.py` as a background frame forwarder if `FRAME_FORWARDER=true`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FACE_MODEL` | `hog` | Detection model: `hog` or `dnn` (`dnn` is ~15× faster — see [Benchmarks](#benchmarks)) |
| `SCALE` | `0.25` | Frame scale factor before detection |
| `TOLERANCE` | `0.55` | Face match threshold (lower = stricter) |
| `MIN_FACE_SIZE` | `100` | Minimum face size in pixels |
| `MEDIA_ROOT` | `/vol/media` | Where uploaded and captured images are stored |
| `FRAME_FORWARDER` | `false` | Start the server-side webcam stream daemon |
| `DEBUG` | `True` | Django debug mode |

---

## Disclaimer

ReconRoll is built for educational and demo purposes. It is not hardened for high-security or large-scale production deployments.

---

## Author

**[Peter Njoroge Chege](https://www.linkedin.com/in/chege-peter/)**
Machine Learning Engineer (In Progress)
AI • Computer Vision • Backend Engineering

Inspired by the original **Virone** concept by **[Everlyne Mwangi](https://www.linkedin.com/in/everlyne-mwangi-2509b9278/)**.

---

## Developer Notes

If you're reading this part:

* Yes, pip errors still haunt me.
* Docker promised peace, webcams declared war.
* ReconRoll is both a demo *and* a flex.
* And yes… by the way… I use Arch btw 🟟.
* If this becomes Skynet, at least the README will survive.

---
