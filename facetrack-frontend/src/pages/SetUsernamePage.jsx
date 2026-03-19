import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const SetUsernamePage = () => {
  const { user, setUsername } = useAuth();
  const [username, setUsernameValue] = useState(user?.username || '');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setUsernameValue(user?.username || '');
  }, [user]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = username.trim();
    setError('');
    setLoading(true);

    if (!trimmed) {
      setError('Username is required.');
      setLoading(false);
      return;
    }

    try {
      await setUsername(trimmed);
      navigate('/profile');
    } catch (err) {
      const apiError = err.response?.data;
      const message = apiError?.username || apiError?.detail || 'Unable to update username.';
      setError(Array.isArray(message) ? message[0] : message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <p className="auth-eyebrow">Account settings</p>
          <h1 className="auth-title">Set a username</h1>
          <p className="auth-subtitle">Choose a short, memorable handle for your profile.</p>
        </div>

        {error && <div className="alert error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span>Username</span>
            <input
              type="text"
              id="username"
              name="username"
              placeholder="your-handle"
              value={username}
              onChange={(event) => setUsernameValue(event.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving...' : 'Save username'}
          </button>
        </form>

        <div className="auth-footer">
          <span>Changed your mind?</span>
          <Link to="/profile">Back to profile</Link>
        </div>
      </div>
    </div>
  );
};
