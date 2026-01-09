import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function CreateSessionPage() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        subject: '',
        class_group_name: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    console.log('CreateSessionPage rendered with formData:', formData);
    console.log('Current loading state:', loading);
    console.log('Current error state:', error);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        console.log(`Form field changed: ${name} = ${value}`);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        
            console.log('Form submitted with data:', {
            subject: formData.subject,
            class_group_name: formData.class_group_name || null,
        });

        try {
            const response = await recognitionService.createSession({
                subject: formData.subject,
                class_group_name: formData.class_group_name || null,
            });

            console.log('Session created successfully:', response.data);
            // response.data contains the session object; navigate using its id
            alert('Session created');
            navigate(`/session/${response.data.id}`);
        } catch (err) {
            console.error('Error creating session:', err);
            console.error('Error response data:', err.response?.data);
            console.error('Error message:', err.message);
            
            const errorMessage = 
                err.response?.data?.message ||
                err.response?.data?.message ||
                err.response?.data?.errors?.join(', ') ||
                err.message;
            
            console.log('Setting error state to:', errorMessage);
            setError(errorMessage);
        } finally {
            setLoading(false);
            console.log('Request completed, loading state set to false');
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
                                            type="text"
                                            id="class_group_name"
                                            name="class_group_name"
                                            placeholder="Enter class group name (e.g., CS101)"
                                            value={formData.class_group_name}
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