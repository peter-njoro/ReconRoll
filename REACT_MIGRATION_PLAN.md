# React Frontend Migration Plan

## Overview
Migrate from Django Templates + Bootstrap to a modern React single-page application (SPA) while keeping Django as a REST API backend. This provides better separation of concerns, improved performance, and a modern development experience.

---

## Architecture

### Current State (Monolithic)
```
Django App
├── Templates (HTML + Django Template Language)
├── Static Files (CSS, JS)
└── Views (Server-side rendering)
     └── Requests routed through Django URLconf
```

### Target State (SPA + REST API)
```
Django Backend (REST API)          React Frontend (SPA)
├── /api/sessions/                 ├── Components
├── /api/students/                 │   ├── SessionList
├── /api/enrollment/               │   ├── SessionDetail
├── /api/upload_frame/             │   ├── EnrollmentForm
└── /api/attendance/               │   └── Dashboard
                                   ├── Pages
                                   │   ├── Home
                                   │   ├── Sessions
                                   │   └── Enroll
                                   └── Hooks
                                       ├── useSession
                                       └── useEnrollment
```

---

## Phase 1: Project Setup (Week 1)

### 1.1 Create React Project Structure

```bash
# Create React app using Vite (faster than CRA)
npm create vite@latest facetrack-frontend -- --template react
cd facetrack-frontend

# Install dependencies
npm install
npm install axios react-router-dom zustand

# Development setup
npm run dev
```

### 1.2 Project Structure
```
facetrack-frontend/
├── src/
│   ├── components/
│   │   ├── SessionList.jsx
│   │   ├── SessionDetail.jsx
│   │   ├── EnrollmentForm.jsx
│   │   ├── StudentList.jsx
│   │   └── Navbar.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Sessions.jsx
│   │   ├── Enroll.jsx
│   │   └── NotFound.jsx
│   ├── hooks/
│   │   ├── useSession.js
│   │   ├── useEnrollment.js
│   │   └── useFaceRecognition.js
│   ├── services/
│   │   ├── api.js
│   │   ├── sessionService.js
│   │   └── enrollmentService.js
│   ├── stores/
│   │   ├── sessionStore.js
│   │   └── authStore.js
│   ├── styles/
│   │   └── main.css
│   ├── App.jsx
│   └── main.jsx
├── public/
├── package.json
├── vite.config.js
└── .env.example
```

### 1.3 Environment Configuration
Create `.env.example`:
```
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=FaceTrack Lite
VITE_VERSION=1.0.0
```

---

## Phase 2: REST API Enhancement (Week 1-2)

### 2.1 Convert Django Views to DRF (Django Rest Framework)

Install DRF:
```bash
pip install djangorestframework django-cors-headers
```

### 2.2 Create API Serializers

```python
# app/recognition/serializers.py
from rest_framework import serializers
from .models import Session, Student, AttendanceRecord, Event

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'full_name', 'student_id', 'class_group']

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'subject', 'class_group', 'status', 'started_at', 'ended_at']

class AttendanceRecordSerializer(serializers.ModelSerializer):
    student = StudentSerializer()
    class Meta:
        model = AttendanceRecord
        fields = ['id', 'session', 'student', 'marked_at']

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'message', 'timestamp', 'severity']
```

### 2.3 Create API ViewSets

```python
# app/recognition/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Session, Student, AttendanceRecord
from .serializers import SessionSerializer, StudentSerializer

class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start recognition for session"""
        session = self.get_object()
        # Start recognition logic here
        return Response({'status': 'started'})
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop recognition for session"""
        session = self.get_object()
        # Stop recognition logic here
        return Response({'status': 'stopped'})
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get real-time session status"""
        session = self.get_object()
        return Response({
            'id': session.id,
            'status': session.status,
            'present_count': session.attendance_records.count(),
            'total_expected': session.class_group.students.count() if session.class_group else 0
        })

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
```

### 2.4 Update Django URLs for API

```python
# app/config/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from recognition.viewsets import SessionViewSet, StudentViewSet

router = DefaultRouter()
router.register(r'sessions', SessionViewSet)
router.register(r'students', StudentViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/upload_frame/', views.upload_frame, name='upload_frame'),
    # Keep legacy URLs during transition
    path('', include('recognition.urls')),
]
```

### 2.5 Enable CORS

```python
# app/config/settings.py
INSTALLED_APPS = [
    # ... existing apps
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ... other middleware
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",   # Alternative port
    "http://127.0.0.1:5173",
]

# In production, add your frontend domain
if not DEBUG:
    CORS_ALLOWED_ORIGINS.append("https://yourdomain.com")
```

---

## Phase 3: React Components (Week 2-3)

### 3.1 Core API Service Layer

```javascript
// src/services/api.js
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
```

