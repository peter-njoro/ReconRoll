import apiClient from './client';

export const recognitionService = {
    // -----------------------------------------------------------------------
    // Info
    // -----------------------------------------------------------------------
    getInfo: () => apiClient.get('/info/'),

    enrollStudent: (formData) =>
        apiClient.post('/enroll/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        }),

    // -----------------------------------------------------------------------
    // Session endpoints
    // -----------------------------------------------------------------------

    listSessions: () => apiClient.get('/sessions/'),
    getSession: (sessionId) => apiClient.get(`/session/${sessionId}/`),
    createSession: (data) => apiClient.post('/session/create/', data),
    deleteSession: (sessionId) => apiClient().delete(`/session/${sessionId}/`),


    // -----------------------------------------------------------------------
    // Sessions – control actions  (DRF router)
    // -----------------------------------------------------------------------

    startSession: (sessionId, devMode = false) =>
        apiClient.post(
            `/session/${sessionId}/start/`,
            {},
            {
                params: { dev_mode: devMode },
            }
        ),

    stopSession: (sessionId) => apiClient.post(`/session/${sessionId}/stop/`),
    stopAllSessions: () => apiClient.post('/sessions/stop_all/'),
    getSessionStatus: (sessionId) => apiClient.get(`/session/${sessionId}/status/`),

    // -----------------------------------------------------------------------
    // Sessions – update  (DRF router)
    // -----------------------------------------------------------------------

    updateSessionFull: (sessionId, data) => apiClient().put(`/session/${sessionId}/`, data),
    updateSession: (sessionId, data) => apiClient.patch(`/session/${sessionId}/`, data),

    // -----------------------------------------------------------------------
    // Frame upload (DRF router)
    // -----------------------------------------------------------------------

    uploadFrame: (sessionId, frameData, signal) => {
        if (!sessionId) {
            console.error('[uploadFrame] sessionId is missing/undefined');
            return Promise.reject(new Error('Session ID is required for frame upload'));
        }
        if (!frameData) {
            console.error('[uploadFrame] frameData is missing/undefined');
            return Promise.reject(new Error('Frame data is required'));
        }
        
        // Convert base64 data URL to binary blob
        const base64String = frameData.split(',')[1]; // Remove "data:image/jpeg;base64," prefix
        const binaryString = atob(base64String);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: 'image/jpeg' });
        
        // Create FormData for multipart upload
        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');
        
        // Use DRF router URL pattern: /api/sessions/<pk>/upload_frame/
        const url = `/sessions/${sessionId}/upload_frame/`;
        console.debug(`[uploadFrame] sessionId="${sessionId}"`);
        console.debug(`[uploadFrame] Calling POST ${url} with multipart/form-data`);
        
        // IMPORTANT: Let axios set Content-Type automatically for FormData (with boundary)
        // We must override the default 'application/json' header
        return apiClient.post(url, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            signal,
        });
    },

    // -----------------------------------------------------------------------
    // Session detail data – traditional Django partial views.
    //
    // Each partial returns  { status, session_id, <key>: [...] }
    // We unwrap <key> here so the caller receives the array / object directly
    // in response.data, matching what SessionDetailPage expects.
    // -----------------------------------------------------------------------

    getPresentPeople: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/present_partial/`)
            .then((res) => ({ ...res, data: res.data.present_people })),

    getAbsentPeople: (sessionId) =>
        apiClient
            .get(`/session/${sessionId}/absent_partial/`)
            .then((res) => ({ ...res, data: res.data.absent_people })),

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
    // People & Rosters
    // -----------------------------------------------------------------------
    getPeopleWithEncodings: () => apiClient.get('/people/'),
    getPersonDetail: (personId) => apiClient.get(`/people/${personId}/`),
    
    // Roster management
    listRosters: () => apiClient.get('/rosters/'),
    getRosterDetail: (rosterId) => apiClient.get(`/roster/${rosterId}/`),
    createRoster: (data) => apiClient.post('/roster/create/', data),
    updateRoster: (rosterId, data) => apiClient.post(`/roster/${rosterId}/update/`, data),
    deleteRoster: (rosterId) => apiClient.delete(`/roster/${rosterId}/delete/`),
    
    // Legacy - sets expected people for a session directly
    createRosterForSession: (sessionId, personIds, replace = true) =>
        apiClient.post('/roster/create/', {
            session_id: sessionId,
            person_ids: personIds,
            replace: replace,
        }),
};