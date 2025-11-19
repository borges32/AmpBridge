// ============================================================================
// Auth Types
// ============================================================================
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  username: string;
  email?: string;
}

export interface UserDetail {
  id: number;
  name: string;
  email: string;
  login: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateUserRequest {
  name: string;
  email: string;
  login: string;
  password: string;
}

export interface UpdateUserRequest {
  name?: string;
  email?: string;
  is_active?: boolean;
}

export interface UserListResponse {
  users: UserDetail[];
  total: number;
  page: number;
  page_size: number;
}

// ============================================================================
// Agent Types
// ============================================================================
export interface Agent {
  id: number;
  instance_id: string;
  host_name: string;
  os_type: string;
  os_description: string;
  service_name?: string;
  service_version?: string;
  host_arch?: string;
  healthy: boolean;
  status_sync: string;
  alert_config: boolean;
  is_connected: boolean;
  started_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

export interface AgentHealth {
  id: number;
  instance_id: string;
  healthy: boolean;
  status: string;
  status_time_unix_nano?: number;
  last_error?: string | null;
  component_health_summary?: string | null;
  start_time_unix_nano?: string;
  up?: boolean;
  created_at: string;
}

export interface AgentPipelineHealth {
  id: number;
  instance_id: string;
  component_type: string;
  component_name: string;
  parent_pipeline: string | null;
  healthy: boolean;
  status: string;
  status_time_unix_nano?: number;
  last_error?: string | null;
  created_at: string;
}

export interface AgentConfig {
  id: number;
  agent_id: number;
  config_hash: string;
  config_yaml: string;
  version: number;
  created_at: string;
  source: string;
  created_by?: string;
}

export interface AgentDetail extends Agent {
  health?: AgentHealth;
  current_config?: AgentConfig;
  attributes?: Record<string, any>;
  agent_description?: {
    identifying_attributes?: Array<{ key: string; value: any }>;
    non_identifying_attributes?: Array<{ key: string; value: any }>;
  };
}

// ============================================================================
// API Response Types
// ============================================================================
export interface PaginatedResponse<T> {
  agents: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AgentListParams {
  page?: number;
  size?: number;
  os_type?: string;
  connected?: boolean;
  healthy?: boolean;
  search?: string;
}

export interface AgentStats {
  total_agents: number;
  connected_agents: number;
  disconnected_agents: number;
  healthy_agents: number;
  unhealthy_agents: number;
  os_distribution: Record<string, number>;
}

// ============================================================================
// Config Version Types
// ============================================================================
export interface ConfigVersionUser {
  id: number;
  name: string;
  email: string;
  login: string;
}

export interface ConfigVersion {
  id: number;
  instance_id: string;
  version: number;
  config_hash: string;
  effective_config: string;
  source: string;
  updated_by_user_id?: number | null;
  updated_by_user?: ConfigVersionUser | null;
  created_at: string;
  updated_at: string;
}

export interface SaveConfigRequest {
  config: string;
}

export interface RestoreConfigRequest {
  version: number;
}

// ============================================================================
// Error Types
// ============================================================================
export interface ApiError {
  detail: string;
  status?: number;
}
