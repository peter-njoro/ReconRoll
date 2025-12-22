# Quick Start: React Frontend with JSON API

## 🚀 5-Minute Setup

### Step 1: Verify API is Running

```bash
# Test the API is working
curl http://localhost:8000/recognition/

# Expected response:
# {
#     "title": "FaceTrack Lite API",
#     "message": "Welcome to FaceTrack Lite...",
#     "version": "2.0",
#     "endpoints": {...}
# }
```

### Step 2: Create React App

```bash
npm create-react-app facetrack-frontend
cd facetrack-frontend
```

### Step 3: Install Dependencies

```bash
npm install axios react-router-dom
```

### Step 4: Create API Service

**`src/api/client.js`**:
```javascript
import axios from 'axios';

const apiClient = axios.create({
    baseURL: 'http://localhost:8000',
    headers: { 'Content-Type': 'application/json' },
});

// Handle CSRF token
apiClient.interceptors.request.use((config) => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
});

export default apiClient;
```

**`src/api/recognitionService.js`**:
```javascript
import apiClient from './client';

export const recognitionService = {
    getInfo: () => apiClient.get('/recognition/'),
    listSessions: () => apiClient.get('/recognition/sessions/'),
    getSession: (id) => apiClient.get(`/recognition/session/${id}/`),
    createSession: (data) => apiClient.post('/recognition/session/create/', data),
    endSession: (id) => apiClient.post(`/recognition/session/${id}/end/`),
    enrollStudent: (formData) => apiClient.post('/recognition/enroll/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    getProgress: (id) => apiClient.get(`/recognition/session/${id}/progress/`),
};
```

### Step 5: Create a Simple Component

**`src/SessionsList.js`**:
```javascript
import { useEffect, useState } from 'react';
import { recognitionService } from './api/recognitionService';

export function SessionsList() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        recognitionService.listSessions()
            .then(res => setSessions(res.data.sessions))
            .catch(err => console.error(err))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div>Loading...</div>;

    return (
        <div>
            <h1>Sessions ({sessions.length})</h1>
            <ul>
                {sessions.map(session => (
                    <li key={session.id}>
                        <strong>{session.subject}</strong>
                        <p>Status: {session.status}</p>
                        <p>Attendance: {session.recognition.attendance_percentage}%</p>
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

### Step 6: Use in App

**`src/App.js`**:
```javascript
import './App.css';
import { SessionsList } from './SessionsList';

function App() {
    return (
        <div className="App">
            <h1>FaceTrack Lite</h1>
            <SessionsList />
        </div>
    );
}

export default App;
```

### Step 7: Run

```bash
npm start
# Opens http://localhost:3000
```

---

## 🎯 Common API Calls

### Get All Sessions
```javascript
const response = await recognitionService.listSessions();
const sessions = response.data.sessions;

// Each session has:
// - id, subject, class_group, status
// - created_at, started_at, ended_at
// - created_by
// - recognition: { is_running, mode, present_count, expected_count, attendance_percentage }
```

### Create Session
```javascript
const response = await recognitionService.createSession({
    subject: 'CS101 - Lecture 5',
    class_group: 1  // optional
});

const newSession = response.data.session;
// { id, subject, class_group, status, created_at }
```

### Get Session Details
```javascript
const response = await recognitionService.getSession(sessionId);
const session = response.data;

// Returns:
// - session: { id, subject, status, ... }
// - present_students: [ { id, name, student_id }, ... ]
// - absent_students: [ { id, name, student_id }, ... ]
// - summary: { expected_count, present_count, absent_count, attendance_percentage }
// - events: [ { id, type, severity, message, timestamp }, ... ]
```

### Get Real-time Progress
```javascript
const response = await recognitionService.getProgress(sessionId);
const progress = response.data.progress;

// Returns:
// - present_count, total_expected
// - attendance_percentage
// - unknown_count
// - is_running, mode
```

### End Session
```javascript
const response = await recognitionService.endSession(sessionId);
// Returns: { status, message, session }
```

### Enroll Student
```javascript
const formData = new FormData();
formData.append('name', 'John Doe');
formData.append('student_id', 'STU001');
formData.append('class_group', 1);
formData.append('face_images', file1);
formData.append('face_images', file2);

