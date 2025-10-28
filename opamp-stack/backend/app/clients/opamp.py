"""OpAMP server client with retry logic and timeout handling."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import httpx
from httpx import AsyncClient, Response

from app.settings import settings
from app.core.utils.backoff import exponential_backoff

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Agent information from OpAMP server."""
    id: str
    name: str
    env: Optional[str] = None
    os: Optional[str] = None
    arch: Optional[str] = None
    version: Optional[str] = None
    status: str = "unknown"
    last_seen: Optional[datetime] = None
    config_version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OpAMPClientError(Exception):
    """Base exception for OpAMP client errors."""
    pass


class OpAMPConnectionError(OpAMPClientError):
    """Connection error to OpAMP server."""
    pass


class OpAMPAPIError(OpAMPClientError):
    """API error from OpAMP server."""
    pass


class OpAMPClient:
    """Async HTTP client for OpAMP server API."""
    
    def __init__(
        self,
        base_url: str = None,
        timeout: int = None,
        retry_attempts: int = None
    ):
        """Initialize OpAMP client.
        
        Args:
            base_url: OpAMP server base URL
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
        """
        self.base_url = (base_url or settings.opamp_base_url).rstrip('/')
        self.timeout = timeout or settings.opamp_timeout
        self.retry_attempts = retry_attempts or settings.opamp_retry_attempts
        
        self._client: Optional[AsyncClient] = None
        
        logger.info(f"OpAMP client initialized with base_url: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                follow_redirects=True
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Response:
        """Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request arguments
            
        Returns:
            HTTP response
            
        Raises:
            OpAMPConnectionError: Connection failed
            OpAMPAPIError: API returned error
        """
        await self._ensure_client()
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.retry_attempts + 1):
            try:
                logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self._client.request(method, url, **kwargs)
                
                # Check for HTTP errors
                if response.status_code >= 400:
                    if response.status_code >= 500 and attempt < self.retry_attempts:
                        # Server error - retry
                        await asyncio.sleep(exponential_backoff(attempt))
                        continue
                    
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    raise OpAMPAPIError(error_msg)
                
                logger.debug(f"Request successful: {response.status_code}")
                return response
                
            except httpx.ConnectError as e:
                if attempt < self.retry_attempts:
                    logger.warning(f"Connection failed (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(exponential_backoff(attempt))
                    continue
                raise OpAMPConnectionError(f"Failed to connect to OpAMP server: {e}")
            
            except httpx.TimeoutException as e:
                if attempt < self.retry_attempts:
                    logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(exponential_backoff(attempt))
                    continue
                raise OpAMPConnectionError(f"Request timeout: {e}")
            
            except Exception as e:
                if attempt < self.retry_attempts:
                    logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                    await asyncio.sleep(exponential_backoff(attempt))
                    continue
                raise OpAMPClientError(f"Unexpected error: {e}")
        
        raise OpAMPConnectionError("Max retry attempts exceeded")
    
    async def list_agents(self, env: Optional[str] = None) -> List[AgentInfo]:
        """List all agents from OpAMP server.
        
        Args:
            env: Optional environment filter
            
        Returns:
            List of agent information
            
        Raises:
            OpAMPClientError: Request failed
        """
        params = {}
        if env:
            params['env'] = env
        
        try:
            response = await self._make_request('GET', '/agents/json', params=params)
            data = response.json()
            
            agents = []
            # Data is now a list of agent objects directly
            for agent_data in data:
                # Extract basic info
                instance_id = agent_data.get('instanceId', agent_data.get('instanceIdStr', ''))
                
                # Extract service name from identifying attributes
                service_name = instance_id
                service_version = None
                arch = None
                os_type = None
                host_name = None
                
                # Parse agent_description for attributes
                status_info = agent_data.get('status', {})
                agent_desc = status_info.get('agent_description', {})
                
                # Extract from identifying_attributes
                identifying_attrs = agent_desc.get('identifying_attributes', [])
                for attr in identifying_attrs:
                    key = attr.get('key', '')
                    value_obj = attr.get('value', {}).get('Value', {})
                    string_value = value_obj.get('StringValue', '')
                    
                    if key == 'service.name':
                        service_name = string_value
                    elif key == 'service.version':
                        service_version = string_value
                
                # Extract from non_identifying_attributes
                non_identifying_attrs = agent_desc.get('non_identifying_attributes', [])
                for attr in non_identifying_attrs:
                    key = attr.get('key', '')
                    value_obj = attr.get('value', {}).get('Value', {})
                    string_value = value_obj.get('StringValue', '')
                    
                    if key == 'host.arch':
                        arch = string_value
                    elif key == 'os.type':
                        os_type = string_value
                    elif key == 'host.name':
                        host_name = string_value
                
                # Determine status from health info
                health_info = status_info.get('health', {})
                agent_status = 'healthy' if health_info.get('healthy', False) else 'unhealthy'
                
                # Parse start time for last_seen
                last_seen = None
                start_time_nano = health_info.get('start_time_unix_nano')
                if start_time_nano:
                    try:
                        # Convert nanoseconds to seconds
                        start_time_seconds = start_time_nano / 1_000_000_000
                        last_seen = datetime.fromtimestamp(start_time_seconds)
                    except (ValueError, TypeError):
                        pass
                
                # Get config version from effective_config
                config_version = None
                effective_config = status_info.get('effective_config', {})
                if effective_config:
                    config_version = str(hash(str(effective_config)))[:8]  # Simple hash for version
                
                agent = AgentInfo(
                    id=instance_id,
                    name=service_name or instance_id,
                    env=env,  # Use the provided env filter
                    os=os_type,
                    arch=arch,
                    version=service_version,
                    status=agent_status,
                    last_seen=last_seen,
                    config_version=config_version,
                    metadata={
                        'host_name': host_name,
                        'health_status': health_info.get('status'),
                        'capabilities': status_info.get('capabilities'),
                        'started_at': agent_data.get('startedAt')
                    }
                )
                
                agents.append(agent)
            
            logger.info(f"Retrieved {len(agents)} agents from OpAMP server")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            raise
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get detailed agent information.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent information or None if not found
            
        Raises:
            OpAMPClientError: Request failed
        """
        params = {'instanceid': agent_id}
        
        try:
            response = await self._make_request('GET', '/agent/json', params=params)
            data = response.json()
            
            # Extract basic info
            instance_id = data.get('instanceId', data.get('instanceIdStr', ''))
            
            # Extract service name from identifying attributes
            service_name = instance_id
            service_version = None
            arch = None
            os_type = None
            host_name = None
            
            # Parse agent_description for attributes
            status_info = data.get('status', {})
            agent_desc = status_info.get('agent_description', {})
            
            # Extract from identifying_attributes
            identifying_attrs = agent_desc.get('identifying_attributes', [])
            for attr in identifying_attrs:
                key = attr.get('key', '')
                value_obj = attr.get('value', {}).get('Value', {})
                string_value = value_obj.get('StringValue', '')
                
                if key == 'service.name':
                    service_name = string_value
                elif key == 'service.version':
                    service_version = string_value
            
            # Extract from non_identifying_attributes
            non_identifying_attrs = agent_desc.get('non_identifying_attributes', [])
            for attr in non_identifying_attrs:
                key = attr.get('key', '')
                value_obj = attr.get('value', {}).get('Value', {})
                string_value = value_obj.get('StringValue', '')
                
                if key == 'host.arch':
                    arch = string_value
                elif key == 'os.type':
                    os_type = string_value
                elif key == 'host.name':
                    host_name = string_value
            
            # Determine status from health info
            health_info = status_info.get('health', {})
            agent_status = 'healthy' if health_info.get('healthy', False) else 'unhealthy'
            
            # Parse start time for last_seen
            last_seen = None
            start_time_nano = health_info.get('start_time_unix_nano')
            if start_time_nano:
                try:
                    # Convert nanoseconds to seconds
                    start_time_seconds = start_time_nano / 1_000_000_000
                    last_seen = datetime.fromtimestamp(start_time_seconds)
                except (ValueError, TypeError):
                    pass
            
            # Get config version from effective_config
            config_version = None
            effective_config = status_info.get('effective_config', {})
            if effective_config:
                config_version = str(hash(str(effective_config)))[:8]  # Simple hash for version
            
            agent = AgentInfo(
                id=instance_id,
                name=service_name or instance_id,
                env=None,  # Env not directly available in this format
                os=os_type,
                arch=arch,
                version=service_version,
                status=agent_status,
                last_seen=last_seen,
                config_version=config_version,
                metadata={
                    'host_name': host_name,
                    'health_status': health_info.get('status'),
                    'capabilities': status_info.get('capabilities'),
                    'started_at': data.get('startedAt'),
                    'effective_config': data.get('effectiveConfig')
                }
            )
            
            logger.debug(f"Retrieved agent {agent_id} details")
            return agent
            
        except OpAMPAPIError as e:
            if "404" in str(e):
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise
    
    async def apply_config(
        self,
        agent_id: str,
        config_yaml: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply configuration to an agent.
        
        Args:
            agent_id: Agent ID
            config_yaml: Configuration in YAML format
            version: Optional version string
            
        Returns:
            Response data from server
            
        Raises:
            OpAMPClientError: Request failed
        """
        payload = {
            'config': config_yaml,
            'version': version or datetime.utcnow().isoformat()
        }
        
        try:
            response = await self._make_request(
                'POST',
                f'/api/agents/{agent_id}/config',
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            result = response.json()
            logger.info(f"Applied config to agent {agent_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply config to agent {agent_id}: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if OpAMP server is healthy.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = await self._make_request('GET', '/health', timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpAMP server health check failed: {e}")
            return False


# Global OpAMP client instance
opamp_client = OpAMPClient()