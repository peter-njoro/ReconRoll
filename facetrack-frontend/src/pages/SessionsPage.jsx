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

    if (loading) return <div>Loading sessions...</div>;
    if (error) return <div>Error: {error}</div>;

    return (
        <div className="sessions-page">
            <h1>Recognition Sessions</h1>
            <Link to="/session/create" className="btn btn-primary">Create New Session</Link>

            <table className="table">
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
                    {Array.isArray(sessions) && sessions.map(session => (
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
                                <Link to={`/session/${session.id}`} className="btn btn-info btn-sm">View</Link>
                                {session.recognition.is_running && (
                                    <button onClick={() => endSession(session.id)} className="btn btn-warning btn-sm">
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