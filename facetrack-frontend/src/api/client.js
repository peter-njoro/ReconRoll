import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});

// Helper to read a cookie by name
function getCookie(name) {
    const matches = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return matches ? decodeURIComponent(matches[2]) : null;
}

// Set default X-CSRFToken header if cookie exists and ensure it's added to each request
const initialCsrf = getCookie('csrftoken');
if (initialCsrf) {
    apiClient.defaults.headers['X-CSRFToken'] = initialCsrf;
}

apiClient.interceptors.request.use((config) => {
    const token = getCookie('csrftoken');
    if (token) {
        config.headers = config.headers || {};
        if (!config.headers['X-CSRFToken']) {
            config.headers['X-CSRFToken'] = token;
        }
    }
    return config;
});

export default apiClient;