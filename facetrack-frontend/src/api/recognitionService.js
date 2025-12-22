import apiClient from './client';

export const recognitionService = {
    // Home/Info
    getInfo: () => apiClient.get('/'),

    // Student Enrollment
    enrollStudent: (formData) => apiClient.post('/recognition/enroll/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    getEnrollSchema: () => apiClient.get('/recognition/enroll/'),
    getEnrollProgress: () => apiClient.get('/recognition/enroll-progress/'),

    // Session Management
    createSession: (data) => apiClient.post('/recognition/session/create/', data),
    getCreateSessionSchema: () => apiClient.get('/recognition/session/create/'),
    getSession: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/`),
    endSession: (sessionId) => apiClient.post(`/recognition/session/${sessionId}/end/`),
    listSessions: () => apiClient.get('/recognition/sessions/'),

    // Session Details (Partials)
    getSessionEvents: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/events/`),
    getPresentStudents: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/present/`),
    getAbsentStudents: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/absent/`),
    getUnidentifiedFaces: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/unidentified/`),
    getProgress: (sessionId) => apiClient.get(`/recognition/session/${sessionId}/progress/`),
};