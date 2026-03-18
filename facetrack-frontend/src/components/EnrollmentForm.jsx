import { useState } from 'react';
import { recognitionService } from '../api/recognitionService';

export function EnrollmentForm() {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        identification_number: '',
        email: '',
        phone: '',
        date_of_birth: '',
        status: 'active',
        notes: '',
    });
    const [images, setImages] = useState([]);
    const [progress, setProgress] = useState(0);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [person, setPerson] = useState(null);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleImageChange = (e) => {
        const newImages = Array.from(e.target.files);
        setImages(prev => [...prev, ...newImages]);
        // Reset input so user can select the same file again
        e.target.value = '';
    };

    const removeImage = (index) => {
        setImages(prev => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        const data = new FormData();
        data.append('first_name', formData.first_name);
        data.append('last_name', formData.last_name);
        data.append('identification_number', formData.identification_number);
        if (formData.email) data.append('email', formData.email);
        if (formData.phone) data.append('phone', formData.phone);
        if (formData.date_of_birth) data.append('date_of_birth', formData.date_of_birth);
        if (formData.status) data.append('status', formData.status);
        if (formData.notes) data.append('notes', formData.notes);
        
        images.forEach(image => {
            data.append('face_images', image);
        });

        // Log what we're sending
        console.log('Sending form data:');
        for (let [key, value] of data.entries()) {
            console.log(`${key}: ${value}`);
        }

        try {
            const response = await recognitionService.enrollStudent(data);
            console.log('Success response:', response.data);
            
            setMessage({
                type: 'success',
                text: response.data.message
            });
            setPerson(response.data.person);
            setFormData({
                first_name: '',
                last_name: '',
                identification_number: '',
                email: '',
                phone: '',
                date_of_birth: '',
                status: 'active',
                notes: '',
            });
            setImages([]);
        } catch (error) {
            console.error('Error response:', error.response?.data);
            console.error('Full error:', error);
            
            // Extract detailed error messages from Django response
            let errorText = error.message;
            const responseData = error.response?.data;
            
            if (responseData) {
                // If there's a message field, use it
                if (responseData.message) {
                    errorText = responseData.message;
                }
                
                // If there are specific errors array, join them
                if (responseData.errors && Array.isArray(responseData.errors)) {
                    const detailedErrors = responseData.errors.filter(e => e && e.length > 0);
                    if (detailedErrors.length > 0) {
                        errorText = detailedErrors.join('\n');
                    }
                }
                
                // If there are field errors (dict), format them nicely
                if (responseData.errors && typeof responseData.errors === 'object' && !Array.isArray(responseData.errors)) {
                    const fieldErrors = Object.entries(responseData.errors)
                        .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
                        .join('\n');
                    if (fieldErrors) {
                        errorText = fieldErrors;
                    }
                }
            }
            
            setMessage({
                type: 'error',
                text: errorText
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-header">
                    <p className="auth-eyebrow">Enrollment</p>
                    <h1 className="auth-title">Enroll a person</h1>
                    <p className="auth-subtitle">Provide details and upload clear face images.</p>
                </div>

                {message && (
                    <div
                        className={`alert ${message.type === 'success' ? 'success' : 'error'}`}
                        style={{ whiteSpace: 'pre-wrap' }}
                    >
                        {message.text}
                    </div>
                )}

                {person && (
                    <div className="success-info-card">
                        <h3 className="success-title">Enrollment successful</h3>
                        <div className="person-details">
                            <p><strong>Name:</strong> {person.name}</p>
                            <p><strong>Encodings:</strong> {person.encodings_count}</p>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="field-row">
                        <label className="field">
                            <span>First name *</span>
                            <input
                                type="text"
                                id="first_name"
                                name="first_name"
                                placeholder="First name"
                                value={formData.first_name}
                                onChange={handleInputChange}
                                required
                            />
                        </label>
                        <label className="field">
                            <span>Last name *</span>
                            <input
                                type="text"
                                id="last_name"
                                name="last_name"
                                placeholder="Last name"
                                value={formData.last_name}
                                onChange={handleInputChange}
                                required
                            />
                        </label>
                    </div>

                    <label className="field">
                        <span>Identification number *</span>
                        <input
                            type="text"
                            id="identification_number"
                            name="identification_number"
                            placeholder="ID or employee number"
                            value={formData.identification_number}
                            onChange={handleInputChange}
                            required
                        />
                    </label>

                    <div className="field-row">
                        <label className="field">
                            <span>Email</span>
                            <input
                                type="email"
                                id="email"
                                name="email"
                                placeholder="name@company.com"
                                value={formData.email}
                                onChange={handleInputChange}
                            />
                        </label>
                        <label className="field">
                            <span>Phone</span>
                            <input
                                type="tel"
                                id="phone"
                                name="phone"
                                placeholder="Optional"
                                value={formData.phone}
                                onChange={handleInputChange}
                            />
                        </label>
                    </div>

                    <div className="field-row">
                        <label className="field">
                            <span>Date of birth</span>
                            <input
                                type="date"
                                id="date_of_birth"
                                name="date_of_birth"
                                value={formData.date_of_birth}
                                onChange={handleInputChange}
                            />
                        </label>
                        <label className="field">
                            <span>Status</span>
                            <select
                                id="status"
                                name="status"
                                value={formData.status}
                                onChange={handleInputChange}
                            >
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                                <option value="suspended">Suspended</option>
                            </select>
                        </label>
                    </div>

                    <label className="field">
                        <span>Notes</span>
                        <textarea
                            id="notes"
                            name="notes"
                            rows="3"
                            placeholder="Optional notes"
                            value={formData.notes}
                            onChange={handleInputChange}
                        />
                    </label>

                    <div className="field">
                        <span>Face images *</span>
                        <input
                            type="file"
                            id="images"
                            multiple
                            accept="image/*"
                            onChange={handleImageChange}
                            disabled={loading}
                        />

                        {images.length > 0 && (
                            <div className="selected-images">
                                <p className="selected-count">
                                    {images.length} image{images.length !== 1 ? 's' : ''} selected
                                </p>
                                <div className="image-list">
                                    {images.map((image, index) => (
                                        <div key={index} className="image-item">
                                            <div className="image-info">
                                                <span className="image-name">{image.name}</span>
                                                <span className="image-size">
                                                    {(image.size / 1024).toFixed(2)} KB
                                                </span>
                                            </div>
                                            <button
                                                type="button"
                                                className="remove-image-btn"
                                                onClick={() => removeImage(index)}
                                                disabled={loading}
                                                title="Remove this image"
                                            >
                                                Remove
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={loading}
                    >
                        {loading ? 'Enrolling...' : 'Enroll person'}
                    </button>
                </form>

                {progress > 0 && progress < 100 && (
                    <div className="progress-section">
                        <div className="progress-bar">
                            <div
                                className="progress-fill"
                                style={{ width: `${progress}%` }}
                            ></div>
                        </div>
                        <p className="progress-text">{progress}% Complete</p>
                    </div>
                )}
            </div>
        </div>
    );
}
