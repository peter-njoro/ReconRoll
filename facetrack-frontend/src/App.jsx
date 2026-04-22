import './App.css';
import { useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { SessionsPage } from './pages/SessionsPage';
import { SessionDetailPage } from './pages/SessionDetailPage';
import { CreateSessionPage } from './pages/CreateSessionPage';
import { RosterSelectPage } from './pages/RosterSelectPage';
import { RostersPage } from './pages/RostersPage';
import { EnrollmentForm } from './components/EnrollmentForm';
import { Login } from './pages/LoginPage';
import { Signup } from './pages/SignupPage';
import { ProfilePage } from './pages/ProfilePage';
import { SetUsernamePage } from './pages/SetUsernamePage';

const Navbar = () => {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const displayName = user?.username
    || user?.full_name
    || [user?.first_name, user?.last_name].filter(Boolean).join(' ')
    || user?.email;

  const handleLogout = async () => {
    await logout();
    window.location.href = '/';
  };

  const close = () => setMenuOpen(false);

  return (
    <nav className="navbar">
      <div className="navbar-inner container">
        <Link className="navbar-brand" to="/" onClick={close}>
          <svg
            width="28"
            height="28"
            viewBox="560 160 240 420"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
            style={{ display: 'inline-block', verticalAlign: 'middle', marginRight: '6px' }}
          >
            <g transform="translate(680, 400)">
              <path d="M 20,-230 C 70,-236 130,-210 150,-156 C 164,-116 156,-70 152,-30 C 164,-16 172,8 164,32 C 158,52 140,56 132,44 C 120,84 96,120 64,148 C 36,172 0,184 -24,180 C -56,176 -76,152 -72,124 C -68,100 -48,88 -28,92 C -12,96 0,108 0,124 C 8,108 12,84 8,60 C 4,32 -8,8 -16,-20 C -24,-56 -24,-104 -16,-144 C -8,-184 4,-212 20,-230 Z" fill="currentColor" />
              <path d="M 20,-230 C 30,-276 64,-310 110,-316 C 156,-322 200,-290 210,-244 C 220,-200 200,-150 180,-120 C 188,-156 192,-204 176,-236 C 160,-268 124,-284 92,-276 C 60,-268 36,-240 24,-208 C 20,-232 18,-230 20,-230 Z" fill="currentColor" opacity="0.7" />
              <path d="M -68,104 C -92,100 -104,116 -100,136 C -96,156 -76,160 -68,148 Z" fill="currentColor" />
            </g>
          </svg>
          ReconRoll
        </Link>

        <button
          className={`navbar-hamburger${menuOpen ? ' open' : ''}`}
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Toggle menu"
        >
          <span /><span /><span />
        </button>

        <ul className={`nav${menuOpen ? ' nav-open' : ''}`} onClick={close}>
          <li><Link className="nav-link" to="/">Home</Link></li>
          <li><Link className="nav-link" to="/enroll">Enroll</Link></li>
          <li><Link className="nav-link" to="/rosters">Rosters</Link></li>
          <li><Link className="nav-link" to="/sessions">Sessions</Link></li>
          {user ? (
            <>
              <li><Link className="nav-link" to="/profile">Hello, {displayName}</Link></li>
              <li>
                <button className="nav-link nav-link-btn" onClick={handleLogout}>
                  Logout
                </button>
              </li>
            </>
          ) : (
            <>
              <li><Link className="nav-link" to="/signup">Sign up</Link></li>
              <li><Link className="nav-link" to="/login">Sign in</Link></li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
};

const AppContent = () => {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile/username"
          element={
            <ProtectedRoute>
              <SetUsernamePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/enroll"
          element={
            <ProtectedRoute>
              <EnrollmentForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/rosters"
          element={
            <ProtectedRoute>
              <RostersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/sessions"
          element={
            <ProtectedRoute>
              <SessionsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/session/create"
          element={
            <ProtectedRoute>
              <CreateSessionPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/session/:sessionId/roster"
          element={
            <ProtectedRoute>
              <RosterSelectPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/session/:sessionId"
          element={
            <ProtectedRoute>
              <SessionDetailPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