const response = await recognitionService.enrollStudent(formData);
// Returns: { status, message, student }
```

---

## 📱 Common Patterns

### Auto-Refresh Session Status

```javascript
useEffect(() => {
    let interval;
    
    const fetchProgress = async () => {
        const res = await recognitionService.getProgress(sessionId);
        setProgress(res.data.progress);
    };
    
    // Initial fetch
    fetchProgress();
    
    // Refresh every 2 seconds if running
    if (isRunning) {
        interval = setInterval(fetchProgress, 2000);
    }
    
    return () => clearInterval(interval);
}, [sessionId, isRunning]);
```

### Error Handling

```javascript
try {
    const response = await recognitionService.createSession(data);
    // Success
    setMessage({ type: 'success', text: response.data.message });
} catch (error) {
    if (error.response?.status === 400) {
        // Validation error
        const errors = error.response.data.errors;
        setMessage({ type: 'error', text: errors.join(', ') });
    } else {
        // Network or server error
        setMessage({ type: 'error', text: error.message });
    }
}
```

### Loading States

```javascript
const [loading, setLoading] = useState(false);

const handleSubmit = async (data) => {
    setLoading(true);
    try {
        await recognitionService.createSession(data);
        setMessage('Session created!');
    } finally {
        setLoading(false);
    }
};

<button disabled={loading}>
    {loading ? 'Creating...' : 'Create Session'}
</button>
```

### Pagination

```javascript
const [currentPage, setCurrentPage] = useState(1);
const [pageSize, setPageSize] = useState(10);

const response = await fetch(
    `/recognition/sessions/?page=${currentPage}&page_size=${pageSize}`
);
```

---

## 🔍 API Response Examples

### List Sessions Response
```json
{
    "status": "ok",
    "count": 2,
    "sessions": [
        {
            "id": 1,
            "subject": "CS101 - Lecture 5",
            "class_group": "Computer Science",
            "status": "ended",
            "created_at": "2025-12-22T10:00:00Z",
            "started_at": "2025-12-22T10:15:00Z",
            "ended_at": "2025-12-22T10:45:00Z",
            "created_by": "prof_smith",
            "recognition": {
                "is_running": false,
                "mode": "none",
                "present_count": 28,
                "expected_count": 30,
                "attendance_percentage": 93.33
            }
        }
    ]
}
```

### Session Detail Response
```json
{
    "status": "ok",
    "session": {
        "id": 1,
        "subject": "CS101 - Lecture 5",
        "class_group": 1,
        "status": "ongoing",
        "created_at": "2025-12-22T10:00:00Z",
        "started_at": "2025-12-22T10:15:00Z",
        "ended_at": null,
        "created_by": "prof_smith"
    },
    "present_students": [
        {"id": 1, "name": "Alice", "student_id": "STU001"},
        {"id": 2, "name": "Bob", "student_id": "STU002"}
    ],
    "absent_students": [
        {"id": 3, "name": "Charlie", "student_id": "STU003"}
    ],
    "summary": {
        "expected_count": 30,
        "present_count": 25,
        "absent_count": 5,
        "attendance_percentage": 83.33
    },
    "events": [
        {
            "id": 1,
            "type": "session_started",
            "severity": "info",
            "message": "Session started in PRODUCTION mode",
            "timestamp": "2025-12-22T10:15:00Z"
        }
    ]
}
```

### Error Response
```json
{
    "status": "error",
    "message": "Enrollment failed",
    "errors": [
        "No face detected in image: photo1.jpg",
        "Multiple faces detected in image: photo2.jpg"
    ]
}
```

---

## 🚨 Error Handling by Status Code

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Success, use response data |
| 201 | Created | Resource created, use response data |
| 400 | Bad Request | Invalid input, show error.data.errors |
| 404 | Not Found | Resource doesn't exist |
| 410 | Gone | Endpoint deprecated |
| 500 | Server Error | Try again later |

---

## 🔒 Authentication (if needed)

Add token to requests:

```javascript
// Store token after login
localStorage.setItem('authToken', response.data.token);

// Add to all requests
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
});
```

---

## 📚 Full Documentation

For complete details, see:
- **VIEWS_JSON_REFACTORING.md** - All endpoint documentation
- **REACT_INTEGRATION.md** - Complete React integration guide
- **VIEWS_REFACTORING_SUMMARY.md** - Summary of all changes

---

## ✅ Next Steps

1. ✅ Test API with curl
2. ✅ Create React app
3. ✅ Set up API client
4. ✅ Create first component
5. ✅ Build your dashboard
6. ✅ Deploy to production

---

## 💡 Tips

- **Start Small**: Build one component at a time
- **Use React DevTools**: Debug component state
- **Test API First**: Use curl/Postman before React
- **Handle Errors**: Always catch and display errors
- **Auto-refresh**: Use setInterval for real-time updates
- **Cache Data**: Use React Context or libraries like React Query

---

## 🎉 You're Ready!

The backend is ready for your React frontend. Happy coding! 🚀

For questions, refer to the documentation files or the endpoint examples above.
