import apiClient from './client';

export const recognitionService = {
    getInfo: () => apiClient.get('/info/'),

    enrollStudent: (formData) =>
        apiClient.post('/enroll/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),

    listSessions: () => apiClient.get('/sessions/'),
    createSession: (data) => apiClient.post('/sessions/', data),
    getSession: (sessionId) => apiClient.get(`/sessions/${sessionId}/`),

    // 🔽 ADD THESE 🔽
    getPresentStudents: (id) => apiClient.get(`/sessions/${id}/present/`),
    getAbsentStudents: (id) => apiClient.get(`/sessions/${id}/absent/`),
    getSessionEvents: (id) => apiClient.get(`/sessions/${id}/events/`),
    getProgress: (id) => apiClient.get(`/sessions/${id}/progress/`),
    endSession: (id) => apiClient.post(`/sessions/${id}/end/`),
};
