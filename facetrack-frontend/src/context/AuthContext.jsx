import { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../api/authService';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // On mount, restore session from stored token
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('authToken');
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const userData = await authService.getProfile();
        setUser(userData);
      } catch {
        // Token invalid or expired — clear it
        localStorage.removeItem('authToken');
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const data = await authService.login({ email, password });
      localStorage.setItem('authToken', data.token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const signup = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const data = await authService.signup(userData);
      localStorage.setItem('authToken', data.token);
      setUser(data.user);
      return data;
    } catch (err) {
      setError(err.response?.data || 'Signup failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    setError(null);
    try {
      await authService.logout();
    } catch {
      // logout endpoint may 401 if token already gone — that's fine
    } finally {
      localStorage.removeItem('authToken');
      setUser(null);
      setLoading(false);
    }
  };

  const setUsername = async (username) => {
    setLoading(true);
    setError(null);
    try {
      const data = await authService.setUsername({ username });
      setUser(data.user || data);
      return data;
    } catch (err) {
      setError(err.response?.data || 'Update failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{
      user, loading, error,
      login, signup, logout, setUsername,
      isAuthenticated: !!user
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