### 3.2 Service Modules

```javascript
// src/services/sessionService.js
import apiClient from './api';

export const sessionService = {
  getAllSessions: () => apiClient.get('/sessions/'),
  getSession: (id) => apiClient.get(`/sessions/${id}/`),
  createSession: (data) => apiClient.post('/sessions/', data),
  updateSession: (id, data) => apiClient.patch(`/sessions/${id}/`, data),
  startSession: (id) => apiClient.post(`/sessions/${id}/start/`),
  stopSession: (id) => apiClient.post(`/sessions/${id}/stop/`),
  getSessionStatus: (id) => apiClient.get(`/sessions/${id}/status/`),
};

// src/services/studentService.js
export const studentService = {
  getAllStudents: () => apiClient.get('/students/'),
  getStudent: (id) => apiClient.get(`/students/${id}/`),
  enrollStudent: (data) => apiClient.post('/students/', data),
  uploadFaceImage: (studentId, file) => {
    const formData = new FormData();
    formData.append('image', file);
    return apiClient.post(`/students/${studentId}/upload-face/`, formData);
  },
};

// src/services/frameService.js
export const frameService = {
  uploadFrame: (sessionId, frameData) => {
    const formData = new FormData();
    formData.append('frame', frameData);
    return apiClient.post('/upload_frame/', formData);
  },
};
```

### 3.3 Custom Hooks

```javascript
// src/hooks/useSession.js
import { useState, useEffect } from 'react';
import { sessionService } from '../services/sessionService';

export const useSession = (sessionId) => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const { data } = await sessionService.getSession(sessionId);
        setSession(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSession();
    
    // Poll for status updates every 2 seconds
    const interval = setInterval(fetchSession, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const startSession = async () => {
    try {
      await sessionService.startSession(sessionId);
      const { data } = await sessionService.getSession(sessionId);
      setSession(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const stopSession = async () => {
    try {
      await sessionService.stopSession(sessionId);
      const { data } = await sessionService.getSession(sessionId);
      setSession(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return { session, loading, error, startSession, stopSession };
};

// src/hooks/useEnrollment.js
import { useState } from 'react';
import { studentService } from '../services/studentService';

export const useEnrollment = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  const enrollStudent = async (studentData, imageFiles) => {
    setLoading(true);
    setError(null);
    
    try {
      // Create student
      const { data: student } = await studentService.enrollStudent(studentData);
      
      // Upload face images
      const totalImages = imageFiles.length;
      for (let i = 0; i < totalImages; i++) {
        await studentService.uploadFaceImage(student.id, imageFiles[i]);
        setProgress(((i + 1) / totalImages) * 100);
      }
      
      return student;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  return { enrollStudent, loading, error, progress };
};
```

### 3.4 React Components

