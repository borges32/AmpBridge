import apiClient from './api';
import { LoginRequest, LoginResponse, User } from '@/types';

// ============================================================================
// Authentication Service
// ============================================================================
class AuthService {
  /**
   * Login user with username and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Backend expects JSON with login and password
    const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', {
      login: credentials.username,
      password: credentials.password,
    });

    // Store token in localStorage
    if (response.access_token) {
      localStorage.setItem('access_token', response.access_token);
    }

    return response;
  }

  /**
   * Logout user
   */
  logout(): void {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  }

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/api/v1/auth/me');
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token');
    return !!token;
  }

  /**
   * Get stored access token
   */
  getToken(): string | null {
    return localStorage.getItem('access_token');
  }
}

export const authService = new AuthService();
export default authService;
