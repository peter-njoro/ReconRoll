import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { recognitionService } from '../api/recognitionService';
import './HomePage.css';

const GITHUB_URL = 'https://github.com/peter-njoro/ReconRoll';

const RELEASES = [
    { version: 'v2.0.0', codename: 'Mizunoe', status: 'released', summary: 'Complete rewrite. REST API, React frontend, PostgreSQL, Docker, background recognition thread.' },
    { version: 'v1.0.0', codename: 'Mizunoto', status: 'released', summary: 'Initial release. Local Django app with server-rendered templates and SQLite.' },
    { version: 'v3.0.0', codename: 'Toshi',    status: 'planned',  summary: 'Drop the GUI. CLI access. Replace dlib with InsightFace (ArcFace). Decouple the pipeline from Django.' },
    { version: 'v4.0.0', codename: 'Ushi',     status: 'planned',  summary: 'ONNX Runtime inference. Async frame pipeline. Installable Python SDK.' },
    { version: 'v5.0.0', codename: 'Tora',     status: 'planned',  summary: 'Multi-frame confirmation. Confidence rejection zones. Quality gating. Accuracy benchmarks.' },
];

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
                    <h1 className="home-title">{info?.title ?? 'ReconRoll'}</h1>
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

            <section className="home-releases">
                <div className="home-releases-header">
                    <div>
                        <h2 className="home-releases-title">Releases</h2>
                        <p className="home-releases-sub">Versioned by the Demon Slayer Corps ranking system — Mizunoto to Hashira.</p>
                    </div>
                    <div className="home-releases-links">
                        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="btn-ghost home-gh-btn">
                            <i className="bi bi-github"></i> View on GitHub
                        </a>
                        <a href={`${GITHUB_URL}/issues`} target="_blank" rel="noopener noreferrer" className="btn-ghost home-gh-btn">
                            <i className="bi bi-bug"></i> Report Issue
                        </a>
                    </div>
                </div>
                <div className="home-releases-list">
                    {RELEASES.map(r => (
                        <div key={r.version} className={`home-release-item home-release-${r.status}`}>
                            <div className="home-release-meta">
                                <span className="home-release-version">{r.version}</span>
                                <span className="home-release-codename">{r.codename}</span>
                                <span className={`home-release-badge home-release-badge-${r.status}`}>
                                    {r.status === 'released' ? 'Released' : 'Planned'}
                                </span>
                            </div>
                            <p className="home-release-summary">{r.summary}</p>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
