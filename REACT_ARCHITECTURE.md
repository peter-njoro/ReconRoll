# React Frontend Architecture Overview

## Current Architecture (Monolithic)

```
┌─────────────────────────────────────────────────────────┐
│                    Django Application                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │           Django URL Router (urls.py)            │ │
│  └──────────────────────────────────────────────────┘ │
│                        │                               │
│  ┌─────────────────────┴──────────────────────────┐   │
│  │                                                │   │
│  ▼                                                ▼   │
│ ┌───────────────┐ ┌───────────────┐ ┌──────────────┐ │
│ │ View Functions│ │  Serializers  │ │   Models     │ │
│ │ (views.py)    │ │   (forms.py)  │ │ (models.py)  │ │
│ └───────────────┘ └───────────────┘ └──────────────┘ │
│        │                                               │
│        ▼                                               │
│ ┌──────────────────────────────────────────────────┐ │
│ │         Django Templates (server-side)           │ │
│ │ ├─ base.html                                     │ │
│ │ ├─ index.html                                    │ │
│ │ ├─ enroll.html                                   │ │
│ │ ├─ session_list.html                             │ │
│ │ └─ session_detail.html                           │ │
│ └──────────────────────────────────────────────────┘ │
│        │                                               │
│        ▼                                               │
│ ┌──────────────────────────────────────────────────┐ │
│ │    Django Static Files (CSS, JS)                 │ │
│ │ ├─ custom.css                                    │ │
│ │ ├─ enroll_loading.js                             │ │
│ │ └─ session_detail.js                             │ │
│ └──────────────────────────────────────────────────┘ │
│        │                                               │
│        ▼                                               │
│  [ HTML Response to Browser ]                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
                  [ Web Browser ]
                  Renders HTML
```

## Target Architecture (Decoupled SPA + API)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  ┌──────────────────────────────────┐   ┌──────────────────────────────┐ │
│  │    Django REST API Backend       │   │    React SPA Frontend        │ │
│  │    (localhost:8000/api)          │   │    (localhost:5173)          │ │
│  ├──────────────────────────────────┤   ├──────────────────────────────┤ │
│  │                                  │   │                              │ │
│  │ ┌────────────────────────────┐  │   │ ┌──────────────────────────┐ │ │
│  │ │   REST API Endpoints       │  │   │ │  React Components        │ │ │
│  │ ├────────────────────────────┤  │   │ ├──────────────────────────┤ │ │
│  │ │ GET    /api/sessions/      │  │   │ │ ├─ SessionList.jsx       │ │ │
│  │ │ POST   /api/sessions/      │  │   │ │ ├─ SessionDetail.jsx     │ │ │
│  │ │ POST   /api/sessions/{id}/ │  │   │ │ ├─ EnrollmentForm.jsx    │ │ │
│  │ │ start/                     │  │   │ │ ├─ StudentList.jsx       │ │ │
│  │ │                            │  │   │ │ └─ Navbar.jsx            │ │ │
│  │ │ GET    /api/students/      │  │   │ │                          │ │ │
│  │ │ POST   /api/students/      │  │   │ └──────────────────────────┘ │ │
│  │ │ POST   /api/upload_frame/  │  │   │                              │ │
│  │ └────────────────────────────┘  │   │ ┌──────────────────────────┐ │ │
│  │          │                       │   │ │  Custom Hooks            │ │ │
│  │          │                       │   │ ├──────────────────────────┤ │ │
│  │          ▼                       │   │ │ ├─ useSession.js         │ │ │
│  │ ┌────────────────────────────┐  │   │ │ ├─ useEnrollment.js      │ │ │
│  │ │    Models & Database       │  │   │ │ └─ useFaceRecognition.js │ │ │
│  │ │ ├─ Session                 │  │   │ └──────────────────────────┘ │ │
│  │ │ ├─ Student                 │  │   │                              │ │
│  │ │ ├─ AttendanceRecord        │  │   │ ┌──────────────────────────┐ │ │
│  │ │ ├─ UnidentifiedFace        │  │   │ │  State Management        │ │ │
│  │ │ └─ Event                   │  │   │ ├──────────────────────────┤ │ │
│  │ └────────────────────────────┘  │   │ │ ├─ sessionStore.js       │ │ │
│  │          │                       │   │ │ ├─ authStore.js          │ │ │
│  │          ▼                       │   │ │ └─ enrollmentStore.js    │ │ │
│  │ ┌────────────────────────────┐  │   │ └──────────────────────────┘ │ │
│  │ │    Serializers (DRF)       │  │   │                              │ │
│  │ │ ├─ SessionSerializer       │  │   │ ┌──────────────────────────┐ │ │
│  │ │ ├─ StudentSerializer       │  │   │ │  API Service Layer       │ │ │
│  │ │ └─ EventSerializer         │  │   │ ├──────────────────────────┤ │ │
│  │ └────────────────────────────┘  │   │ │ ├─ sessionService.js     │ │ │
│  │                                  │   │ │ ├─ studentService.js     │ │ │
│  │                                  │   │ │ └─ frameService.js       │ │ │
│  │                                  │   │ └──────────────────────────┘ │ │
│  │                                  │   │                              │ │
│  │                                  │   │ ┌──────────────────────────┐ │ │
│  │                                  │   │ │  React Router            │ │ │
│  │                                  │   │ ├──────────────────────────┤ │ │
│  │                                  │   │ │ /                        │ │ │
│  │                                  │   │ │ /sessions                │ │ │
│  │                                  │   │ │ /session/:id             │ │ │
│  │                                  │   │ │ /enroll                  │ │ │
│  │                                  │   │ └──────────────────────────┘ │ │
│  │                                  │   │                              │ │
│  │                                  │   │ ┌──────────────────────────┐ │ │
│  │                                  │   │ │  Styling                 │ │ │
│  │                                  │   │ ├──────────────────────────┤ │ │
│  │                                  │   │ │ ├─ Tailwind CSS           │ │ │
│  │                                  │   │ │ └─ main.css              │ │ │
│  │                                  │   │ └──────────────────────────┘ │ │
│  └──────────────────────────────────┘   └──────────────────────────────┘ │
│         │                                         │                      │
│         │      REST API (JSON)                    │                      │
│         │  ◄──────────────────────────────────►   │                      │
│         │                                         │                      │
└────────────────────────────────────────────────────────────────────────────┘
                         │                           │
                         └──────────┬────────────────┘
                                    │
                         [ Network / Internet ]
                                    │
                         ┌──────────▼────────────┐
                         │    Web Browser        │
                         │ (Shows React App)     │
                         └───────────────────────┘
