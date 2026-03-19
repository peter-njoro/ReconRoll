import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { recognitionService } from '../api/recognitionService';
import './HomePage.css';

export function HomePage() {
    const [info, setInfo] = useState(null);
    const { isAuthenticated } = useAuth();

    useEffect(() => {
        recognitionService.getInfo()
            .then(res => setInfo(res.data))
            .catch(() => {});
    }, []);

    const features = info?.features ?? [];

    return (
        <div className="home">
            <section className="home-hero">
                <div className="home-hero-content">
                    <span className="home-badge">v{info?.version ?? '—'}</span>
                    <h1 className="home-title">{info?.title ?? 'FaceTrack'}</h1>
                    <p className="home-tagline">{info?.tagline ?? ''}</p>
                    <p className="home-desc">{info?.description ?? ''}</p>
                    <div className="home-actions">
                        {isAuthenticated ? (
                            <>
                                <Link to="/enroll" className="btn-primary">Enroll Person</Link>
                                <Link to="/sessions" className="btn-ghost">View Sessions</Link>
                            </>
                        ) : (
                            <>
                                <Link to="/signup" className="btn-primary">Get Started</Link>
                                <Link to="/login" className="btn-ghost">Sign In</Link>
                            </>
                        )}
                    </div>
                </div>

                <div className="hero-visual">
                    <div className="face-illustration">
                        <div className="face-dots"></div>
                    </div>
                </div>
            </section>

            {features.length > 0 && (
                <section className="home-features">
                    {features.map((f, i) => (
                        <div key={i} className="home-feature-card">
                            <i className={`bi bi-${f.icon} home-feature-icon`}></i>
                            <h3>{f.title}</h3>
                            <p>{f.description}</p>
                        </div>
                    ))}
                </section>
            )}
        </div>
    );
}