```jsx
// src/components/SessionList.jsx
import React, { useState, useEffect } from 'react';
import { sessionService } from '../services/sessionService';
import { Link } from 'react-router-dom';

export const SessionList = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const { data } = await sessionService.getAllSessions();
        setSessions(data);
      } catch (error) {
        console.error('Failed to fetch sessions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSessions();
  }, []);

  if (loading) return <div className="spinner-border">Loading...</div>;

  return (
    <div className="container mt-4">
      <h1>Sessions</h1>
      <Link to="/session/create" className="btn btn-primary mb-3">
        New Session
      </Link>
      
      <div className="row">
        {sessions.map((session) => (
          <div key={session.id} className="col-md-6 mb-3">
            <div className="card">
              <div className="card-body">
                <h5 className="card-title">{session.subject}</h5>
                <p className="card-text">
                  Status: <span className={`badge bg-${session.status === 'ongoing' ? 'success' : 'secondary'}`}>
                    {session.status}
                  </span>
                </p>
                <Link to={`/session/${session.id}`} className="btn btn-sm btn-primary">
                  Details
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// src/components/SessionDetail.jsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useSession } from '../hooks/useSession';

export const SessionDetail = () => {
  const { sessionId } = useParams();
  const { session, loading, error, startSession, stopSession } = useSession(sessionId);

  if (loading) return <div className="spinner-border">Loading session...</div>;
  if (error) return <div className="alert alert-danger">{error}</div>;
  if (!session) return <div className="alert alert-warning">Session not found</div>;

  return (
    <div className="container mt-4">
      <div className="row">
        <div className="col-md-8">
          <h1>{session.subject}</h1>
          <p>Status: <strong>{session.status}</strong></p>
          
          <div className="mb-3">
            {session.status === 'ready' && (
              <button onClick={startSession} className="btn btn-success">
                Start Recognition
              </button>
            )}
            {session.status === 'ongoing' && (
              <button onClick={stopSession} className="btn btn-danger">
                Stop Recognition
              </button>
            )}
          </div>

          <div className="row mt-4">
            <div className="col-md-6">
              <h3>Present Students</h3>
              <div id="present-students" className="list-group">
                {/* Loaded dynamically */}
              </div>
            </div>
            <div className="col-md-6">
              <h3>Absent Students</h3>
              <div id="absent-students" className="list-group">
                {/* Loaded dynamically */}
              </div>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card">
            <div className="card-header">
              <h5>Statistics</h5>
            </div>
            <div className="card-body">
              <p>Present: <strong>{session.present_count || 0}</strong></p>
              <p>Expected: <strong>{session.total_expected || 0}</strong></p>
              <p>Unknown: <strong>{session.unknown_count || 0}</strong></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// src/components/EnrollmentForm.jsx
import React, { useState } from 'react';
import { useEnrollment } from '../hooks/useEnrollment';

export const EnrollmentForm = () => {
  const [formData, setFormData] = useState({
    full_name: '',
    student_id: '',
    class_group: '',
  });
  const [images, setImages] = useState([]);
  const { enrollStudent, loading, error, progress } = useEnrollment();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await enrollStudent(formData, images);
      alert('Student enrolled successfully!');
      setFormData({ full_name: '', student_id: '', class_group: '' });
      setImages([]);
    } catch (err) {
      console.error('Enrollment failed:', err);
    }
  };

  return (
    <div className="container mt-4">
      <h1>Enroll Student</h1>
      
      {error && <div className="alert alert-danger">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label className="form-label">Full Name</label>
          <input
            type="text"
            className="form-control"
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
            required
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Student ID</label>
          <input
            type="text"
            className="form-control"
            value={formData.student_id}
            onChange={(e) => setFormData({ ...formData, student_id: e.target.value })}
            required
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Face Images</label>
          <input
            type="file"
            className="form-control"
            multiple
            accept="image/*"
            onChange={(e) => setImages(Array.from(e.target.files))}
            required
          />
        </div>

        {progress > 0 && (
          <div className="progress mb-3">
            <div
              className="progress-bar"
              role="progressbar"
              style={{ width: `${progress}%` }}
            >
              {Math.round(progress)}%
            </div>
          </div>
        )}

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Enrolling...' : 'Enroll'}
        </button>
      </form>
    </div>
  );
};
```

### 3.5 App Router

```jsx
// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Home } from './pages/Home';
import { SessionList } from './pages/Sessions';
import { SessionDetail } from './components/SessionDetail';
import { EnrollmentForm } from './components/EnrollmentForm';
import { NotFound } from './pages/NotFound';

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sessions" element={<SessionList />} />
        <Route path="/session/:sessionId" element={<SessionDetail />} />
        <Route path="/enroll" element={<EnrollmentForm />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

export default App;
```

---

## Phase 4: State Management (Week 3)

### 4.1 Zustand Store Setup

```javascript
// src/stores/sessionStore.js
import { create } from 'zustand';
import { sessionService } from '../services/sessionService';

export const useSessionStore = create((set, get) => ({
  sessions: [],
  currentSession: null,
  loading: false,
  error: null,

  fetchSessions: async () => {
    set({ loading: true });
    try {
      const { data } = await sessionService.getAllSessions();
      set({ sessions: data, error: null });
    } catch (error) {
      set({ error: error.message });
    } finally {
      set({ loading: false });
    }
  },

  startSession: async (sessionId) => {
    try {
      await sessionService.startSession(sessionId);
      const { data } = await sessionService.getSession(sessionId);
      set({ currentSession: data });
    } catch (error) {
      set({ error: error.message });
    }
  },

  stopSession: async (sessionId) => {
    try {
      await sessionService.stopSession(sessionId);
      const { data } = await sessionService.getSession(sessionId);
      set({ currentSession: data });
    } catch (error) {
      set({ error: error.message });
    }
  },
}));

// src/stores/authStore.js
export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('auth_token'),
  isAuthenticated: !!localStorage.getItem('auth_token'),

  login: async (username, password) => {
    try {
      const { data } = await apiClient.post('/auth/login/', { username, password });
      localStorage.setItem('auth_token', data.token);
      set({ token: data.token, user: data.user, isAuthenticated: true });
    } catch (error) {
      set({ error: error.message });
    }
  },

  logout: () => {
    localStorage.removeItem('auth_token');
    set({ token: null, user: null, isAuthenticated: false });
  },
}));
```

---

## Phase 5: Styling & UI (Week 3-4)

### 5.1 Tailwind CSS Setup (recommended) or Bootstrap

```bash
# Option 1: Tailwind CSS (recommended for modern React)
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Option 2: Bootstrap React
npm install react-bootstrap bootstrap
```

### 5.2 Global Styles

