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

    if (loading) {
        return (
            <div className="session-detail">
                <div className="session-detail-container">
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
                        <div className="loading-spinner"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="session-detail">
                <div className="session-detail-container">
                    <div className="error-alert">Error: {error}</div>
                </div>
            </div>
        );
    }

    if (!session) {
        return (
            <div className="session-detail">
                <div className="session-detail-container">
                    <div className="error-alert">Session not found</div>
                </div>
            </div>
        );
    }

    return (
        <div className="session-detail">
            <div className="session-detail-container">
                <div className="session-detail-header">
                    <h1 className="session-detail-title">{session.subject}</h1>
                    <div className="session-detail-info">
                        <div className="detail-info-item">
                            <div className="detail-info-label">Status</div>
                            <div className="detail-info-value">
                                <span className={`status-badge ${session.status === 'ongoing' ? 'running' : 'stopped'}`}>
                                    {session.status === 'ongoing' ? '🟢 Running' : '🔴 Stopped'}
                                </span>
                            </div>
                        </div>
                        <div className="detail-info-item">
                            <div className="detail-info-label">Class Group</div>
                            <div className="detail-info-value">{session.class_group || 'N/A'}</div>
                        </div>
                        <div className="detail-info-item">
                            <div className="detail-info-label">Created At</div>
                            <div className="detail-info-value">{new Date(session.created_at).toLocaleDateString()}</div>
                        </div>
                    </div>
                </div>

                {progress && (
                    <div className="progress-section">
                        <h2><i className="bi bi-graph-up"></i> Recognition Progress</h2>
                        <div className="progress-stats">
                            <div className="stat-item">
                                <div className="stat-value">{progress.present_count}</div>
                                <div className="stat-label">Present</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-value">{progress.total_expected}</div>
                                <div className="stat-label">Expected</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-value">{progress.attendance_percentage}%</div>
                                <div className="stat-label">Attendance</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-value">{progress.unknown_count}</div>
                                <div className="stat-label">Unidentified</div>
                            </div>
                        </div>
                        <div className="progress-bar-large">
                            <div
                                className="progress-fill"
                                style={{ width: `${progress.attendance_percentage}%` }}
                            />
                        </div>
                    </div>
                )}

                <div className="students-section">
                    <div className="students-list">
                        <h3><i className="bi bi-check-circle"></i> Present Students ({presentStudents.length})</h3>
                        {presentStudents.length > 0 ? (
                            <ul>
                                {presentStudents.map(student => (
                                    <li key={student.id}>
                                        <i className="bi bi-person-check"></i> {student.name} ({student.student_id})
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: '#6b7280', textAlign: 'center', paddingTop: '1rem' }}>No present students yet</p>
                        )}
                    </div>

                    <div className="students-list">
                        <h3><i className="bi bi-x-circle"></i> Absent Students ({absentStudents.length})</h3>
                        {absentStudents.length > 0 ? (
                            <ul>
                                {absentStudents.map(student => (
                                    <li key={student.id}>
                                        <i className="bi bi-person-x"></i> {student.name} ({student.student_id})
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: '#6b7280', textAlign: 'center', paddingTop: '1rem' }}>No absent students</p>
                        )}
                    </div>
                </div>

                {events.length > 0 && (
                    <div className="events-section">
                        <h2><i className="bi bi-clock-history"></i> Recent Events ({events.length})</h2>
                        <div className="events-list">
                            {events.map(event => (
                                <div key={event.id} className={`event ${event.severity || 'info'}`}>
                                    <span className="type">[{event.type}]</span>
                                    <span className="message">{event.message}</span>
                                    <span className="time">
                                        {new Date(event.timestamp).toLocaleTimeString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="session-controls">
                    <label className="controls-checkbox">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                        />
                        <span>Auto-refresh every 5 seconds</span>
                    </label>

                    {session.status === 'ongoing' && (
                        <button 
                            className="btn-end-session"
                            onClick={() => endSession(sessionId)}
                        >
                            <i className="bi bi-stop-circle"></i> End Session
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}