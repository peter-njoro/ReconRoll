# React Integration Guide

## Overview

The backend now returns pure JSON responses, making it perfect for React frontend development. This guide shows how to integrate the API endpoints into a React application.

## Setup

### 1. Install Dependencies

```bash
npm install axios react-router-dom
# or
yarn add axios react-router-dom
```

### 2. Create API Client

**`src/api/client.js`**:
```javascript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add CSRF token for POST requests (Django requirement)
apiClient.interceptors.request.use((config) => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
    }
    return config;
});

export default apiClient;
```

### 3. Create API Service

**`src/api/recognitionService.js`**:
```javascript
import apiClient from './client';

export const recognitionService = {
    // Home/Info
    getInfo: () => apiClient.get('/recognition/'),

    // Student Enrollment
    enrollStudent: (formData) => apiClient.post('/recognition/enroll/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    getEnrollSchema: () => apiClient.get('/recognition/enroll/'),
    getEnrollProgress: () => apiClient.get('/recognition/enroll-progress/'),

    // Session Management
    createSession: (data) => apiClient.post('/recognition/session/create/', data),
    getCreateSessionSchema: () => apiClient.get('/recognition/session/create/'),
    getSession: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/`),
    endSession: (sessionId) => apiClient.post(`/recognition/session/${sessionId}/end/`),
    listSessions: () => apiClient.get('/recognition/sessions/'),

    // Session Details (Partials)
    getSessionEvents: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/events/`),
    getPresentStudents: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/present/`),
    getAbsentStudents: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/absent/`),
    getUnidentifiedFaces: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/unidentified/`),
    getProgress: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/progress/`),
};
```

---

## React Components

### 1. Home Page

**`src/pages/HomePage.js`**:
```javascript
import { useEffect, useState } from 'react';
import { recognitionService } from '../api/recognitionService';

export function HomePage() {
    const [info, setInfo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchInfo = async () => {
            try {
                const response = await recognitionService.getInfo();
                setInfo(response.data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchInfo();
    }, []);

    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div>
            <h1>{info.title}</h1>
            <p>{info.message}</p>
            <h2>API Version: {info.version}</h2>
            <h3>Available Endpoints:</h3>
            <ul>
                {Object.entries(info.endpoints).map(([key, url]) => (
                    <li key={key}>{key}: {url}</li>
                ))}
            </ul>
        </div>
    );
}
```

### 2. Enrollment Component

**`src/components/EnrollmentForm.js`**:
```javascript
import { useState } from 'react';
import { recognitionService } from '../api/recognitionService';

export function EnrollmentForm() {
    const [formData, setFormData] = useState({
        name: '',
        student_id: '',
        class_group: '',
    });
    const [images, setImages] = useState([]);
    const [progress, setProgress] = useState(0);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [student, setStudent] = useState(null);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleImageChange = (e) => {
        setImages(Array.from(e.target.files));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        
        const data = new FormData();
        data.append('name', formData.name);
        data.append('student_id', formData.student_id);
        if (formData.class_group) {
            data.append('class_group', formData.class_group);
        }
        images.forEach(image => {
            data.append('face_images', image);
        });

        try {
            const response = await recognitionService.enrollStudent(data);
            setMessage({
                type: 'success',
                text: response.data.message
            });
            setStudent(response.data.student);
            setFormData({ name: '', student_id: '', class_group: '' });
            setImages([]);
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.response?.data?.message || error.message
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="enrollment-form">
            <h2>Enroll Student</h2>
            
            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}

            {student && (
                <div className="success-info">
                    <p>Student enrolled: {student.name}</p>
                    <p>Encodings: {student.encodings_count}</p>
                </div>
            )}

            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    name="name"
                    placeholder="Student Name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                />

                <input
                    type="text"
                    name="student_id"
                    placeholder="Student ID"
                    value={formData.student_id}
                    onChange={handleInputChange}
                    required
                />

                <input
                    type="number"
                    name="class_group"
                    placeholder="Class Group (optional)"
                    value={formData.class_group}
                    onChange={handleInputChange}
                />

                <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageChange}
                    required
                />
                <p>Selected: {images.length} images</p>

                <button type="submit" disabled={loading}>
                    {loading ? 'Enrolling...' : 'Enroll Student'}
                </button>
            </form>

            {progress > 0 && progress < 100 && (
                <div className="progress">
                    <div className="progress-bar" style={{ width: `${progress}%` }}>
                        {progress}%
                    </div>
                </div>
            )}
        </div>
    );
}
```

