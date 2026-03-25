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

    const [isWebcamActive, setIsWebcamActive] = useState(false);
    const [webcamError, setWebcamError] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const streamRef = useRef(null);
    const uploadIntervalRef = useRef(null);
    const isProcessingRef = useRef(false);
    const uploadInFlightRef = useRef(false);  // prevent overlapping uploads
    const abortControllerRef = useRef(null);  // cancel in-flight requests on stop

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
        let interval;
        if (autoRefresh) interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, [sessionId, autoRefresh]);

    const startWebcam = async () => {
        try {
            setWebcamError(null);

            // mediaDevices is only available in secure contexts (HTTPS or localhost).
            // Over plain HTTP on an external IP the browser blocks it entirely.
            if (!navigator.mediaDevices?.getUserMedia) {
                setWebcamError(
                    'Camera access requires a secure connection (HTTPS). ' +
                    'Please access this page over HTTPS or use localhost.'
                );
                return;
            }

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
            });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                streamRef.current = stream;
                setIsWebcamActive(true);
            }
        } catch (err) {
            console.error('Error accessing webcam:', err);
            if (err.name === 'NotAllowedError') {
                setWebcamError('Camera permission denied. Please allow camera access in your browser settings.');
            } else if (err.name === 'NotFoundError') {
                setWebcamError('No camera found. Please connect a camera and try again.');
            } else {
                setWebcamError('Failed to access webcam: ' + err.message);
            }
        }
    };

    const stopWebcam = () => {
        // Kill the stop flag first so any in-flight interval tick bails out immediately
        isProcessingRef.current = false;

        // Abort any in-flight upload request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        uploadInFlightRef.current = false;

        if (uploadIntervalRef.current) {
            clearInterval(uploadIntervalRef.current);
            uploadIntervalRef.current = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) videoRef.current.srcObject = null;
        setIsWebcamActive(false);
    };

    const captureAndUploadFrame = async () => {
        if (!sessionId || !isProcessingRef.current) return;
        if (uploadInFlightRef.current) return;  // previous upload still pending, skip this tick
        if (!videoRef.current || !canvasRef.current) return;
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (video.videoWidth === 0 || video.videoHeight === 0) return;
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const frameData = canvas.toDataURL('image/jpeg', 0.8);

        uploadInFlightRef.current = true;
        abortControllerRef.current = new AbortController();
        try {
            await recognitionService.uploadFrame(sessionId, frameData, abortControllerRef.current.signal);
        } catch (err) {
            if (err.name !== 'CanceledError' && err.code !== 'ERR_CANCELED') {
                console.error('[uploadFrame] Error:', err.message);
            }
        } finally {
            uploadInFlightRef.current = false;
            abortControllerRef.current = null;
        }
    };

    const startRecognition = async () => {
        if (!sessionId) { setError('Session ID is missing.'); return; }
        try {
            setError(null);
            await startWebcam();
            // startWebcam sets webcamError and returns early if mediaDevices unavailable
            if (!streamRef.current) return;
            await recognitionService.startSession(sessionId);
            setIsProcessing(true);
            isProcessingRef.current = true;

            let retries = 0;
            while (retries < 10) {
                const statusRes = await recognitionService.getSession(sessionId);
                if (statusRes.data.session.status === 'in_progress') break;
                await new Promise(r => setTimeout(r, 200));
                retries++;
            }
            if (retries >= 10) throw new Error('Session did not start within expected time');

            uploadIntervalRef.current = setInterval(captureAndUploadFrame, 500);
            await fetchData();
        } catch (err) {
            setError('Failed to start recognition: ' + err.message);
            setIsProcessing(false);
            isProcessingRef.current = false;
        }
    };

    const stopRecognition = async () => {
        try {
            await recognitionService.stopSession(sessionId);
            stopWebcam();
            setIsProcessing(false);
            isProcessingRef.current = false;
            await fetchData();
        } catch (err) {
            setError('Failed to stop recognition: ' + err.message);
        }
    };

    useEffect(() => () => stopWebcam(), []);

    if (loading) return (
        <div className="session-detail">
            <div className="session-detail-container">
                <div className="loading-state"><span className="spinner"></span><p>Loading session...</p></div>
            </div>
        </div>
    );

    if (error) return (
        <div className="session-detail">
            <div className="session-detail-container">
                <div className="error-alert">{error}</div>
            </div>
        </div>
    );

    if (!session) return (
        <div className="session-detail">
            <div className="session-detail-container">
                <div className="error-alert">Session not found</div>
            </div>
        </div>
    );

    const sessionData = session.session ?? session;

    return (
        <div className="session-detail">
            <div className="session-detail-container">

                {/* Header */}
                <div className="session-detail-header">
                    <h1 className="session-detail-title">{sessionData.name}</h1>
                    <div className="session-detail-info">
                        <div className="detail-info-item">
                            <div className="detail-info-label">Status</div>
                            <div className="detail-info-value">
                                <span className={`status-badge ${sessionData.status === 'in_progress' ? 'in_progress' : sessionData.status}`}>
                                    {sessionData.status === 'in_progress' ? 'Running' : sessionData.status}
                                </span>
                            </div>
                        </div>
                        {sessionData.session_type && (
                            <div className="detail-info-item">
                                <div className="detail-info-label">Type</div>
                                <div className="detail-info-value">{sessionData.session_type}</div>
                            </div>
                        )}
                        {sessionData.roster_name && (
                            <div className="detail-info-item">
                                <div className="detail-info-label">Roster</div>
                                <div className="detail-info-value">{sessionData.roster_name}</div>
                            </div>
                        )}
                        <div className="detail-info-item">
                            <div className="detail-info-label">Created</div>
                            <div className="detail-info-value">{new Date(sessionData.created_at).toLocaleDateString()}</div>
                        </div>
                    </div>
                </div>

                {/* Webcam */}
                <div className="webcam-section">
                    <h2><i className="bi bi-camera-video"></i> Live Camera Feed</h2>

                    {webcamError && <div className="error-alert">{webcamError}</div>}

                    <div className="webcam-container">
                        <video
                            ref={videoRef}
                            autoPlay playsInline muted
                            className={`webcam-video${isWebcamActive ? ' active' : ''}`}
                        />
                        {!isWebcamActive && (
                            <div className="webcam-placeholder">
                                <i className="bi bi-camera-video-off"></i>
                                <span>Camera inactive</span>
                            </div>
                        )}
                        <canvas ref={canvasRef} style={{ display: 'none' }} />
                    </div>

                    <div className="webcam-controls">
                        {!isProcessing ? (
                            <button
                                className="btn-start-recognition"
                                onClick={startRecognition}
                                disabled={sessionData.status === 'ended' || sessionData.status === 'completed'}
                            >
                                <i className="bi bi-play-circle"></i> Start Recognition
                            </button>
                        ) : (
                            <button className="btn-stop-recognition" onClick={stopRecognition}>
                                <i className="bi bi-stop-circle"></i> Stop Recognition
                            </button>
                        )}
                        {isProcessing && (
                            <span className="processing-indicator">
                                <span className="spinner"></span> Processing...
                            </span>
                        )}
                    </div>
                </div>

                {/* Progress */}
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
                            <div className="progress-fill" style={{ width: `${progress.attendance_percentage}%` }} />
                        </div>
                    </div>
                )}

                {/* Unidentified faces */}
                {unidentifiedFaces.length > 0 && (
                    <div className="unidentified-section">
                        <h2><i className="bi bi-question-circle"></i> Unidentified Faces ({unidentifiedFaces.length})</h2>
                        <div className="unidentified-grid">
                            {unidentifiedFaces.map((face, i) => (
                                <div key={face.id ?? i} className="unidentified-item">
                                    {face.cropped_face && (
                                        <img src={face.cropped_face} alt="Unidentified face" />
                                    )}
                                    <small>{face.timestamp ? new Date(face.timestamp).toLocaleTimeString() : '—'}</small>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Present / Absent */}
                <div className="people-section">
                    <div className="people-list">
                        <h3><i className="bi bi-check-circle"></i> Present ({presentPeople.length})</h3>
                        {presentPeople.length > 0 ? (
                            <ul>
                                {presentPeople.map(person => (
                                    <li key={person.id}>
                                        <i className="bi bi-person-check"></i>
                                        {person.name || person.full_name}
                                        <span className="person-id-tag">{person.identification_number || 'N/A'}</span>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="empty-list-msg">No people present yet</p>
                        )}
                    </div>

                    <div className="people-list">
                        <h3><i className="bi bi-x-circle"></i> Absent ({absentPeople.length})</h3>
                        {absentPeople.length > 0 ? (
                            <ul>
                                {absentPeople.map(person => (
                                    <li key={person.id}>
                                        <i className="bi bi-person-x"></i>
                                        {person.name || person.full_name}
                                        <span className="person-id-tag">{person.identification_number || 'N/A'}</span>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="empty-list-msg">No absent people</p>
                        )}
                    </div>
                </div>

                {/* Events */}
                {events.length > 0 && (
                    <div className="events-section">
                        <h2><i className="bi bi-clock-history"></i> Recent Events ({events.length})</h2>
                        <div className="events-list">
                            {events.map((event, i) => (
                                <div key={event.id ?? i} className={`event ${event.severity || 'info'}`}>
                                    <span className="type">[{event.event_type}]</span>
                                    <span className="message">{event.message}</span>
                                    <span className="time">{new Date(event.timestamp).toLocaleTimeString()}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Controls */}
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
