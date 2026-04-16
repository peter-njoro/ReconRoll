import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProfilePage = () => {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  if (loading) {
    return (
      <div className="profile-page">
        <div className="container-lg">
          <div className="loading-state">
            <span className="spinner"></span>
            <p>Loading your profile...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="profile-page">
        <div className="container-lg">
          <div className="error-state">
            <i className="bi bi-exclamation-triangle"></i>
            <p>No user data available</p>
          </div>
        </div>
      </div>
    );
  }

  const fullName = user.full_name
    || [user.first_name, user.last_name].filter(Boolean).join(' ')
    || 'Not provided';
  const initials = [user.first_name?.[0], user.last_name?.[0]].filter(Boolean).join('').toUpperCase() || '?';
  const memberSince = user.created_at ? new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long' }) : '—';

  return (
    <div className="profile-page">
      <div className="container-lg">
        <div className="profile-layout">

          {/* Left — avatar + name */}
          <div className="profile-sidebar">
            <div className="profile-avatar-wrap">
              <div className="profile-initials">{initials}</div>
            </div>
            <h1 className="profile-name">{fullName}</h1>
            <p className="profile-handle">{user.username ? `@${user.username}` : user.email}</p>
            <div className="profile-badges">
              <span className={`role-badge ${user.is_verified ? 'verified' : ''}`}>
                <i className={`bi bi-${user.is_verified ? 'patch-check' : 'patch-question'}`}></i>
                {user.is_verified ? 'Verified' : 'Unverified'}
              </span>
              {user.is_staff && (
                <span className="role-badge staff">
                  <i className="bi bi-shield"></i> Staff
                </span>
              )}
              <span className={`role-badge ${user.is_active ? 'active' : 'inactive'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <p className="profile-since">Member since {memberSince}</p>
          </div>

          {/* Right — details */}
          <div className="profile-main">
            <div className="profile-section">
              <h2 className="profile-section-title">Account details</h2>
              <div className="profile-info-grid">
                <div className="info-item">
                  <span className="info-label"><i className="bi bi-person"></i> Full name</span>
                  <span className="info-value">{fullName}</span>
                </div>
                <div className="info-item">
                  <span className="info-label"><i className="bi bi-at"></i> Username</span>
                  <span className="info-value">{user.username || <em className="muted-em">Not set</em>}</span>
                </div>
                <div className="info-item">
                  <span className="info-label"><i className="bi bi-envelope"></i> Email</span>
                  <span className="info-value">{user.email}</span>
                </div>
                <div className="info-item">
                  <span className="info-label"><i className="bi bi-fingerprint"></i> User ID</span>
                  <span className="info-value info-mono">{String(user.id).slice(0, 8)}…</span>
                </div>
                {user.updated_at && (
                  <div className="info-item">
                    <span className="info-label"><i className="bi bi-clock-history"></i> Last updated</span>
                    <span className="info-value">{new Date(user.updated_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="profile-actions">
              <Link to="/profile/username" className="btn-secondary-outline">
                <i className="bi bi-pencil"></i> Set username
              </Link>
              <button onClick={handleLogout} className="btn-logout">
                <i className="bi bi-box-arrow-right"></i> Logout
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
