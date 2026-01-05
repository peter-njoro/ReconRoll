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
                const data = response.data;

                setSessions(
                    Array.isArray(data)
                        ? data
                        : data.results || []
                );
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchSessions();
    }, []);

    if (loading) {
        return (
            <div className="sessions-page">
                <div className="container-lg">
                    <div className="loading-state">
                        <span className="spinner"></span>
                        <p>Loading sessions...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="sessions-page">
                <div className="container-lg">
                    <div className="error-state">
                        <i className="bi bi-exclamation-triangle"></i>
                        <p>Error: {error}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="sessions-page">
            <div className="container-lg">
                <div className="page-header">
                    <div>
                        <h1>Recognition Sessions</h1>
                        <p className="page-subtitle">Manage and monitor your recognition sessions</p>
                    </div>
                    <Link to="/session/create" className="btn-primary-gradient">
                        <i className="bi bi-plus-circle"></i>
                        Create New Session
                    </Link>
                </div>

                {sessions.length === 0 ? (
                    <div className="empty-state">
                        <i className="bi bi-inbox"></i>
                        <h3>No sessions yet</h3>
                        <p>Create your first recognition session to get started</p>
                        <Link to="/session/create" className="btn-primary-gradient">
                            Create Session
                        </Link>
                    </div>
                ) : (
                    <div className="sessions-grid">
                        {Array.isArray(sessions) && sessions.map(session => (
                            <div key={session.id} className="session-card">
                                <div className="session-card-header">
                                    <h3 className="session-title">{session.subject}</h3>
                                    <span className={`status-badge ${session.status.toLowerCase()}`}>
                                        {session.status}
                                    </span>
                                </div>

                                <div className="session-info">
                                    <div className="info-row">
                                        <span className="info-label">
                                            <i className="bi bi-folder"></i>
                                            Class Group
                                        </span>
                                        <span className="info-value">{session.class_group || 'N/A'}</span>
                                    </div>

                                    <div className="info-row">
                                        <span className="info-label">
                                            <i className="bi bi-people"></i>
                                            Attendance
                                        </span>
                                        <span className="info-value">
                                            {session.recognition.present_count}/{session.recognition.expected_count}
                                        </span>
                                    </div>

                                    <div className="info-row">
                                        <span className="info-label">
                                            <i className="bi bi-percent"></i>
                                            Percentage
                                        </span>
                                        <span className="info-value">
                                            {session.recognition.attendance_percentage}%
                                        </span>
                                    </div>

                                    <div className="progress-bar-container">
                                        <div className="progress-bar">
                                            <div
                                                className="progress-fill"
                                                style={{ width: `${session.recognition.attendance_percentage}%` }}
                                            ></div>
                                        </div>
                                    </div>

                                    <div className="info-row">
                                        <span className="info-label">
                                            <i className="bi bi-camera-video"></i>
                                            Recognition
                                        </span>
                                        <span className={`status-indicator ${session.recognition.is_running ? 'running' : 'stopped'}`}>
                                            <span className="dot"></span>
                                            {session.recognition.is_running
                                                ? `Running (${session.recognition.mode})`
                                                : 'Stopped'}
                                        </span>
                                    </div>
                                </div>

                                <div className="session-actions">
                                    <Link to={`/session/${session.id}`} className="action-link primary">
                                        <i className="bi bi-eye"></i>
                                        View Details
                                    </Link>
                                    {session.recognition.is_running && (
                                        <button
                                            onClick={() => endSession(session.id)}
                                            className="action-link danger"
                                        >
                                            <i className="bi bi-stop-circle"></i>
                                            End Session
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
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