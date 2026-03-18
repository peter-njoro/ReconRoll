import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { recognitionService } from '../api/recognitionService';

export function SessionDetailPage() {
    const { sessionId } = useParams();
    const [session, setSession] = useState(null);
    const [presentPeople, setPresentPeople] = useState([]);
    const [absentPeople, setAbsentPeople] = useState([]);
    const [unidentifiedFaces, setUnidentifiedFaces] = useState([]);
    const [events, setEvents] = useState([]);
    const [progress, setProgress] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    // Webcam state
    const [isWebcamActive, setIsWebcamActive] = useState(false);
    const [webcamError, setWebcamError] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const streamRef = useRef(null);
    const uploadIntervalRef = useRef(null);
    const isProcessingRef = useRef(false); // Ref for immediate access in interval

    // Fetch session data
    const fetchData = async () => {
        try {
            const [sessionRes, presentRes, absentRes, eventsRes, progressRes, unidentifiedRes] = await Promise.all([
                recognitionService.getSession(sessionId),
                recognitionService.getPresentPeople(sessionId),
                recognitionService.getAbsentPeople(sessionId),
                recognitionService.getSessionEvents(sessionId),
                recognitionService.getProgress(sessionId),
                recognitionService.getUnidentifiedFaces(sessionId),
            ]);

            setSession(sessionRes.data);
            setPresentPeople(presentRes.data || []);
            setAbsentPeople(absentRes.data || []);
            setEvents(eventsRes.data || []);
            setProgress(progressRes.data || null);
            setUnidentifiedFaces(unidentifiedRes.data || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();

        // Auto-refresh every 5 seconds if session is running
        let interval;
        if (autoRefresh) {
            interval = setInterval(fetchData, 5000);
        }

        return () => clearInterval(interval);
    }, [sessionId, autoRefresh]);

    // Start webcam
    const startWebcam = async () => {
        try {
            setWebcamError(null);
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                }
            });

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                streamRef.current = stream;
                setIsWebcamActive(true);
            }
        } catch (err) {
            console.error('Error accessing webcam:', err);
            setWebcamError('Failed to access webcam. Please ensure camera permissions are granted.');
        }
    };

    // Stop webcam
    const stopWebcam = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        setIsWebcamActive(false);

        // Stop frame uploads
        if (uploadIntervalRef.current) {
            clearInterval(uploadIntervalRef.current);
            uploadIntervalRef.current = null;
        }
    };

    // Capture and upload frame
    const captureAndUploadFrame = async () => {
        // Validate sessionId exists
        if (!sessionId) {
            console.error('Session ID is undefined in captureAndUploadFrame');
            return;
        }

        console.debug(`[captureAndUploadFrame] sessionId = "${sessionId}"`);

        // Check if processing is enabled (use ref for immediate access)
        if (!isProcessingRef.current) {
            console.debug('[captureAndUploadFrame] Not processing, skipping');
            return;
        }

        // Check if refs are available
        if (!videoRef.current) {
            console.warn('[captureAndUploadFrame] videoRef not available');
            return;
        }
        
        if (!canvasRef.current) {
            console.warn('[captureAndUploadFrame] canvasRef not available');
            return;
        }

        const video = videoRef.current;
        const canvas = canvasRef.current;

        // Check if video is ready
        if (video.videoWidth === 0 || video.videoHeight === 0) {
            console.warn('[captureAndUploadFrame] Video not ready yet (dimensions are 0)');
            return;
        }

        const context = canvas.getContext('2d');

        // Set canvas size to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw current video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert canvas to base64 JPEG
        const frameData = canvas.toDataURL('image/jpeg', 0.8);

        try {
            // Upload frame to backend
            console.debug(`[uploadFrame] Calling with sessionId: "${sessionId}"`);
            const response = await recognitionService.uploadFrame(sessionId, frameData);
            console.debug(`[uploadFrame] Success:`, response.data);
        } catch (err) {
            console.error('[uploadFrame] Error:', err.message);
            if (err.response) {
                console.error('[uploadFrame] Response:', err.response.data);
            }
        }
    };

    // Start recognition session
    const startRecognition = async () => {
        // Validate session ID
        if (!sessionId) {
            setError('Session ID is missing. Unable to start recognition.');
            console.error('[startRecognition] sessionId is undefined');
            return;
        }

        console.log(`[startRecognition] Starting with sessionId: "${sessionId}"`);

        try {
            setError(null);

            // Start the recognition thread on the backend
            console.debug(`[startRecognition] Calling startSession API...`);
            await recognitionService.startSession(sessionId);
            console.debug(`[startRecognition] startSession successful`);

            // Start webcam
            console.debug(`[startRecognition] Starting webcam...`);
            await startWebcam();

            // IMPORTANT: Set processing flag BEFORE starting interval
            // Use both state (for UI) and ref (for immediate access in interval)
            setIsProcessing(true);
            isProcessingRef.current = true;
            console.debug(`[startRecognition] Set isProcessing to true`);

            // Wait for backend to update session status and video to be ready
            // Poll the session status to ensure it's actually running
            console.debug(`[startRecognition] Waiting for session to be in_progress...`);
            let retries = 0;
            const maxRetries = 10;
            while (retries < maxRetries) {
                const statusRes = await recognitionService.getSession(sessionId);
                if (statusRes.data.session.status === 'in_progress') {
                    console.debug(`[startRecognition] Session is in_progress, starting frame uploads`);
                    break;
                }
                await new Promise(resolve => setTimeout(resolve, 200));
                retries++;
            }

            if (retries >= maxRetries) {
                throw new Error('Session did not start within expected time');
            }

            // Start uploading frames every 500ms (2 FPS)
            console.debug(`[startRecognition] Setting up frame upload interval...`);
            uploadIntervalRef.current = setInterval(() => {
                captureAndUploadFrame();
            }, 500);

            // Refresh data immediately
            await fetchData();
            console.log(`[startRecognition] Recognition started successfully`);
        } catch (err) {
            console.error('[startRecognition] Error:', err.message);
            setError('Failed to start recognition: ' + err.message);
            setIsProcessing(false);
            isProcessingRef.current = false;
        }
    };

    // Stop recognition session
    const stopRecognition = async () => {
        try {
            // Stop the recognition thread on the backend
            await recognitionService.stopSession(sessionId);

            // Stop webcam and uploads
            stopWebcam();
            setIsProcessing(false);
            isProcessingRef.current = false;

            // Refresh data
            await fetchData();
        } catch (err) {
            setError('Failed to stop recognition: ' + err.message);
        }
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopWebcam();
        };
    }, []);

    if (loading) {
        return (
            <div className="session-detail">
                <div className="session-detail-container">
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
                        <div className="loading-spinner"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="session-detail">
                <div className="session-detail-container">
                    <div className="error-alert">Error: {error}</div>
                </div>
            </div>
        );
    }

    if (!session) {
        return (
            <div className="session-detail">
                <div className="session-detail-container">
                    <div className="error-alert">Session not found</div>
                </div>
            </div>
        );
    }

    return (
        <div className="session-detail">
            <div className="session-detail-container">
                <div className="session-detail-header">
                    <h1 className="session-detail-title">{session.name}</h1>
                    <div className="session-detail-info">
                        <div className="detail-info-item">
                            <div className="detail-info-label">Status</div>
                            <div className="detail-info-value">
                                <span className={`status-badge ${session.status === 'in_progress' ? 'running' : 'stopped'}`}>
                                    {session.status === 'in_progress' ? '🟢 Running' : '🔴 Stopped'}
                                </span>
                            </div>
                        </div>
                        <div className="detail-info-item">
                            <div className="detail-info-label">Type</div>
                            <div className="detail-info-value">{session.session_type || 'N/A'}</div>
                        </div>
                        <div className="detail-info-item">
                            <div className="detail-info-label">Created At</div>
                            <div className="detail-info-value">{new Date(session.created_at).toLocaleDateString()}</div>
                        </div>
                    </div>
                </div>

                {/* Webcam Section */}
                <div className="webcam-section">
                    <h2><i className="bi bi-camera-video"></i> Live Camera Feed</h2>

                    {webcamError && (
                        <div className="error-alert" style={{ marginBottom: '1rem' }}>
                            {webcamError}
                        </div>
                    )}

                    <div className="webcam-container">
                        <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            muted
                            style={{
                                width: '100%',
                                maxWidth: '640px',
                                borderRadius: '8px',
                                backgroundColor: '#000',
                                display: isWebcamActive ? 'block' : 'none'
                            }}
                        />

                        {!isWebcamActive && (
                            <div style={{
                                width: '100%',
                                maxWidth: '640px',
                                height: '480px',
                                backgroundColor: '#1f2937',
                                borderRadius: '8px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#9ca3af'
                            }}>
                                <i className="bi bi-camera-video-off" style={{ fontSize: '48px' }}></i>
                            </div>
                        )}

                        {/* Hidden canvas for frame capture */}
                        <canvas ref={canvasRef} style={{ display: 'none' }} />
                    </div>

                    <div className="webcam-controls" style={{ marginTop: '1rem', display: 'flex', gap: '1rem' }}>
                        {!isProcessing ? (
                            <button
                                className="btn-start-recognition"
                                onClick={startRecognition}
                                disabled={session.status === 'ended'}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    backgroundColor: '#10b981',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: session.status === 'ended' ? 'not-allowed' : 'pointer',
                                    fontSize: '16px',
                                    fontWeight: '500'
                                }}
                            >
                                <i className="bi bi-play-circle"></i> Start Recognition
                            </button>
                        ) : (
                            <button
                                className="btn-stop-recognition"
                                onClick={stopRecognition}
                                style={{
                                    padding: '0.75rem 1.5rem',
                                    backgroundColor: '#ef4444',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    fontSize: '16px',
                                    fontWeight: '500'
                                }}
                            >
                                <i className="bi bi-stop-circle"></i> Stop Recognition
                            </button>
                        )}

                        {isProcessing && (
                            <span style={{
                                display: 'flex',
                                alignItems: 'center',
                                color: '#10b981',
                                fontWeight: '500'
                            }}>
                                <div className="loading-spinner" style={{
                                    width: '20px',
                                    height: '20px',
                                    marginRight: '0.5rem',
                                    borderWidth: '2px'
                                }}></div>
                                Processing...
                            </span>
                        )}
                    </div>
                </div>

                {progress && (
                    <div className="progress-section">
                        <h2><i className="bi bi-graph-up"></i> Recognition Progress</h2>
                        <div className="progress-stats">
                            <div className="stat-item">
                                <div className="stat-value">{progress.present_count}</div>
                                <div className="stat-label">Present</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-value">{progress.total_expected}</div>
                                <div className="stat-label">Expected</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-value">{progress.attendance_percentage}%</div>
                                <div className="stat-label">Attendance</div>
                            </div>
                            <div className="stat-item">
                                <div className="stat-value">{progress.unknown_count}</div>
                                <div className="stat-label">Unidentified</div>
                            </div>
                        </div>
                        <div className="progress-bar-large">
                            <div
                                className="progress-fill"
                                style={{ width: `${progress.attendance_percentage}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* Unidentified Faces Section */}
                {unidentifiedFaces.length > 0 && (
                    <div className="unidentified-section">
                        <h2><i className="bi bi-question-circle"></i> Unidentified Faces ({unidentifiedFaces.length})</h2>
                        <div className="unidentified-grid" style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                            gap: '1rem',
                            marginTop: '1rem'
                        }}>
                            {unidentifiedFaces.map(face => (
                                <div key={face.id} className="unidentified-item" style={{
                                    border: '2px solid #f59e0b',
                                    borderRadius: '8px',
                                    padding: '0.5rem',
                                    textAlign: 'center'
                                }}>
                                    {face.cropped_face && (
                                        <img
                                            src={face.cropped_face}
                                            alt="Unidentified face"
                                            style={{
                                                width: '100%',
                                                borderRadius: '4px',
                                                marginBottom: '0.5rem'
                                            }}
                                        />
                                    )}
                                    <small style={{ color: '#6b7280' }}>
                                        {face.timestamp ? new Date(face.timestamp).toLocaleTimeString() : 'Unknown time'}
                                    </small>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="people-section">
                    <div className="people-list">
                        <h3><i className="bi bi-check-circle"></i> Present ({presentPeople.length})</h3>
                        {presentPeople.length > 0 ? (
                            <ul>
                                {presentPeople.map(person => (
                                    <li key={person.id}>
                                        <i className="bi bi-person-check"></i> {person.name || person.full_name} ({person.identification_number || 'N/A'})
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: '#6b7280', textAlign: 'center', paddingTop: '1rem' }}>No people present yet</p>
                        )}
                    </div>

                    <div className="people-list">
                        <h3><i className="bi bi-x-circle"></i> Absent ({absentPeople.length})</h3>
                        {absentPeople.length > 0 ? (
                            <ul>
                                {absentPeople.map(person => (
                                    <li key={person.id}>
                                        <i className="bi bi-person-x"></i> {person.name || person.full_name} ({person.identification_number || 'N/A'})
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: '#6b7280', textAlign: 'center', paddingTop: '1rem' }}>No absent people</p>
                        )}
                    </div>
                </div>

                {events.length > 0 && (
                    <div className="events-section">
                        <h2><i className="bi bi-clock-history"></i> Recent Events ({events.length})</h2>
                        <div className="events-list">
                            {events.map(event => (
                                <div key={event.id} className={`event ${event.severity || 'info'}`}>
                                    <span className="type">[{event.event_type}]</span>
                                    <span className="message">{event.message}</span>
                                    <span className="time">
                                        {new Date(event.timestamp).toLocaleTimeString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="session-controls">
                    <label className="controls-checkbox">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                        />
                        <span>Auto-refresh every 5 seconds</span>
                    </label>
                </div>
            </div>
        </div>
    );
}