```

## Component Hierarchy

```
App (Main Component)
├── <Router>
│   ├── <Navbar />
│   │   ├── Logo
│   │   ├── Navigation Links
│   │   └── User Profile
│   │
│   └── <Routes>
│       ├── / ─────────────► <Home />
│       │
│       ├── /sessions ─────► <SessionList />
│       │                   ├── Session Cards
│       │                   │   ├── SessionCard
│       │                   │   │   ├── Subject
│       │                   │   │   ├── Status Badge
│       │                   │   │   └── View Button
│       │                   │   └── [...]
│       │                   └── [Create New] Button
│       │
│       ├── /session/:id ──► <SessionDetail />
│       │                   ├── Header
│       │                   ├── Statistics Cards
│       │                   │   ├── Present Count
│       │                   │   ├── Absent Count
│       │                   │   ├── Unknown Count
│       │                   │   └── Status
│       │                   ├── Control Panel
│       │                   │   ├── [Start] / [Stop] Button
│       │                   │   └── [Export] Button
│       │                   ├── Tabs
│       │                   │   ├── Present Students
│       │                   │   │   └── StudentList
│       │                   │   │       └── StudentRow
│       │                   │   ├── Absent Students
│       │                   │   │   └── StudentList
│       │                   │   ├── Unknown Faces
│       │                   │   │   └── FaceGrid
│       │                   │   │       └── FaceCard
│       │                   │   └── Events Log
│       │                   │       └── EventList
│       │                   │           └── EventRow
│       │                   └── Real-time Status Panel
│       │
│       ├── /enroll ────────► <EnrollmentForm />
│       │                   ├── Form
│       │                   │   ├── Name Input
│       │                   │   ├── Student ID Input
│       │                   │   ├── Class Group Dropdown
│       │                   │   └── Image Upload (Multiple)
│       │                   ├── Image Preview Grid
│       │                   │   └── ImagePreview
│       │                   ├── Progress Bar
│       │                   └── [Submit] Button
│       │
│       └── /404 ──────────► <NotFound />
```

## Data Flow Example: Starting a Session

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Component                           │
│                   <SessionDetail />                              │
│                   Displays: Subject, Status,                     │
│                   Statistics, [Start] Button                     │
└──────────────────┬───────────────────────────────────────────────┘
                   │
         User clicks [Start]
                   │
                   ▼
    ┌──────────────────────────────┐
    │  startSession() Handler       │
    │  (from useSession hook)       │
    └──────────────┬────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │ sessionService.startSession(sessionId)       │
    │ Makes API call via axios                     │
    └──────────────┬───────────────────────────────┘
                   │
         HTTP Request (JSON)
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │   Django REST API Endpoint                   │
    │   POST /api/sessions/{id}/start/             │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │  SessionViewSet.start() Method               │
    │  1. Get session from DB                      │
    │  2. Create stop_flag (threading.Event)       │
    │  3. Create recognition thread                │
    │  4. Update session.status = 'ongoing'        │
    │  5. Save to DB                               │
    │  6. Return success response                  │
    └──────────────┬───────────────────────────────┘
                   │
         HTTP Response (JSON)
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │ Response Handler in React                    │
    │ {status: 'started', session_id: '...'}       │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │ Update React State                           │
    │ setSession({...session, status: 'ongoing'})  │
    └──────────────┬───────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────────────────┐
    │ Component Re-renders                         │
    │ - Show [Stop] button instead of [Start]      │
    │ - Update status badge to "ongoing"           │
    │ - Poll server every 2s for updates           │
    └──────────────────────────────────────────────┘
```

