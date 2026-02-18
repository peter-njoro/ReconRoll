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

  const fullName = user.full_name || [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Not provided';
  const username = user.username || 'Not set';

  return (
    <div className="profile-page">
      <div className="container-lg">
        <div className="profile-card">
          <div className="profile-header">
            <div className="profile-avatar">
              <i className="bi bi-person-circle"></i>
            </div>
            <h1 className="profile-name">{fullName}</h1>
            <div className="profile-roles">
              <span className={`role-badge ${user.is_verified ? 'verified' : 'unverified'}`}>
                {user.is_verified ? 'Verified' : 'Unverified'}
              </span>
            </div>
          </div>

          <div className="profile-info-grid">
            <div className="info-item">
              <label className="info-label">
                <i className="bi bi-person"></i>
                Name
              </label>
              <p className="info-value">{fullName}</p>
            </div>

            <div className="info-item">
              <label className="info-label">
                <i className="bi bi-at"></i>
                Username
              </label>
              <p className="info-value">{username}</p>
            </div>

            <div className="info-item">
              <label className="info-label">
                <i className="bi bi-envelope"></i>
                Email
              </label>
              <p className="info-value">{user.email}</p>
            </div>

            <div className="info-item">
              <label className="info-label">
                <i className="bi bi-shield-check"></i>
                Status
              </label>
              <p className="info-value">{user.is_active ? 'Active' : 'Inactive'}</p>
            </div>
          </div>

          <div className="profile-actions">
            <Link to="/profile/username" className="btn-secondary-outline">
              Set username
            </Link>
            <button onClick={handleLogout} className="btn-logout">
              <i className="bi bi-box-arrow-right"></i>
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
