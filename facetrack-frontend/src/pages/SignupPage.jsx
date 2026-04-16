import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Signup = () => {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    password2: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setLoading(true);

    // Validate passwords match
    if (formData.password !== formData.password2) {
      setErrors({ password2: 'Passwords do not match.' });
      setLoading(false);
      return;
    }

    try {
      const payload = {
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        password: formData.password,
        password2: formData.password2,
      };
      await signup(payload);
      navigate('/profile/username');
    } catch (err) {
      setErrors(err.response?.data || { general: 'Signup failed. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const generalError = errors.general || errors.non_field_errors?.[0];
  const renderError = (value) => (Array.isArray(value) ? value[0] : value);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <p className="auth-eyebrow">Create account</p>
          <h1 className="auth-title">Get started</h1>
          <p className="auth-subtitle">Just the basics to set up your access.</p>
        </div>

        {generalError && (
          <div className="alert error">{generalError}</div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="field-row">
            <label className="field">
              <span>First name</span>
              <input
                type="text"
                id="first_name"
                name="first_name"
                placeholder="Ada"
                value={formData.first_name}
                onChange={handleChange}
                autoComplete="given-name"
                required
              />
              {errors.first_name && <span className="error-text">{renderError(errors.first_name)}</span>}
            </label>

            <label className="field">
              <span>Last name</span>
              <input
                type="text"
                id="last_name"
                name="last_name"
                placeholder="Lovelace"
                value={formData.last_name}
                onChange={handleChange}
                autoComplete="family-name"
                required
              />
              {errors.last_name && <span className="error-text">{renderError(errors.last_name)}</span>}
            </label>
          </div>

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              id="email"
              name="email"
              placeholder="name@company.com"
              value={formData.email}
              onChange={handleChange}
              autoComplete="email"
              required
            />
            {errors.email && <span className="error-text">{renderError(errors.email)}</span>}
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              id="password"
              name="password"
              placeholder="Create a secure password"
              value={formData.password}
              onChange={handleChange}
              autoComplete="new-password"
              required
            />
            {errors.password && <span className="error-text">{renderError(errors.password)}</span>}
          </label>

          <label className="field">
            <span>Confirm password</span>
            <input
              type="password"
              id="password2"
              name="password2"
              placeholder="Repeat your password"
              value={formData.password2}
              onChange={handleChange}
              autoComplete="new-password"
              required
            />
            {errors.password2 && <span className="error-text">{renderError(errors.password2)}</span>}
          </label>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <div className="auth-footer">
          <span>Already have an account?</span>
          <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
};