### 3. Sessions List Component

**`src/pages/SessionsPage.js`**:
```javascript
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function SessionsPage() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const response = await recognitionService.listSessions();
                setSessions(response.data.sessions);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchSessions();
    }, []);

    if (loading) return <div>Loading sessions...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div className="sessions-page">
            <h1>Recognition Sessions</h1>
            <Link to="/session/create">Create New Session</Link>

            <table>
                <thead>
                    <tr>
                        <th>Subject</th>
                        <th>Class Group</th>
                        <th>Status</th>
                        <th>Attendance</th>
                        <th>Recognition</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {sessions.map(session => (
                        <tr key={session.id}>
                            <td>{session.subject}</td>
                            <td>{session.class_group}</td>
                            <td>{session.status}</td>
                            <td>
                                {session.recognition.present_count}/
                                {session.recognition.expected_count}
                                ({session.recognition.attendance_percentage}%)
                            </td>
                            <td>
                                {session.recognition.is_running ? (
                                    <span className="running">
                                        Running ({session.recognition.mode})
                                    </span>
                                ) : (
                                    <span className="stopped">Stopped</span>
                                )}
                            </td>
                            <td>
                                <Link to={`/session/${session.id}`}>View</Link>
                                {session.recognition.is_running && (
                                    <button onClick={() => endSession(session.id)}>
                                        End
                                    </button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

async function endSession(sessionId) {
    try {
        await recognitionService.endSession(sessionId);
        window.location.reload();
    } catch (error) {
        alert(`Error ending session: ${error.message}`);
    }
}
```

### 4. Session Detail Component

**`src/pages/SessionDetailPage.js`**:
```javascript
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function SessionDetailPage() {
    const { sessionId } = useParams();
    const [session, setSession] = useState(null);
    const [presentStudents, setPresentStudents] = useState([]);
    const [absentStudents, setAbsentStudents] = useState([]);
    const [events, setEvents] = useState([]);
    const [progress, setProgress] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [sessionRes, presentRes, absentRes, eventsRes, progressRes] = await Promise.all([
                    recognitionService.getSession(sessionId),
                    recognitionService.getPresentStudents(sessionId),
                    recognitionService.getAbsentStudents(sessionId),
                    recognitionService.getSessionEvents(sessionId),
                    recognitionService.getProgress(sessionId),
                ]);

                setSession(sessionRes.data.session);
                setPresentStudents(presentRes.data.present_students);
                setAbsentStudents(absentRes.data.absent_students);
                setEvents(eventsRes.data.events);
                setProgress(progressRes.data.progress);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();

        // Auto-refresh every 5 seconds if session is running
        let interval;
        if (autoRefresh) {
            interval = setInterval(fetchData, 5000);
        }

        return () => clearInterval(interval);
    }, [sessionId, autoRefresh]);

    if (loading) return <div>Loading session details...</div>;
    if (error) return <div>Error: {error}</div>;
    if (!session) return <div>Session not found</div>;

    return (
        <div className="session-detail">
            <h1>{session.subject}</h1>

            <div className="session-info">
                <p>Status: <strong>{session.status}</strong></p>
                <p>Class Group: <strong>{session.class_group}</strong></p>
                <p>Created: <strong>{new Date(session.created_at).toLocaleString()}</strong></p>
            </div>

            {progress && (
                <div className="progress-section">
                    <h2>Recognition Progress</h2>
                    <p>Present: {progress.present_count}/{progress.total_expected}</p>
                    <p>Attendance: {progress.attendance_percentage}%</p>
                    <p>Unidentified: {progress.unknown_count}</p>
                    <p>Status: {progress.is_running ? '🟢 Running' : '🔴 Stopped'}</p>

                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{ width: `${progress.attendance_percentage}%` }}
                        />
                    </div>
                </div>
            )}

            <div className="students-section">
                <div className="present-students">
                    <h2>Present Students ({presentStudents.length})</h2>
                    <ul>
                        {presentStudents.map(student => (
                            <li key={student.id}>
                                {student.name} ({student.student_id})
                            </li>
                        ))}
                    </ul>
                </div>

                <div className="absent-students">
                    <h2>Absent Students ({absentStudents.length})</h2>
                    <ul>
                        {absentStudents.map(student => (
                            <li key={student.id}>
                                {student.name} ({student.student_id})
                            </li>
                        ))}
                    </ul>
                </div>
            </div>

            <div className="events-section">
                <h2>Recent Events ({events.length})</h2>
                <div className="events-list">
                    {events.map(event => (
                        <div key={event.id} className={`event ${event.severity}`}>
                            <span className="type">[{event.type}]</span>
                            <span className="message">{event.message}</span>
                            <span className="time">
                                {new Date(event.timestamp).toLocaleTimeString()}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="controls">
                <label>
                    <input
                        type="checkbox"
                        checked={autoRefresh}
                        onChange={(e) => setAutoRefresh(e.target.checked)}
                    />
                    Auto-refresh every 5 seconds
                </label>

                {session.status === 'ongoing' && (
                    <button onClick={() => endSession(sessionId)}>
                        End Session
                    </button>
                )}
            </div>
        </div>
    );
}

async function endSession(sessionId) {
    try {
        const response = await recognitionService.endSession(sessionId);
        alert(response.data.message);
        window.location.reload();
    } catch (error) {
        alert(`Error: ${error.response?.data?.message || error.message}`);
    }
}
```

