import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
// const DJANGO_BASE_URL = process.env.REACT_APP_DJANGO_URL || 'http://localhost:8000/recognition';
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});


// const django = axios.create({
//     baseURL: DJANGO_BASE_URL,
//     headers: { 'Content-Type': 'application/json' },
//     withCredentials: true,
// });

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

[apiClient].forEach((instance) => {
    apiClient.interceptors.request.use((config) => {
            const token = getCookie('csrftoken');
            console.log(`[${config.baseURL === API_BASE_URL ? 'DRF' : 'Django'}] ${config.method.toUpperCase()} ${config.url}`);
            if (token) {
                config.headers = config.headers || {};
                if (!config.headers['X-CSRFToken']) {
                    config.headers['X-CSRFToken'] = token;
                }
            }
            return config;
        },
        (error) => {
            console.error('API Request Error:', error);
            return Promise.reject(error);
        }
    );

// Add response interceptor for error handling
    apiClient.interceptors.response.use(
        (response) => response,
        (error) => {
            if (error.response) {
                // Server responded with error status
                console.error('API Response Error:', error.response.status, error.response.data);

                // Handle specific error codes
                if (error.response.status === 401) {
                    console.error('Unauthorized access - please log in');
                    // You can add redirect logic here if needed
                } else if (error.response.status === 403) {
                    console.error('Access forbidden');
                } else if (error.response.status === 404) {
                    console.error('Resource not found');
                } else if (error.response.status === 429) {
                    console.error('Too many requests - rate limited');
                }
            } else if (error.request) {
                // Request made but no response received
                console.error('No response from server:', error.request);
            } else {
                // Error in setting up the request
                console.error('Request setup error:', error.message);
            }

            return Promise.reject(error);
        }
    );
});

export default apiClient;