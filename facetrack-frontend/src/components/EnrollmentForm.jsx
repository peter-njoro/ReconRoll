import { useState } from 'react';
import { recognitionService } from '../api/recognitionService';

export function EnrollmentForm() {
    const [formData, setFormData] = useState({
        name: '',
        student_id: '',
        class_group: '',
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
        setImages(Array.from(e.target.files));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        const data = new FormData();
        data.append('name', formData.name);
        data.append('student_id', formData.student_id);
        if (formData.class_group) {
            data.append('class_group', formData.class_group);
        }
        images.forEach(image => {
            data.append('face_images', image);
        });

        try {
            const response = await recognitionService.enrollStudent(data);
            setMessage({
                type: 'success',
                text: response.data.message
            });
            setStudent(response.data.student);
            setFormData({ name: '', student_id: '', class_group: '' });
            setImages([]);
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.response?.data?.message || error.message
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
                            <div className={`alert-custom alert-${message.type}`}>
                                <i className={`bi bi-${message.type === 'success' ? 'check-circle' : 'exclamation-circle'}`}></i>
                                <span>{message.text}</span>
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
                                <label htmlFor="student_id">Student ID *</label>
                                <div className="input-wrapper">
                                    <i className="bi bi-card-text"></i>
                                    <input
                                        type="text"
                                        id="student_id"
                                        name="student_id"
                                        placeholder="Enter student ID"
                                        value={formData.student_id}
                                        onChange={handleInputChange}
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
                                        onChange={handleInputChange}
                                    />
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
                                        required
                                    />
                                    <div className="upload-hint">
                                        <i className="bi bi-cloud-upload"></i>
                                        <p>Drag and drop your images here or click to browse</p>
                                        <span>Minimum 3-5 clear face images recommended</span>
                                    </div>
                                </div>
                                {images.length > 0 && (
                                    <div className="selected-images">
                                        <p className="selected-count">
                                            <i className="bi bi-check-circle-fill"></i>
                                            {images.length} image{images.length !== 1 ? 's' : ''} selected
                                        </p>
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