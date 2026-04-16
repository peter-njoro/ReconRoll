import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL;

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
});

apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('authToken');
        console.log(`[DRF] ${config.method.toUpperCase()} ${config.url}`);
        if (token) {
            config.headers = config.headers || {};
            config.headers['Authorization'] = `Token ${token}`;
        }
        return config;
    },
    (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
    }
);

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            console.error('API Response Error:', error.response.status, error.response.data);
            if (error.response.status === 401) console.error('Unauthorized access - please log in');
            else if (error.response.status === 403) console.error('Access forbidden');
            else if (error.response.status === 404) console.error('Resource not found');
            else if (error.response.status === 429) console.error('Too many requests - rate limited');
        } else if (error.request) {
            console.error('No response from server:', error.request);
        } else {
            console.error('Request setup error:', error.message);
        }
        return Promise.reject(error);
    }
);

export default apiClient;
