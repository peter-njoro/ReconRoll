import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function CreateSessionPage() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        session_type: 'recognition',
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
            // Backend expects start_time (datetime) and status
            // Default to current time and 'scheduled' status
            const now = new Date().toISOString();
            
            const response = await recognitionService.createSession({
                name: formData.name,
                description: formData.description || '',
                session_type: formData.session_type,
                start_time: now,  // Required by backend
                status: 'scheduled',  // Default status
            });

            console.log('[CreateSessionPage] API Response:', response);
            const sessionId = response.data.session?.id || response.data.id;
            console.log('[CreateSessionPage] Extracted sessionId:', sessionId);
            
            if (!sessionId) {
                setError('Failed to extract session ID from response');
                return;
            }
            
            // Redirect to roster selection page to add expected people
            console.log(`[CreateSessionPage] Navigating to /session/${sessionId}/roster`);
            navigate(`/session/${sessionId}/roster`);
        } catch (err) {
            console.error('[CreateSessionPage] Error:', err);
            const errorMessage = 
                err.response?.data?.message ||
                err.response?.data?.errors?.join(', ') ||
                err.message ||
                'Failed to create session';
            setError(errorMessage);
        } finally {
            setLoading(false);
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
                                <label htmlFor="session_type">Session Type</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-layers"></i>
                                    <select
                                        id="session_type"
                                        name="session_type"
                                        value={formData.session_type}
                                        onChange={handleChange}
                                    >
                                        <option value="recognition">Face Recognition</option>
                                        <option value="enrollment">Face Enrollment</option>
                                        <option value="verification">Face Verification</option>
                                    </select>
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="btn-submit"
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <span className="spinner"></span>
                                        Creating Session...
                                    </>
                                ) : (
                                    <>
                                        <i className="bi bi-play-circle"></i>
                                        Create and Start Session
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="form-footer">
                            <p>Need help? <a href="/sessions">View active sessions</a></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}