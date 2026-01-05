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
    return <div className="container mt-5 text-center"><p>Loading...</p></div>;
  }

  if (!user) {
    return <div className="container mt-5"><p>No user data available</p></div>;
  }

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h3 className="card-title mb-4">User Profile</h3>

              <div className="profile-info mb-4">
                <div className="mb-3">
                  <label className="fw-bold">Username:</label>
                  <p>{user.username}</p>
                </div>

                <div className="mb-3">
                  <label className="fw-bold">Email:</label>
                  <p>{user.email}</p>
                </div>

                <div className="mb-3">
                  <label className="fw-bold">Full Name:</label>
                  <p>{user.full_name || 'Not provided'}</p>
                </div>

                <div className="mb-3">
                  <label className="fw-bold">Role:</label>
                  <p>
                    {user.is_student && <span className="badge bg-info me-2">Student</span>}
                    {user.is_teacher && <span className="badge bg-success me-2">Teacher</span>}
                    {!user.is_student && !user.is_teacher && <span>None</span>}
                  </p>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="btn btn-danger w-100"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
