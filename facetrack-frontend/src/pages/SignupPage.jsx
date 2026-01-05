import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const Signup = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    full_name: '',
    is_student: false,
    is_teacher: false,
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
      await signup(formData);
      navigate('/');
    } catch (err) {
      setErrors(err.response?.data || { general: 'Signup failed. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  const generalError = errors.general || errors.non_field_errors;

  return (
    <div className="auth-page">
      <div className="container-lg">
        <div className="auth-container">
          <div className="auth-card">
            <div className="auth-header">
              <div className="auth-icon">
                <i className="bi bi-person-plus"></i>
              </div>
              <h2 className="auth-title">Create Account</h2>
              <p className="auth-subtitle">Join our facial recognition system</p>
            </div>

            {generalError && (
              <div className="alert-custom alert-danger">
                <i className="bi bi-exclamation-circle"></i>
                <span>{Array.isArray(generalError) ? generalError[0] : generalError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="username">Username</label>
                <div className="input-wrapper">
                  <i className="bi bi-person"></i>
                  <input
                    type="text"
                    id="username"
                    name="username"
                    placeholder="Choose a username"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
                </div>
                {errors.username && <span className="error-text">{errors.username}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="email">Email</label>
                <div className="input-wrapper">
                  <i className="bi bi-envelope"></i>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    placeholder="Enter your email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </div>
                {errors.email && <span className="error-text">{errors.email}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="full_name">Full Name</label>
                <div className="input-wrapper">
                  <i className="bi bi-card-text"></i>
                  <input
                    type="text"
                    id="full_name"
                    name="full_name"
                    placeholder="Enter your full name"
                    value={formData.full_name}
                    onChange={handleChange}
                  />
                </div>
                {errors.full_name && <span className="error-text">{errors.full_name}</span>}
              </div>

              <div className="form-group role-selector">
                <label>Select Your Role</label>
                <div className="role-options">
                  <div className="role-check">
                    <input
                      type="checkbox"
                      id="is_student"
                      name="is_student"
                      checked={formData.is_student}
                      onChange={handleChange}
                    />
                    <label htmlFor="is_student">
                      <i className="bi bi-book"></i>
                      <span>I am a Student</span>
                    </label>
                  </div>
                  <div className="role-check">
                    <input
                      type="checkbox"
                      id="is_teacher"
                      name="is_teacher"
                      checked={formData.is_teacher}
                      onChange={handleChange}
                    />
                    <label htmlFor="is_teacher">
                      <i className="bi bi-mortarboard"></i>
                      <span>I am a Teacher</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="password">Password</label>
                <div className="input-wrapper">
                  <i className="bi bi-key"></i>
                  <input
                    type="password"
                    id="password"
                    name="password"
                    placeholder="Create a strong password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                  />
                </div>
                {errors.password && <span className="error-text">{errors.password}</span>}
              </div>

              <div className="form-group">
                <label htmlFor="password2">Confirm Password</label>
                <div className="input-wrapper">
                  <i className="bi bi-key"></i>
                  <input
                    type="password"
                    id="password2"
                    name="password2"
                    placeholder="Confirm your password"
                    value={formData.password2}
                    onChange={handleChange}
                    required
                  />
                </div>
                {errors.password2 && <span className="error-text">{errors.password2}</span>}
              </div>

              <button
                type="submit"
                className="btn-submit"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    Creating Account...
                  </>
                ) : (
                  'Create Account'
                )}
              </button>
            </form>

            <div className="auth-footer">
              <p>Already have an account? <a href="/login">Sign in</a></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