```css
/* src/styles/main.css */
:root {
  --primary: #007bff;
  --success: #28a745;
  --danger: #dc3545;
  --warning: #ffc107;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
}

.navbar {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card {
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}
```

---

## Phase 6: Testing & Deployment (Week 4)

### 6.1 Unit Tests

```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom
```

```javascript
// src/__tests__/sessionService.test.js
import { describe, it, expect, vi } from 'vitest';
import { sessionService } from '../services/sessionService';

describe('sessionService', () => {
  it('should fetch all sessions', async () => {
    const mockData = [{ id: 1, subject: 'Math' }];
    vi.mock('../services/api', () => ({
      default: { get: vi.fn(() => Promise.resolve({ data: mockData })) }
    }));

    const result = await sessionService.getAllSessions();
    expect(result.data).toEqual(mockData);
  });
});
```

### 6.2 Build & Deploy

```bash
# Build for production
npm run build

# Output in dist/ directory ready for deployment
```

---

## Migration Strategy

### Step-by-Step Transition (No Downtime)

**Week 1-2: Backend API Preparation**
- [ ] Add DRF serializers and viewsets
- [ ] Enable CORS
- [ ] Test all API endpoints

**Week 2-3: Frontend Development (Parallel)**
- [ ] Set up React project
- [ ] Build components
- [ ] Connect to API
- [ ] Test functionality

**Week 3-4: Gradual Rollout**
- [ ] Deploy React app to separate domain (subdomain.yourdomain.com)
- [ ] Dual-run: Django templates + React
- [ ] Migrate users gradually
- [ ] Monitor for issues

**Week 4: Full Migration**
- [ ] Retire Django templates
- [ ] Keep API running indefinitely
- [ ] Update documentation

---

## File Mapping: Django → React

| Django Template | React Component | Route |
|---|---|---|
| index.html | Home.jsx | / |
| enroll.html | EnrollmentForm.jsx | /enroll |
| session_list.html | SessionList.jsx | /sessions |
| session_detail.html | SessionDetail.jsx | /session/:id |
| start_session.html | SessionDetail.jsx | /session/:id |
| base.html | Navbar.jsx | (layout) |

---

## API Endpoint Reference

```
GET    /api/sessions/                    # List all sessions
POST   /api/sessions/                    # Create session
GET    /api/sessions/{id}/               # Get session detail
PATCH  /api/sessions/{id}/               # Update session
POST   /api/sessions/{id}/start/         # Start recognition
POST   /api/sessions/{id}/stop/          # Stop recognition
GET    /api/sessions/{id}/status/        # Get status

GET    /api/students/                    # List students
POST   /api/students/                    # Create student
GET    /api/students/{id}/               # Get student detail
POST   /api/students/{id}/upload-face/   # Upload face image

POST   /api/upload_frame/                # Upload video frame
GET    /api/attendance/{session_id}/     # Get attendance records
```

---

## Key Benefits

✅ **Separation of Concerns** - Frontend and backend are independent  
✅ **Modern Development** - React ecosystem, fast tooling (Vite)  
✅ **Better Performance** - SPA loads faster, less server roundtrips  
✅ **Scalability** - Can scale frontend and backend independently  
✅ **Mobile-Ready** - React app can be wrapped in React Native  
✅ **Offline Support** - Can add service workers for offline capability  
✅ **Developer Experience** - HMR, dev tools, larger community  

---

## Potential Challenges & Solutions

| Challenge | Solution |
|---|---|
| Authentication tokens across domains | Use httpOnly cookies or localStorage with CORS |
| Image uploads for enrollment | Use multipart FormData, handle on API |
| Real-time updates (session status) | WebSocket or polling every 2-5 seconds |
| SEO concerns | Use Next.js instead of CRA/Vite for SSR |
| Deployment complexity | Docker: separate frontend/backend containers |

---

## Deployment Options

### Option 1: Separate Containers (Recommended)
```dockerfile
# Docker Compose
services:
  backend:
    build: ./django-app
    ports: ["8000:8000"]
  
  frontend:
    build: ./react-app
    ports: ["3000:3000"]
```

### Option 2: Single Container with Nginx
```nginx
server {
  location /api/ {
    proxy_pass http://django:8000;
  }
  
  location / {
    proxy_pass http://react:3000;
  }
}
```

### Option 3: Cloudflare / Netlify + Cloud Run
- Deploy React to Netlify
- Deploy Django to Cloud Run
- Connect via API

---

## Questions Before Starting

1. **Authentication**: Do you want JWT tokens, sessions, or OAuth?
2. **Real-time Updates**: Do you need WebSockets for live updates?
3. **Styling**: Tailwind CSS or Bootstrap?
4. **State Management**: Zustand, Redux, or Context API?
5. **Testing**: Unit, integration, or E2E tests?

