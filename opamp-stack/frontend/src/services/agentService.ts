import apiClient from './api';
import {
  Agent,
  AgentDetail,
  AgentHealth,
  AgentPipelineHealth,
  AgentListParams,
  AgentStats,
  PaginatedResponse,
  ConfigVersion,
  SaveConfigRequest,
} from '@/types';

// ============================================================================
// Agent Service
// ============================================================================
class AgentService {
  /**
   * Get paginated list of agents with filters
   */
  async getAgents(params?: AgentListParams): Promise<PaginatedResponse<Agent>> {
    const queryParams = new URLSearchParams();
    
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.size) queryParams.append('page_size', params.size.toString());
    if (params?.os_type) queryParams.append('os_type', params.os_type);
    if (params?.connected !== undefined) queryParams.append('connected', params.connected.toString());
    if (params?.healthy !== undefined) queryParams.append('healthy', params.healthy.toString());
    if (params?.search) queryParams.append('search', params.search);

    return apiClient.get<PaginatedResponse<Agent>>(
      `/api/v1/agents?${queryParams.toString()}`
    );
  }

  /**
   * Get detailed information about a specific agent
   */
  async getAgentDetail(instanceId: string): Promise<AgentDetail> {
    return apiClient.get<AgentDetail>(`/api/v1/agents/${instanceId}`);
  }

  /**
   * Get agent statistics for dashboard
   */
  async getAgentStats(): Promise<AgentStats> {
    return apiClient.get<AgentStats>('/api/v1/agents/stats');
  }

  /**
   * Download agent configuration as YAML
   */
  async downloadConfig(instanceId: string): Promise<Blob> {
    return apiClient.downloadFile(`/api/v1/agents/${instanceId}/config`);
  }

  /**
   * Get current configuration for an agent
   */
  async getCurrentConfig(instanceId: string): Promise<string> {
    // The endpoint returns plain text YAML, not JSON
    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache',
    };
    
    // Add authorization token if available
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Use relative path to work with nginx proxy in production
    // In dev, vite proxy will handle it
    const response = await fetch(
      `/api/v1/agents/${instanceId}/config`,
      {
        method: 'GET',
        cache: 'no-store', // Prevent caching to ensure fresh data
        headers,
      }
    );
    
    if (response.status === 401) {
      // Unauthorized - redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }
    
    if (!response.ok) {
      throw new Error('Failed to fetch configuration');
    }
    return response.text();
  }

  /**
   * Get configuration version history for an agent
   */
  async getConfigHistory(instanceId: string): Promise<ConfigVersion[]> {
    return apiClient.get<ConfigVersion[]>(`/api/v1/agents/${instanceId}/configs`);
  }

  /**
   * Get specific configuration version
   */
  async getConfigVersion(instanceId: string, version: number): Promise<ConfigVersion> {
    return apiClient.get<ConfigVersion>(
      `/api/v1/agents/${instanceId}/configs/${version}`
    );
  }

  /**
   * Save/update agent configuration
   */
  async saveConfig(instanceId: string, config: SaveConfigRequest): Promise<void> {
    return apiClient.post<void>(`/api/v1/config?instance_id=${instanceId}`, config);
  }

  /**
   * Restore a previous configuration version
   */
  async restoreConfig(instanceId: string, version: number): Promise<void> {
    return apiClient.post<void>(`/api/v1/agents/${instanceId}/config/restore?version=${version}`, {});
  }

  /**
   * Get agent health information
   */
  async getAgentHealth(instanceId: string, limit: number = 1): Promise<AgentHealth[]> {
    return apiClient.get<AgentHealth[]>(`/api/v1/agents/${instanceId}/health?limit=${limit}`);
  }

  /**
   * Get agent pipeline/component health information
   */
  async getAgentPipelineHealth(instanceId: string, componentName?: string): Promise<AgentPipelineHealth[]> {
    const params = componentName ? `?component_name=${componentName}` : '';
    return apiClient.get<AgentPipelineHealth[]>(`/api/v1/agents/${instanceId}/pipelines/health${params}`);
  }

  /**
   * Export all agents to CSV
   */
  async exportAgentsCSV(): Promise<Blob> {
    return apiClient.downloadFile('/api/v1/agents/csv');
  }

  /**
   * Delete an agent and all its history
   */
  async deleteAgent(instanceId: string): Promise<{ success: boolean; message: string; instance_id: string }> {
    return apiClient.delete<{ success: boolean; message: string; instance_id: string }>(
      `/api/v1/agents/${instanceId}`
    );
  }

  /**
   * Sync a specific agent with OpAMP server
   */
  async syncAgent(instanceId: string): Promise<{ success: boolean; message: string; instance_id: string; updated: boolean; config_versioned: boolean }> {
    return apiClient.post<{ success: boolean; message: string; instance_id: string; updated: boolean; config_versioned: boolean }>(
      `/api/v1/opamp/sync/${instanceId}`,
      {}
    );
  }
}

export const agentService = new AgentService();
export default agentService;
