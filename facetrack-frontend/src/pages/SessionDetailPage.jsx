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
                    <button onClick={() => endSession(sessionId)} className="btn btn-primary">
                        End Session
                    </button>
                )}
            </div>
        </div>
    );
}