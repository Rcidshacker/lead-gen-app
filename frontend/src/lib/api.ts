import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Create Axios Instance ───
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Request Interceptor: Attach JWT ───
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ─── Response Interceptor: Handle Errors ───
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (typeof window === 'undefined') {
      return Promise.reject(error);
    }

    const status = error.response?.status;

    if (status === 401) {
      // Token expired or invalid — redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // Avoid redirect loop if already on login
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    if (status === 403) {
      console.error('Access forbidden. You do not have permission for this action.');
    }

    if (status && status >= 500) {
      console.error('Server error. Please try again later.');
    }

    return Promise.reject(error);
  }
);

// ─── Typed API Methods ───
export const apiClient = {
  get: <T>(url: string, params?: Record<string, unknown>) =>
    api.get<T>(url, { params }).then((r) => r.data),

  post: <T>(url: string, data?: unknown) =>
    api.post<T>(url, data).then((r) => r.data),

  put: <T>(url: string, data?: unknown) =>
    api.put<T>(url, data).then((r) => r.data),

  patch: <T>(url: string, data?: unknown) =>
    api.patch<T>(url, data).then((r) => r.data),

  delete: <T>(url: string) =>
    api.delete<T>(url).then((r) => r.data),
};

export default api;
