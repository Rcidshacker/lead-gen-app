import { apiClient } from './api';

// ─── Types ───
interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
    full_name: string;
  };
}

interface RegisterResponse {
  id: string;
  email: string;
  full_name: string;
}

// ─── Helpers ───
function isTokenExpired(token: string): boolean {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const { exp } = JSON.parse(jsonPayload);
    // Expire 30 seconds early to avoid edge cases
    return Date.now() >= (exp - 30) * 1000;
  } catch {
    return true; // If we can't decode it, consider it expired
  }
}

// ─── Auth Functions ───
export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiClient.post<LoginResponse>('/api/v1/auth/login', {
    email,
    password,
  });

  // Store tokens
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', data.access_token);
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token);
    }
  }

  return data;
}

export async function register(
  email: string,
  password: string,
  fullName: string
): Promise<RegisterResponse> {
  const data = await apiClient.post<RegisterResponse>('/api/v1/auth/register', {
    email,
    password,
    full_name: fullName,
  });

  return data;
}

export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;
  return !isTokenExpired(token);
}
