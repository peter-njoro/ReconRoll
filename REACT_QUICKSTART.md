# React Migration - Quick Start Guide

## TL;DR - Get Started in 30 Minutes

### Step 1: Initialize React Project

```bash
# In your workspace root
npm create vite@latest facetrack-frontend -- --template react
cd facetrack-frontend

# Install essentials
npm install axios react-router-dom zustand
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Start dev server
npm run dev
```

Your React app will run at `http://localhost:5173`

### Step 2: Configure Django Backend for API

```bash
cd app  # Go to Django project

# Install DRF
pip install djangorestframework django-cors-headers
```

Add to `app/config/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... rest of middleware
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}
```

### Step 3: Create Basic API Structure

Create `app/recognition/serializers.py`:

```python
from rest_framework import serializers
from .models import Session, Student, AttendanceRecord, Event

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'full_name', 'student_id', 'class_group']

class SessionSerializer(serializers.ModelSerializer):
    present_count = serializers.SerializerMethodField()
    expected_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = ['id', 'subject', 'class_group', 'status', 'present_count', 'expected_count', 'started_at', 'end_time']
    
    def get_present_count(self, obj):
        return obj.attendance_records.count()
    
    def get_expected_count(self, obj):
        return obj.class_group.students.count() if obj.class_group else 0

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'event_type', 'message', 'timestamp', 'severity']
```

Create `app/recognition/api.py`:

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Session, Student
from .serializers import SessionSerializer, StudentSerializer
from .recognition_runner import active_recognition
import threading

class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from .recognition_runner import run_recognition
        from django.utils import timezone
        
        session = self.get_object()
        
        if str(pk) in active_recognition:
            return Response({'error': 'Session already running'}, status=status.HTTP_400_BAD_REQUEST)
        
        stop_flag = threading.Event()
        t = threading.Thread(
            target=run_recognition,
            args=(str(pk),),
            kwargs={'dev_mode': False, 'stop_flag': stop_flag},
            daemon=True
        )
        t.start()
        
        active_recognition[str(pk)] = {
            'thread': t,
            'stop_flag': stop_flag,
            'started_at': timezone.now(),
            'mode': 'prod'
        }
        
        session.status = 'ongoing'
        session.save()
        
        return Response({'status': 'started', 'session_id': pk})
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        session = self.get_object()
        
        if str(pk) in active_recognition:
            active_recognition[str(pk)]['stop_flag'].set()
            active_recognition.pop(str(pk), None)
        
        session.status = 'ended'
        session.save()
        
        return Response({'status': 'stopped'})
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        session = self.get_object()
        return Response({
            'id': session.id,
            'subject': session.subject,
            'status': session.status,
            'present_count': session.attendance_records.count(),
            'expected_count': session.class_group.students.count() if session.class_group else 0,
            'unknown_count': session.unidentified_faces.count(),
            'is_running': str(pk) in active_recognition and active_recognition[str(pk)].get('thread', {}).is_alive()
        })

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
```

Update `app/config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from recognition.api import SessionViewSet, StudentViewSet

router = DefaultRouter()
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'students', StudentViewSet, basename='student')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('', include('recognition.urls')),
]
```

### Step 4: Create React Components

Create `facetrack-frontend/src/services/api.js`:

```javascript
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default apiClient;
```

Create `facetrack-frontend/src/services/sessionService.js`:

```javascript
import apiClient from './api';

export const sessionService = {
  getAllSessions: () => apiClient.get('/sessions/'),
  getSession: (id) => apiClient.get(`/sessions/${id}/`),
  createSession: (data) => apiClient.post('/sessions/', data),
  updateSession: (id, data) => apiClient.patch(`/sessions/${id}/`, data),
  startSession: (id) => apiClient.post(`/sessions/${id}/start/`),
  stopSession: (id) => apiClient.post(`/sessions/${id}/stop/`),
  getStatus: (id) => apiClient.get(`/sessions/${id}/status/`),
};
```

Create `facetrack-frontend/src/hooks/useSession.js`:

```javascript
import { useState, useEffect } from 'react';
import { sessionService } from '../services/sessionService';

export const useSession = (sessionId) => {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const fetchSession = async () => {
      try {
        const { data } = await sessionService.getStatus(sessionId);
        if (isMounted) setSession(data);
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchSession();
    const interval = setInterval(fetchSession, 2000);
    
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [sessionId]);

  const startSession = async () => {
    try {
      await sessionService.startSession(sessionId);
      const { data } = await sessionService.getStatus(sessionId);
      setSession(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const stopSession = async () => {
    try {
      await sessionService.stopSession(sessionId);
      const { data } = await sessionService.getStatus(sessionId);
      setSession(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return { session, loading, error, startSession, stopSession };
};
```

Create `facetrack-frontend/src/pages/SessionDetail.jsx`:

```jsx
import React, { useParams } from 'react';
import { useSession } from '../hooks/useSession';

export default function SessionDetail() {
  const { id } = useParams();
  const { session, loading, error, startSession, stopSession } = useSession(id);

  if (loading) return <div className="p-4">Loading...</div>;
  if (error) return <div className="p-4 text-red-600">Error: {error}</div>;
  if (!session) return <div className="p-4 text-yellow-600">Session not found</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4">{session.subject}</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded shadow">
          <div className="text-2xl font-bold text-blue-600">{session.present_count}</div>
          <div className="text-gray-600">Present</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-2xl font-bold text-gray-600">{session.expected_count - session.present_count}</div>
          <div className="text-gray-600">Absent</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-2xl font-bold text-yellow-600">{session.unknown_count}</div>
          <div className="text-gray-600">Unknown</div>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <div className="text-2xl font-bold capitalize" style={{color: session.status === 'ongoing' ? '#10b981' : '#6b7280'}}>
            {session.status}
          </div>
          <div className="text-gray-600">Status</div>
        </div>
      </div>

      <div className="mb-4">
        {session.status === 'ready' ? (
          <button
            onClick={startSession}
            className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded"
          >
            Start Recognition
          </button>
        ) : session.status === 'ongoing' ? (
          <button
            onClick={stopSession}
            className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded"
          >
            Stop Recognition
          </button>
        ) : null}
      </div>
    </div>
  );
}
```

### Step 5: Run Both Servers

```bash
# Terminal 1: Django backend
cd app
python manage.py runserver

# Terminal 2: React frontend
cd facetrack-frontend
npm run dev
```

Visit `http://localhost:5173` - your React app will call the Django API at `http://localhost:8000/api`

---

## Next Steps

1. **Copy this migration guide** to your team
2. **Start with Phase 1** - Set up React project structure
3. **Complete Phase 2** - Convert Django views to REST API
4. **Build components** - Use the templates/examples provided
5. **Test thoroughly** - Ensure all features work
6. **Deploy separately** - Frontend and backend in their own containers/servers

---

## Troubleshooting

**CORS errors?**
```python
# Make sure CORS_ALLOWED_ORIGINS includes your React frontend URL
CORS_ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
```

**API not responding?**
```javascript
// Check that VITE_API_URL is correct in your .env file
VITE_API_URL=http://localhost:8000/api
```

**Port conflicts?**
```bash
# Run React on different port
npm run dev -- --port 3000

# Run Django on different port
python manage.py runserver 8001
```

---

## Support Files

- See `REACT_MIGRATION_PLAN.md` for comprehensive guide
- Check `views.py` attachment for current Django implementation reference

Good luck with your migration! 🚀

