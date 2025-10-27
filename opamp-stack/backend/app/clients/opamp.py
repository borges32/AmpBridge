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
            response = await self._make_request('GET', '/api/agents', params=params)
            data = response.json()
            
            agents = []
            for agent_data in data.get('agents', []):
                agent = AgentInfo(
                    id=agent_data['id'],
                    name=agent_data.get('name', agent_data['id']),
                    env=agent_data.get('env'),
                    os=agent_data.get('os'),
                    arch=agent_data.get('arch'),
                    version=agent_data.get('version'),
                    status=agent_data.get('status', 'unknown'),
                    config_version=agent_data.get('config_version'),
                    metadata=agent_data.get('metadata')
                )
                
                # Parse last_seen if provided
                if 'last_seen' in agent_data:
                    try:
                        agent.last_seen = datetime.fromisoformat(
                            agent_data['last_seen'].replace('Z', '+00:00')
                        )
                    except (ValueError, AttributeError):
                        pass
                
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
        try:
            response = await self._make_request('GET', f'/api/agents/{agent_id}')
            data = response.json()
            
            agent = AgentInfo(
                id=data['id'],
                name=data.get('name', data['id']),
                env=data.get('env'),
                os=data.get('os'),
                arch=data.get('arch'),
                version=data.get('version'),
                status=data.get('status', 'unknown'),
                config_version=data.get('config_version'),
                metadata=data.get('metadata')
            )
            
            # Parse last_seen if provided
            if 'last_seen' in data:
                try:
                    agent.last_seen = datetime.fromisoformat(
                        data['last_seen'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    pass
            
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