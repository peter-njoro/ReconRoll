import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function CreateSessionPage() {
    const navigate = useNavigate();
    const [rosters, setRosters] = useState([]);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        roster: '',
        session_type: '',
    });
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    // Load rosters on mount
    useEffect(() => {
        const fetchRosters = async () => {
            try {
                const response = await recognitionService.listRosters();
                setRosters(response.data.rosters || []);
            } catch (err) {
                console.error('Error fetching rosters:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchRosters();
    }, []);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);

        try {
            // Backend expects start_time (datetime) and status
            // Default to current time and 'scheduled' status
            const now = new Date().toISOString();
            
            const sessionPayload = {
                name: formData.name,
                description: formData.description || '',
                start_time: now,  // Required by backend
                status: 'scheduled',  // Default status
            };

            // Add roster if selected
            if (formData.roster) {
                sessionPayload.roster = formData.roster;
            }

            // Add session_type if provided
            if (formData.session_type) {
                sessionPayload.session_type = formData.session_type;
            }

            const response = await recognitionService.createSession(sessionPayload);

            console.log('[CreateSessionPage] API Response:', response);
            const sessionId = response.data.session?.id || response.data.id;
            console.log('[CreateSessionPage] Extracted sessionId:', sessionId);
            
            if (!sessionId) {
                setError('Failed to extract session ID from response');
                return;
            }
            
            // If no roster was selected, redirect to roster selection to add expected people
            // Otherwise, go directly to session detail
            if (formData.roster) {
                navigate(`/session/${sessionId}`);
            } else {
                navigate(`/session/${sessionId}/roster`);
            }
        } catch (err) {
            console.error('[CreateSessionPage] Error:', err);
            const errorMessage = 
                err.response?.data?.message ||
                err.response?.data?.errors?.join(', ') ||
                err.message ||
                'Failed to create session';
            setError(errorMessage);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="create-session-page">
            <div className="container-lg">
                <div className="form-container">
                    <div className="form-card">
                        <div className="form-header">
                            <div className="form-icon">
                                <i className="bi bi-plus-circle"></i>
                            </div>
                            <h1 className="form-title">Create New Session</h1>
                            <p className="form-subtitle">Set up a new facial recognition session</p>
                        </div>

                        {error && (
                            <div className="alert-custom alert-danger">
                                <i className="bi bi-exclamation-circle"></i>
                                <span>{error}</span>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="form-content">
                            <div className="form-group">
                                <label htmlFor="name">Session Name *</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-pencil"></i>
                                    <input
                                        type="text"
                                        id="name"
                                        name="name"
                                        placeholder="e.g., Team Meeting - Feb 18"
                                        value={formData.name}
                                        onChange={handleChange}
                                        required
                                        disabled={submitting}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="description">Description (Optional)</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-file-text"></i>
                                    <textarea
                                        id="description"
                                        name="description"
                                        placeholder="Add any notes about this session..."
                                        value={formData.description}
                                        onChange={handleChange}
                                        rows="3"
                                        disabled={submitting}
                                        style={{
                                            paddingLeft: '2.5rem',
                                            paddingRight: '0.75rem',
                                            paddingTop: '0.75rem',
                                            paddingBottom: '0.75rem',
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="roster">
                                    Select Roster (Optional)
                                    <span className="hint"> - People will be auto-populated from the roster</span>
                                </label>
                                <div className="input-wrapper">
                                    <i className="bi bi-people"></i>
                                    <select
                                        id="roster"
                                        name="roster"
                                        value={formData.roster}
                                        onChange={handleChange}
                                        disabled={submitting || loading}
                                    >
                                        <option value="">-- No Roster --</option>
                                        {rosters.map(roster => (
                                            <option key={roster.id} value={roster.id}>
                                                {roster.name} ({roster.people_count} people)
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="session_type">Session Type (Optional)</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-layers"></i>
                                    <select
                                        id="session_type"
                                        name="session_type"
                                        value={formData.session_type}
                                        onChange={handleChange}
                                        disabled={submitting}
                                    >
                                        <option value="">-- Select Type --</option>
                                        <option value="recognition">Face Recognition</option>
                                        <option value="enrollment">Face Enrollment</option>
                                        <option value="verification">Face Verification</option>
                                    </select>
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="btn-submit"
                                disabled={submitting || loading}
                            >
                                {submitting ? (
                                    <>
                                        <span className="spinner"></span>
                                        Creating Session...
                                    </>
                                ) : (
                                    <>
                                        <i className="bi bi-play-circle"></i>
                                        Create Session
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="form-footer">
                            <p>Need help? <a href="/sessions">View active sessions</a> or <a href="/rosters">manage rosters</a></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}