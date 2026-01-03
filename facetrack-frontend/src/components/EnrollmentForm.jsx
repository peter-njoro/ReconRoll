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
        <div className="enrollment-form">
            <h2>Enroll Student</h2>
            
            {message && (
                <div className={`message ${message.type}`}>
                    {message.text}
                </div>
            )}

            {student && (
                <div className="success-info">
                    <p>Student enrolled: {student.name}</p>
                    <p>Encodings: {student.encodings_count}</p>
                </div>
            )}

            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    name="name"
                    placeholder="Student Name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                />

                <input
                    type="text"
                    name="student_id"
                    placeholder="Student ID"
                    value={formData.student_id}
                    onChange={handleInputChange}
                    required
                />

                <input
                    type="number"
                    name="class_group"
                    placeholder="Class Group (optional)"
                    value={formData.class_group}
                    onChange={handleInputChange}
                />

                <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handleImageChange}
                    required
                />
                <p>Selected: {images.length} images</p>

                <button type="submit" disabled={loading}>
                    {loading ? 'Enrolling...' : 'Enroll Student'}
                </button>
            </form>

            {progress > 0 && progress < 100 && (
                <div className="progress">
                    <div className="progress-bar" style={{ width: `${progress}%` }}>
                        {progress}%
                    </div>
                </div>
            )}
        </div>
    );
}