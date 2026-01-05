import { useNavigate } from 'react-router-dom';
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

  return (
    <div className="profile-page">
      <div className="container-lg">
        <div className="profile-card">
          <div className="profile-header">
            <div className="profile-avatar">
              <i className="bi bi-person-circle"></i>
            </div>
            <h1 className="profile-name">{user.username}</h1>
            <div className="profile-roles">
              {user.is_student && <span className="role-badge student">Student</span>}
              {user.is_teacher && <span className="role-badge teacher">Teacher</span>}
              {!user.is_student && !user.is_teacher && <span className="role-badge neutral">User</span>}
            </div>
          </div>

          <div className="profile-info-grid">
            <div className="info-item">
              <label className="info-label">
                <i className="bi bi-person"></i>
                Username
              </label>
              <p className="info-value">{user.username}</p>
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
                <i className="bi bi-card-text"></i>
                Full Name
              </label>
              <p className="info-value">{user.full_name || 'Not provided'}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="btn-logout"
          >
            <i className="bi bi-box-arrow-right"></i>
            Logout
          </button>
        </div>
      </div>
    </div>
  );
};
