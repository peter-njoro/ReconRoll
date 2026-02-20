import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
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
  const displayName = user?.username || user?.full_name || [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.email;
  
  const handleLogout = async () => {
    await logout();
    window.location.href = '/';
  };

  return (
    <nav className="navbar navbar-expand-lg fixed-top shadow-sm bg-white">
      <div className="container">
        <a className="navbar-brand fw-bold" href="/">
          <i className="bi bi-camera-video"></i> FaceTrack Lite
        </a>
        <ul className="nav nav-pills ms-auto">
          <li className="nav-item"><a className="nav-link" href="/">Home</a></li>
          <li className="nav-item"><a className="nav-link" href="/enroll">Enroll</a></li>
          <li className="nav-item"><a className="nav-link" href="/rosters">Rosters</a></li>
          <li className="nav-item"><a className="nav-link" href="/sessions">Session History</a></li>
          {user ? (
            <>
              <li className="nav-item">
                <span className="navbar-text">
                  <a className="nav-link" href="/profile">Hello, {displayName}.</a>
                </span>
              </li>
              <li className="nav-item">
                <button className="nav-link btn btn-link" onClick={handleLogout}>
                  Logout
                </button>
              </li>
            </>
          ) : (
            <>
              <li className="nav-item"><a className="nav-link" href="/signup">Signup</a></li>
              <li className="nav-item"><a className="nav-link" href="/login">Signin</a></li>
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
