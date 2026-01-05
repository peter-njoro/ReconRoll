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
                                <label htmlFor="subject">Session Subject *</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-pencil"></i>
                                    <input
                                        type="text"
                                        id="subject"
                                        name="subject"
                                        placeholder="e.g., CS101 - Lecture 5"
                                        value={formData.subject}
                                        onChange={handleChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="class_group">Class Group (Optional)</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-folder"></i>
                                    <input
                                        type="number"
                                        id="class_group"
                                        name="class_group"
                                        placeholder="Enter class group ID"
                                        value={formData.class_group}
                                        onChange={handleChange}
                                    />
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