### 5. Create Session Component

**`src/pages/CreateSessionPage.js`**:
```javascript
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function CreateSessionPage() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        subject: '',
        class_group: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const response = await recognitionService.createSession({
                subject: formData.subject,
                class_group: formData.class_group || null,
            });

            alert(response.data.message);
            navigate(`/session/${response.data.session.id}`);
        } catch (err) {
            setError(
                err.response?.data?.message || 
                err.response?.data?.errors?.join(', ') ||
                err.message
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="create-session">
            <h1>Create New Session</h1>

            {error && <div className="error">{error}</div>}

            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    name="subject"
                    placeholder="Session Subject (e.g., CS101 - Lecture 5)"
                    value={formData.subject}
                    onChange={handleChange}
                    required
                />

                <input
                    type="number"
                    name="class_group"
                    placeholder="Class Group ID (optional)"
                    value={formData.class_group}
                    onChange={handleChange}
                />

                <button type="submit" disabled={loading}>
                    {loading ? 'Creating...' : 'Create Session'}
                </button>
            </form>
        </div>
    );
}
```

---

## Routing Setup

**`src/App.js`**:
```javascript
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { SessionsPage } from './pages/SessionsPage';
import { SessionDetailPage } from './pages/SessionDetailPage';
import { CreateSessionPage } from './pages/CreateSessionPage';
import { EnrollmentForm } from './components/EnrollmentForm';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/enroll" element={<EnrollmentForm />} />
                <Route path="/sessions" element={<SessionsPage />} />
                <Route path="/session/create" element={<CreateSessionPage />} />
                <Route path="/session/:sessionId" element={<SessionDetailPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
```

---

## Error Handling

### Consistent Error Handling

```javascript
const handleError = (error) => {
    if (error.response) {
        // Server responded with error
        console.error('Status:', error.response.status);
        console.error('Message:', error.response.data.message);
        console.error('Errors:', error.response.data.errors);
        
        return error.response.data.message;
    } else if (error.request) {
        // Request made but no response
        return 'No response from server';
    } else {
        // Error in request setup
        return error.message;
    }
};
```

---

## Authentication

For protected endpoints, add token header:

```javascript
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
});
```

---

## Environment Variables

**`.env`**:
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_TIMEOUT=30000
```

---

## Testing

### Testing API Service

```javascript
import { recognitionService } from '../api/recognitionService';

describe('recognitionService', () => {
    test('getInfo returns app info', async () => {
        const response = await recognitionService.getInfo();
        expect(response.data.title).toBeDefined();
        expect(response.data.version).toBeDefined();
    });

    test('listSessions returns array', async () => {
        const response = await recognitionService.listSessions();
        expect(Array.isArray(response.data.sessions)).toBe(true);
    });
});
```

---

## Performance Tips

1. **Use Pagination**: For large data sets, add pagination
2. **Cache Data**: Use React Query or SWR for caching
3. **Debounce**: Debounce auto-refresh for large lists
4. **Lazy Load**: Load images only when needed

---

## Summary

The refactored backend provides a clean JSON API perfect for React development. All endpoints are documented with request/response formats, making integration straightforward.

Key points:
- ✅ Pure JSON responses
- ✅ Consistent error handling
- ✅ HTTP status codes
- ✅ Easy to test
- ✅ Works with any frontend framework

Ready to build your React frontend! 🚀
