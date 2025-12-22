import apiClient from './client';

export const recognitionService = {
    // Home/Info
    getInfo: () => apiClient.get('/info/'),

    // Student Enrollment (adjust based on your actual endpoints)
    enrollStudent: (formData) => apiClient.post('/students/enroll/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    }),
    
    // Session Management (these match the ViewSet)
    listSessions: () => apiClient.get('/sessions/'),
    createSession: (data) => apiClient.post('/sessions/', data),
    getSession: (sessionId) => apiClient.get(`/sessions/${sessionId}/`),
    
    // Add other custom endpoints as needed
};