## File Structure After Migration

```
ReconRoll/
├── app/                          # Django Backend
│   ├── config/
│   │   ├── settings.py          # ← Add DRF, CORS
│   │   ├── urls.py              # ← Add API routes
│   │   └── wsgi.py
│   │
│   ├── recognition/
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py             # ← Keep for legacy HTML
│   │   ├── api.py               # ← NEW: ViewSets
│   │   ├── serializers.py       # ← NEW: Serializers
│   │   ├── urls.py
│   │   ├── recognition_runner.py
│   │   ├── face_utils.py
│   │   ├── webcam_stream.py
│   │   ├── templates/           # ← Can deprecate
│   │   └── static/              # ← Can deprecate
│   │
│   ├── users/
│   │   └── ...
│   │
│   └── manage.py
│
├── facetrack-frontend/          # React SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── SessionList.jsx
│   │   │   ├── SessionDetail.jsx
│   │   │   ├── EnrollmentForm.jsx
│   │   │   └── ...
│   │   │
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Sessions.jsx
│   │   │   ├── Enroll.jsx
│   │   │   └── NotFound.jsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useSession.js
│   │   │   ├── useEnrollment.js
│   │   │   └── useFaceRecognition.js
│   │   │
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── sessionService.js
│   │   │   ├── studentService.js
│   │   │   └── frameService.js
│   │   │
│   │   ├── stores/
│   │   │   ├── sessionStore.js
│   │   │   ├── authStore.js
│   │   │   └── enrollmentStore.js
│   │   │
│   │   ├── styles/
│   │   │   └── main.css
│   │   │
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── .env.example
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── docker-compose.yml           # ← Update for both services
├── Dockerfile.backend           # ← NEW
├── Dockerfile.frontend          # ← NEW
│
└── README.md                    # ← Update instructions

```

## Network Topology

```
                           ┌─────────────┐
                           │   Browser   │
                           │  (localhost)│
                           └──────┬──────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    │ HTTP Requests            │ HTTP Requests
                    │ JSON Responses           │ JSON Responses
                    │                           │
              ┌─────▼──────┐            ┌──────▼─────┐
              │  React App │            │  Django    │
              │  :5173     │            │  API       │
              │            │            │  :8000/api │
              └────────────┘            └────────────┘
                    │                           │
                    │                           │
                    └───────────┬───────────────┘
                                │
                        ┌───────▼────────┐
                        │  PostgreSQL DB │
                        │  :5432         │
                        └────────────────┘
```

## Feature Comparison

| Feature | Django Templates | React SPA |
|---------|---|---|
| Page Reload | Full page (slow) | Partial updates (fast) |
| User Experience | Traditional | Modern, responsive |
| API Separation | No | Yes |
| Code Reusability | Limited | High (components) |
| State Management | Server-side | Client-side |
| Real-time Updates | Server push | Polling or WebSockets |
| Mobile Ready | Limited | Easy (React Native) |
| Development Speed | Moderate | Fast (HMR) |
| Learning Curve | Django-specific | React ecosystem |
| Deployment | Single server | Two separate servers |
| Scaling | Coupled | Independent |

---

This architecture provides the foundation for a modern, scalable face recognition system with proper separation of concerns!

