import apiClient from './client';

export const recognitionService = {
    enrollStudent: (formData) =>
        apiClient.post('/enroll/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),
    // Session endpoints
    listSessions: () => apiClient.get('/sessions/'),
    getSession: (sessionId) => apiClient.get(`/sessions/${sessionId}/`),

     createSession: (data) => apiClient.post('/sessions/', data),

    updateSession: (sessionId, sessionData) => apiClient().put(`/sessions/${sessionId}/`, sessionData),

    deleteSession: (sessionId) => apiClient().delete(`/sessions/${sessionId}/`),

    // Session control endpoints
    startSession: (sessionId, devMode = false) =>
        apiClient().post(`/sessions/${sessionId}/start/`, {}, {
            params: { dev_mode: devMode ? 'true' : 'false' }
        }),

    stopSession: (sessionId) => apiClient.post(`/sessions/${sessionId}/stop/`),

    stopAllSessions: () => apiClient.post('/sessions/stop_all/'),

    getSessionStatus: (sessionId) => apiClient.get(`/sessions/${sessionId}/status/`),

    // Frame upload endpoint (NEW)
    uploadFrame: (sessionId, frameData) =>
        apiClient.post(`/sessions/${sessionId}/upload_frame/`, {
            frame: frameData
        }),

    // Session data endpoints
    getPresentStudents: (sessionId) => apiClient.get(`/sessions/${sessionId}/present_partial/`),

    getAbsentStudents: (sessionId) => apiClient.get(`/sessions/${sessionId}/absent_partial/`),

    getSessionEvents: (sessionId) => apiClient.get(`/sessions/${sessionId}/events_partial/`),

    getProgress: (sessionId) => apiClient.get(`/sessions/${sessionId}/progress_partial/`),

    // Unidentified faces endpoint (NEW)
    getUnidentifiedFaces: (sessionId) => apiClient.get(`/sessions/${sessionId}/unidentified_partial/`),

    // Student endpoints
    // getStudents: () => apiClient.get('/students/'),

    // getStudent: (studentId) => apiClient.get(`/students/${studentId}/`),

    // createStudent: (studentData) => apiClient.post('/students/', studentData),

    // updateStudent: (studentId, studentData) => apiClient.put(`/students/${studentId}/`, studentData),

    // deleteStudent: (studentId) => apiClient.delete(`/students/${studentId}/`),

    // Class group endpoints
    // getClassGroups: () => apiClient.get('/class-groups/'),

    // getClassGroup: (groupId) => apiClient.get(`/class-groups/${groupId}/`),

    // createClassGroup: (groupData) => apiClient.post('/class-groups/', groupData),

    // updateClassGroup: (groupId, groupData) => apiClient.put(`/class-groups/${groupId}/`, groupData),

    // deleteClassGroup: (groupId) => apiClient.delete(`/class-groups/${groupId}/`),
};