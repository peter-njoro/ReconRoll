# ReconRoll API Reference

All endpoints are prefixed with `/api/`. Authentication uses DRF token auth — include the token in the `Authorization` header as `Token <token>`.

---

## Auth

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/users/signup/` | Register a new user | No |
| `POST` | `/api/users/login/` | Log in and receive a token | No |
| `POST` | `/api/users/logout/` | Invalidate the current token | Yes |
| `GET` | `/api/users/me/` | Get the current user's profile | Yes |

---

## Enrollment

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/enroll/` | Enroll a new person with one or more face images | No |
| `GET` | `/api/enroll/progress/` | Poll enrollment processing progress | No |

---

## People

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/people/` | List all people who have face encodings | Yes |
| `GET` | `/api/people/<id>/` | Get details for a specific person | Yes |

---

## Rosters

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/rosters/` | List all rosters | Yes |
| `POST` | `/api/roster/create/` | Create a new roster | Yes |
| `GET` | `/api/roster/<id>/` | Get a roster and its people | Yes |
| `POST` | `/api/roster/<id>/update/` | Update a roster's name, description, or people | Yes |
| `DELETE` | `/api/roster/<id>/delete/` | Delete a roster | Yes |

---

## Sessions

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/sessions/` | List all sessions | Yes |
| `POST` | `/api/session/create/` | Create a new session | Yes |
| `GET` | `/api/session/<id>/` | Get session details and attendance summary | Yes |
| `POST` | `/api/session/<id>/start/` | Start the recognition thread for a session | Yes |
| `POST` | `/api/session/<id>/stop/` | Stop the recognition thread and complete the session | Yes |
| `POST` | `/api/sessions/stop-all/` | Stop all currently running sessions | Yes |
| `POST` | `/api/sessions/<id>/upload_frame/` | Upload a webcam frame for processing | Yes |

---

## Session Data

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/session/<id>/present_partial/` | Get present people for a session | Yes |
| `GET` | `/api/session/<id>/absent_partial/` | Get absent people for a session | Yes |
| `GET` | `/api/session/<id>/events_partial/` | Get the event log for a session | Yes |
| `GET` | `/api/session/<id>/unidentified_partial/` | Get unidentified face captures for a session | Yes |
| `GET` | `/api/session/<id>/progress_partial/` | Get attendance progress stats for a session | Yes |

---

## Misc

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/info/` | System info and feature overview | No |
| `GET` | `/api/csrf/` | Get a CSRF token | No |
