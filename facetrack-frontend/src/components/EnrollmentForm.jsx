import { useState } from 'react';
import { recognitionService } from '../api/recognitionService';

export function EnrollmentForm() {
    const [formData, setFormData] = useState({
        name: '',
        student_id: '',
        email: '',
        course: '',
        year_of_study: '1',
    });
    const [images, setImages] = useState([]);
    const [progress, setProgress] = useState(0);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [student, setStudent] = useState(null);

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
        data.append('name', formData.name);
        data.append('student_id', formData.student_id);
        
        if (formData.email) {
            data.append('email', formData.email);
        }
        if (formData.course) {
            data.append('course', formData.course);
        }
        if (formData.year_of_study) {
            data.append('year_of_study', formData.year_of_study);
        }
        
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
            setStudent(response.data.student);
            setFormData({ name: '', student_id: '', email: '', course: '', year_of_study: '1' });
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
        <div className="enrollment-page">
            <div className="container-lg">
                <div className="enrollment-container">
                    <div className="enrollment-card">
                        <div className="form-header">
                            <div className="form-icon">
                                <i className="bi bi-person-plus-fill"></i>
                            </div>
                            <h1 className="form-title">Enroll Student</h1>
                            <p className="form-subtitle">Register a student for facial recognition</p>
                        </div>

                        {message && (
                            <div 
                                className={`alert-custom alert-${message.type}`}
                                style={message.type === 'error' ? {
                                    borderLeft: `4px solid var(--error-color)`,
                                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                                    color: 'var(--error-color)'
                                } : {}}
                            >
                                <i className={`bi bi-${message.type === 'success' ? 'check-circle' : 'exclamation-circle'}`}></i>
                                <div style={{ whiteSpace: 'pre-wrap' }}>
                                    {message.text}
                                </div>
                            </div>
                        )}

                        {student && (
                            <div className="success-info-card">
                                <div className="success-icon">
                                    <i className="bi bi-check-circle"></i>
                                </div>
                                <h3 className="success-title">Enrollment Successful!</h3>
                                <div className="student-details">
                                    <p><strong>Student Name:</strong> {student.name}</p>
                                    <p><strong>Facial Encodings:</strong> {student.encodings_count}</p>
                                </div>
                            </div>
                        )}

                        <form onSubmit={handleSubmit} className="enrollment-form">
                            <div className="form-group">
                                <label htmlFor="name">Student Name *</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-person"></i>
                                    <input
                                        type="text"
                                        id="name"
                                        name="name"
                                        placeholder="Enter student's full name"
                                        value={formData.name}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="student_id">Student ID / Registration Number *</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-card-text"></i>
                                    <input
                                        type="text"
                                        id="student_id"
                                        name="student_id"
                                        placeholder="Enter registration number"
                                        value={formData.student_id}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="email">Email Address (Optional)</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-envelope"></i>
                                    <input
                                        type="email"
                                        id="email"
                                        name="email"
                                        placeholder="Enter email address"
                                        value={formData.email}
                                        onChange={handleInputChange}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="course">Course (Optional)</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-book"></i>
                                    <input
                                        type="text"
                                        id="course"
                                        name="course"
                                        placeholder="Enter course name"
                                        value={formData.course}
                                        onChange={handleInputChange}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label htmlFor="year_of_study">Year of Study (Optional)</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-calendar"></i>
                                    <select
                                        id="year_of_study"
                                        name="year_of_study"
                                        value={formData.year_of_study}
                                        onChange={handleInputChange}
                                    >
                                        <option value="1">Year 1</option>
                                        <option value="2">Year 2</option>
                                        <option value="3">Year 3</option>
                                        <option value="4">Year 4</option>
                                        <option value="5">Year 5</option>
                                    </select>
                                </div>
                            </div>

                            <div className="form-group image-upload">
                                <label htmlFor="images">Face Images *</label>
                                <div className="upload-wrapper">
                                    <input
                                        type="file"
                                        id="images"
                                        multiple
                                        accept="image/*"
                                        onChange={handleImageChange}
                                        disabled={loading}
                                    />
                                    <div className="upload-hint">
                                        <i className="bi bi-cloud-upload"></i>
                                        <p>Drag and drop your images here or click to browse</p>
                                        <span>Add multiple images one by one (minimum 3-5 clear face images recommended)</span>
                                    </div>
                                </div>

                                {images.length > 0 && (
                                    <div className="selected-images">
                                        <p className="selected-count">
                                            <i className="bi bi-check-circle-fill"></i>
                                            {images.length} image{images.length !== 1 ? 's' : ''} selected
                                        </p>
                                        <div className="image-list">
                                            {images.map((image, index) => (
                                                <div key={index} className="image-item">
                                                    <div className="image-info">
                                                        <i className="bi bi-image"></i>
                                                        <div className="image-details">
                                                            <span className="image-name">{image.name}</span>
                                                            <span className="image-size">
                                                                {(image.size / 1024).toFixed(2)} KB
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        className="remove-image-btn"
                                                        onClick={() => removeImage(index)}
                                                        disabled={loading}
                                                        title="Remove this image"
                                                    >
                                                        <i className="bi bi-trash"></i>
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button
                                type="submit"
                                className="btn-submit"
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <span className="spinner"></span>
                                        Enrolling Student...
                                    </>
                                ) : (
                                    <>
                                        <i className="bi bi-upload"></i>
                                        Enroll Student
                                    </>
                                )}
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
            </div>
        </div>
    );
}