# ReconRoll — Release History

> Facial recognition attendance system. Originally built as *FaceTrack Lite*, rewritten and renamed in v2.
> Releases follow the **Demon Slayer Corps** ranking system, from Mizunoto (lowest) to Hashira (highest).
> See [README.md](README.md) for full system documentation.

---

## Release Index

| Version | Codename | Rank | Date | Status |
|---------|----------|------|------|--------|
| v3.0.0 | Toshi | 3rd Rank | TBD | 🔵 Planned |
| v4.0.0 | Ushi | 4th Rank | TBD | 🔵 Planned |
| v5.0.0 | Tora | 5th Rank | TBD | 🔵 Planned |
| [v2.0.0](#v200--mizunoe) | Mizunoe | 2nd Rank | 2025 | ✅ Released |
| [v1.0.0](#v100--mizunoto) | Mizunoto | 1st Rank | 2025 | ✅ Released |

---

## v2.x — ReconRoll Era

> The system was renamed from *FaceTrack Lite* to **ReconRoll** in this version.
> This is the last release with a graphical user interface. All future versions are headless.

---

### v2.0.0 — Mizunoe

**Released:** 2025
**Tag:** `v2.0.0-mizunoe`

#### Summary

Complete rewrite of FaceTrack Lite. The original project was a local-only Django app with a browser-based UI and SQLite database. ReconRoll replaces that with a REST API backend, a React SPA frontend, PostgreSQL, and a fully containerized deployment stack. The system can now run on a remote server and be accessed from any device on the network — the webcam no longer needs to be on the same machine as the backend.

This is the first version that is genuinely cloud-capable.

#### What Changed from v1

- **Architecture**: Monolithic Django views → Django REST Framework with a dedicated API layer
- **Frontend**: Server-rendered templates → React + Vite SPA communicating over HTTPS
- **Database**: SQLite → PostgreSQL
- **Deployment**: Local dev server → Docker Compose with nginx reverse proxy and uWSGI
- **Recognition pipeline**: Moved to a background thread (`recognition_runner.py`) with a frame queue, decoupled from the request/response cycle
- **Frame delivery**: Frontend captures webcam frames via canvas and POSTs them to the API every 500ms, enabling remote webcam support
- **Enrollment**: Multi-image enrollment with SHA-256 deduplication and cross-image identity verification
- **Session model**: Full session lifecycle — `scheduled → in_progress → completed / cancelled` — with race condition handling on thread registration
- **Data models**: `Person`, `FaceEncoding`, `Roster`, `Session`, `RosterAttendance`, `UnidentifiedFace`, `Event`
- **Media serving**: nginx serves enrolled face images and unknown face captures directly from a shared Docker volume
- **Roster scoping**: Recognition runs only against people expected in a session, not the entire database — reduces false positives and speeds up matching

#### Known Limitations

- GUI still required to operate the system (React frontend)
- dlib/`face_recognition` library is still the encoding backend — accurate but slow on CPU and difficult to extend
- No CLI or programmatic access outside the REST API
- HTTPS uses a self-signed certificate — not suitable for public deployment without replacement

---

## v1.x — FaceTrack Lite Era

> Released under the original project name. Archived for reference.

---

### v1.0.0 — Mizunoto

**Released:** 2025
**Tag:** `v1.0.0-mizunoto`

#### Summary

Initial release. A local facial recognition attendance system built as a Django application with server-rendered templates. The system ran entirely on a single machine — the webcam, backend, and browser all had to be on the same host. Built to demonstrate computer vision and Django skills as a GitHub portfolio project.

#### Features

- Django 4.x with server-rendered templates (no separate frontend framework)
- OpenCV-based face detection and dlib 128D face encodings via the `face_recognition` library
- SQLite database
- `AttendanceRecord` model tracking per-session attendance
- `enroll_view` for enrolling people with face image uploads
- `get_face_encodings` utility for extracting and storing encodings
- Face image uploads stored at `recognition/uploads/faces/`
- Basic session concept: start a session, run recognition against a webcam feed, view results
- LAN-accessible dev server via UFW + Docker port mapping

#### Limitations

- Local-only — no API, no remote access
- SQLite — not suitable for multi-user or concurrent sessions
- No background processing — recognition ran synchronously in the request cycle
- Browser-dependent — no headless or programmatic access
- No Docker deployment (added later during development, not part of the tagged release)

---

## Upcoming Releases

> From v3 onwards, ReconRoll has no graphical user interface.
> The focus shifts entirely to the recognition pipeline: model quality, inference speed, and accuracy.

---

### v3.0.0 — Toshi *(Planned)*

**Tag:** `v3.0.0-toshi`
**Theme:** Drop the GUI. Upgrade the model. Decouple the pipeline.

#### Goals

- Remove the React frontend entirely
- Introduce a **CLI** as the primary access method
  - `reconroll enroll` — enroll a person from images
  - `reconroll session` — start/stop a session, specify a roster
  - `reconroll report` — pull attendance summaries
- Replace dlib / `face_recognition` with **InsightFace (ArcFace model)**
  - Better accuracy on hard cases: similar-looking faces, varying angles, partial occlusion
  - Faster inference on CPU than dlib's ResNet
  - Actively maintained with ONNX export support
- Decouple the recognition pipeline from Django
  - Recognition logic lives in a standalone Python package with no Django dependency
  - Django is retained only for the database and API layer
  - Pipeline can be imported and used independently of the web server
- Introduce a basic benchmark script to establish an accuracy baseline

#### Non-Goals

- No GUI replacement
- No edge deployment optimizations yet
- No ONNX Runtime inference yet (planned for v4)

---

### v4.0.0 — Ushi *(Planned)*

**Tag:** `v4.0.0-ushi`
**Theme:** Speed. Async pipeline. SDK release.

#### Goals

- Export the ArcFace model to **ONNX** and replace the Python runtime with **ONNX Runtime**
  - Significant inference speedup on CPU
  - Removes the InsightFace runtime as a hard dependency for production
- Async frame processing pipeline
  - True async ingestion with `asyncio` or thread pool — no blocking on encode
  - Frame skipping with adaptive rate based on queue depth
- Introduce **encoding cache** — skip re-encoding people already confirmed present in a session
- Release the recognition pipeline as an installable **Python SDK**
  - `pip install reconroll`
  - Importable as a library for use in notebooks, other projects, benchmarks
- Benchmark suite expanded: speed benchmarks (frames/sec, latency per frame) alongside accuracy

#### Non-Goals

- No changes to enrollment or session management logic
- No edge-specific builds yet

---

### v5.0.0 — Tora *(Planned)*

**Tag:** `v5.0.0-tora`
**Theme:** Accuracy. Hard cases. Research-grade pipeline.

#### Goals

- **Multi-frame confirmation**: a person is only marked present after N consistent matches across separate frames, not a single hit
  - Eliminates lucky false positives from a single good frame
  - N is configurable per session
- **Confidence thresholding with rejection zones**: instead of a binary match/no-match on distance, introduce a rejection band — scores in an uncertain range are held, not committed
  - Only high-confidence matches update attendance
  - Uncertain matches are logged for manual review
- **Quality gating**: face crops are evaluated before encoding
  - Reject crops below a minimum size, above a blur threshold, or with poor face landmark confidence
  - Only high-quality crops feed into the matching pipeline
- **Accuracy benchmarks vs v3 baseline**: measure false positive rate, false negative rate, and recognition latency across a standardized test set
- Publish benchmark results in `docs/benchmarks.md`

#### Non-Goals

- No new access methods
- No model replacement (v3's ArcFace is the baseline being measured)

---

## Rank Reference

| Rank Name | Position | Assigned Version |
|-----------|----------|-----------------|
| Mizunoto | 1st (Lowest) | v1.0.0 |
| Mizunoe | 2nd | v2.0.0 |
| Toshi | 3rd | v3.0.0 |
| Ushi | 4th | v4.0.0 |
| Tora | 5th | v5.0.0 |
| Tatsu | 6th | — |
| Mi | 7th | — |
| Uma | 8th | — |
| Saru | 9th | — |
| Tori | 10th | — |
| Inu | 11th | — |
| I | 12th | — |
| Hashira | Highest | — |

---

*ReconRoll is a portfolio project by [Peter Njoroge Chege](https://www.linkedin.com/in/chege-peter/). Built for educational and demo purposes.*