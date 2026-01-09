import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { recognitionService } from '../api/recognitionService';

export function HomePage() {
    const [info, setInfo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { isAuthenticated } = useAuth();

    const routeMap = {
        enroll: '/enroll',
        sessions: '/sessions',
    };

    useEffect(() => {
        const fetchInfo = async () => {
            try {
                const response = await recognitionService.getInfo();
                setInfo(response.data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchInfo();
    }, []);

    return (
        <div className="modern-home-page">
            {/* Hero Section (backend-driven content) */}
            <section className="hero-section">
                <div className="container-lg">
                    <div className="hero-grid">
                        <div className="hero-content">
                            { /* Use backend-provided hero content when available */ }
                            {(() => {
                                const hero = info?.hero || {};
                                const title = hero.title || hero.message || 'Identification system for safety and security';
                                const subtitle = hero.subtitle || 'Apply facial recognition for a range of scenarios';
                                return (
                                    <>
                                        <h1 className="hero-title">{title}</h1>
                                        <p className="hero-subtitle">{subtitle}</p>
                                    </>
                                );
                            })()}

                            <div className="hero-cta">
                                {isAuthenticated ? (
                                    <>
                                        <Link to="/enroll" className="btn-primary-gradient">
                                            Get Started
                                        </Link>
                                        <Link to="/sessions" className="btn-secondary-outline">
                                            View Sessions
                                        </Link>
                                    </>
                                ) : (
                                    <>
                                        <Link to="/signup" className="btn-primary-gradient">
                                            Explore the solution
                                        </Link>
                                        <Link to="/login" className="btn-secondary-outline">
                                            Sign In
                                        </Link>
                                    </>
                                )}
                            </div>
                        </div>
                        <div className="hero-visual">
                            <div className="face-illustration">
                                <div className="face-dots"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="features-section">
                <div className="container-lg">
                    <div className="features-grid">
                        <div className="feature-card">
                            <div className="feature-icon">
                                <i className="bi bi-camera-video"></i>
                            </div>
                            <h3 className="feature-title">Advanced Facial Recognition</h3>
                            <p className="feature-text">
                                Our facial recognition software is able to recognize faces of humans in your database and recognize faces regardless of their color, accessories, or background.
                            </p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">
                                <i className="bi bi-shield-check"></i>
                            </div>
                            <h3 className="feature-title">Secure & Reliable</h3>
                            <p className="feature-text">
                                Built with enterprise-grade security standards to ensure your data and recognition results are protected at all times.
                            </p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">
                                <i className="bi bi-lightning-fill"></i>
                            </div>
                            <h3 className="feature-title">Real-Time Processing</h3>
                            <p className="feature-text">
                                Instant recognition and verification with minimal latency, perfect for high-security applications and attendance systems.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Endpoints Section */}
            {!loading && info && (
                <section className="endpoints-section">
                    <div className="container-lg">
                        <h2 className="section-title">Quick Access</h2>
                        <div className="endpoints-grid">
                            {Object.entries(info.endpoints).map(([key]) => (
                                <Link 
                                    key={key}
                                    to={routeMap[key]} 
                                    className="endpoint-card"
                                >
                                    <div className="endpoint-icon">
                                        <i className={`bi bi-${key === 'enroll' ? 'person-plus' : 'clock-history'}`}></i>
                                    </div>
                                    <h3 className="endpoint-title">
                                        {key === 'enroll' ? 'Enroll' : 'Sessions'}
                                    </h3>
                                    <p className="endpoint-desc">
                                        {key === 'enroll' 
                                            ? 'Register new faces in the system' 
                                            : 'View your recognition sessions'}
                                    </p>
                                </Link>
                            ))}
                        </div>
                    </div>
                </section>
            )}

            {/* CTA Section */}
            <section className="cta-section">
                <div className="container-lg">
                    <div className="cta-content">
                        <h2>Ready to enhance your security?</h2>
                        <p>Join thousands of organizations using facial recognition technology</p>
                        {!isAuthenticated && (
                            <Link to="/signup" className="btn-primary-gradient">
                                Get Started Now
                            </Link>
                        )}
                    </div>
                </div>
            </section>
        </div>
    );
}