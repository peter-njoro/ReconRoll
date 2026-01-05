import apiClient from './client';

export const authService = {
  signup: async (userData) => {
    const response = await apiClient.post('/users/signup/', userData);
    return response.data;
  },

  login: async (credentials) => {
    const response = await apiClient.post('/users/login/', credentials);
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/users/logout/');
    return response.data;
  },

  getProfile: async () => {
    const response = await apiClient.get('/users/me/');
    return response.data;
  },
};
