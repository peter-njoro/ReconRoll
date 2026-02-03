import apiClient from './client';

export const recognitionService = {
    enrollStudent: (formData) =>
        apiClient.post('/enroll/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),

    // -----------------------------------------------------------------------
    // Session endpoints
    // -----------------------------------------------------------------------

    listSessions: () => apiClient.get('/sessions/'),
    getSession: (sessionId) => apiClient.get(`/sessions/${sessionId}/`),
    createSession: (data) => apiClient.post('/sessions/', data),
    deleteSession: (sessionId) => apiClient().delete(`/sessions/${sessionId}/`),

    // -----------------------------------------------------------------------
    // Sessions – control actions  (DRF router)
    // -----------------------------------------------------------------------

    startSession: (sessionId, devMode = false) =>
        apiClient.post(`/session/${sessionId}/start/`, {}, {
            params: { dev_mode: devMode ? 'true' : 'false' },
        }),
    stopSession: (sessionId) => apiClient.post(`/sessions/${sessionId}/stop/`),
    stopAllSessions: () => apiClient.post('/sessions/stop_all/'),
    getSessionStatus: (sessionId) => apiClient.get(`/sessions/${sessionId}/status/`),

    // -----------------------------------------------------------------------
    // Sessions – update  (DRF router)
    // -----------------------------------------------------------------------

    updateSessionFull:    (sessionId, data) => apiClient().put(`/sessions/${sessionId}/`, data),
    updateSession:        (sessionId, data) => apiClient.patch(`/sessions/${sessionId}/`, data),

    // -----------------------------------------------------------------------
    // Frame upload (DRF router)
    // -----------------------------------------------------------------------

    uploadFrame: (sessionId, frameData) =>
        apiClient.post(`/sessions/${sessionId}/upload_frame/`, { frame: frameData }),

    // -----------------------------------------------------------------------
    // Session detail data – traditional Django partial views.
    //
    // Each partial returns  { status, session_id, <key>: [...] }
    // We unwrap <key> here so the caller receives the array / object directly
    // in response.data, matching what SessionDetailPage expects.
    // -----------------------------------------------------------------------

    getPresentStudents: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/present_partial/`)
            .then((res) => ({ ...res, data: res.data.present_students })),

    getAbsentStudents: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/absent_partial/`)
            .then((res) => ({ ...res, data: res.data.absent_students })),

    getSessionEvents: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/events_partial/`)
            .then((res) => ({ ...res, data: res.data.events })),

    getProgress: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/progress_partial/`)
            .then((res) => ({ ...res, data: res.data.progress })),

    getUnidentifiedFaces: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/unidentified_partial/`)
            .then((res) => ({ ...res, data: res.data.unidentified_faces })),

    // -----------------------------------------------------------------------
    // Students  (DRF router)
    // -----------------------------------------------------------------------
    // getStudents:    ()           => api.get('/students/'),
    // getStudent:     (id)         => api.get(`/students/${id}/`),
    // createStudent:  (data)       => api.post('/students/', data),
    // updateStudent:  (id, data)   => api.put(`/students/${id}/`, data),
    // deleteStudent:  (id)         => api.delete(`/students/${id}/`),

    // -----------------------------------------------------------------------
    // Class Groups  (DRF router)
    // -----------------------------------------------------------------------
    // getClassGroups:    ()        => api.get('/class-groups/'),
    // getClassGroup:     (id)      => api.get(`/class-groups/${id}/`),
    // createClassGroup:  (data)    => api.post('/class-groups/', data),
    // updateClassGroup:  (id, data)=> api.put(`/class-groups/${id}/`, data),
    // deleteClassGroup:  (id)      => api.delete(`/class-groups/${id}/`),
};