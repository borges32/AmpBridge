import api from './api';
import type { UserDetail, UserListResponse, CreateUserRequest, UpdateUserRequest } from '@/types';

// ============================================================================
// User Service
// ============================================================================

/**
 * List all users with pagination
 */
export const listUsers = async (page: number = 1, pageSize: number = 50): Promise<UserListResponse> => {
  return await api.get<UserListResponse>('/api/v1/users', {
    params: {
      page,
      page_size: pageSize,
    },
  });
};

/**
 * Get user by ID
 */
export const getUser = async (userId: number): Promise<UserDetail> => {
  return await api.get<UserDetail>(`/api/v1/users/${userId}`);
};

/**
 * Create new user
 */
export const createUser = async (userData: CreateUserRequest): Promise<UserDetail> => {
  return await api.post<UserDetail>('/api/v1/users', userData);
};

/**
 * Update user
 */
export const updateUser = async (userId: number, userData: UpdateUserRequest): Promise<UserDetail> => {
  return await api.put<UserDetail>(`/api/v1/users/${userId}`, userData);
};

/**
 * Delete user
 */
export const deleteUser = async (userId: number): Promise<void> => {
  await api.delete(`/api/v1/users/${userId}`);
};
