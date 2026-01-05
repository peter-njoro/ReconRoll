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
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h3 className="card-title text-center mb-4">Create Account</h3>

              {generalError && (
                <div className="alert alert-danger" role="alert">
                  {Array.isArray(generalError) ? generalError[0] : generalError}
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label htmlFor="username" className="form-label">Username</label>
                  <input
                    type="text"
                    className={`form-control ${errors.username ? 'is-invalid' : ''}`}
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    required
                  />
                  {errors.username && <div className="invalid-feedback">{errors.username}</div>}
                </div>

                <div className="mb-3">
                  <label htmlFor="email" className="form-label">Email</label>
                  <input
                    type="email"
                    className={`form-control ${errors.email ? 'is-invalid' : ''}`}
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                  {errors.email && <div className="invalid-feedback">{errors.email}</div>}
                </div>

                <div className="mb-3">
                  <label htmlFor="full_name" className="form-label">Full Name</label>
                  <input
                    type="text"
                    className={`form-control ${errors.full_name ? 'is-invalid' : ''}`}
                    id="full_name"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleChange}
                  />
                  {errors.full_name && <div className="invalid-feedback">{errors.full_name}</div>}
                </div>

                <div className="mb-3">
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="is_student"
                      name="is_student"
                      checked={formData.is_student}
                      onChange={handleChange}
                    />
                    <label className="form-check-label" htmlFor="is_student">
                      I am a Student
                    </label>
                  </div>
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="is_teacher"
                      name="is_teacher"
                      checked={formData.is_teacher}
                      onChange={handleChange}
                    />
                    <label className="form-check-label" htmlFor="is_teacher">
                      I am a Teacher
                    </label>
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="password" className="form-label">Password</label>
                  <input
                    type="password"
                    className={`form-control ${errors.password ? 'is-invalid' : ''}`}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    required
                  />
                  {errors.password && <div className="invalid-feedback">{errors.password}</div>}
                </div>

                <div className="mb-3">
                  <label htmlFor="password2" className="form-label">Confirm Password</label>
                  <input
                    type="password"
                    className={`form-control ${errors.password2 ? 'is-invalid' : ''}`}
                    id="password2"
                    name="password2"
                    value={formData.password2}
                    onChange={handleChange}
                    required
                  />
                  {errors.password2 && <div className="invalid-feedback">{errors.password2}</div>}
                </div>

                <button
                  type="submit"
                  className="btn btn-primary w-100"
                  disabled={loading}
                >
                  {loading ? 'Creating Account...' : 'Sign Up'}
                </button>
              </form>

              <div className="mt-3 text-center">
                <p>Already have an account? <a href="/login">Sign in</a></p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
