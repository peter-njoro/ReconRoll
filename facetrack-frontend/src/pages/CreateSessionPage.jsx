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