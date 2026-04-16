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
          <i className="bi bi-camera-video"></i> ReconRoll
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
