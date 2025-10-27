"""Agent service for managing agent operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.db.models import Agent, AgentStatusSnapshot
from app.clients.opamp import opamp_client, AgentInfo
from app.core.utils.pagination import PaginationParams, paginate_query

logger = logging.getLogger(__name__)


class AgentService:
    """Service for managing agents."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    async def sync_agents_from_opamp(self, env_filter: Optional[str] = None) -> int:
        """Sync agents from OpAMP server to local database.
        
        Args:
            env_filter: Optional environment filter
            
        Returns:
            Number of agents synchronized
        """
        try:
            # Fetch agents from OpAMP server
            async with opamp_client:
                opamp_agents = await opamp_client.list_agents(env=env_filter)
            
            synced_count = 0
            
            for opamp_agent in opamp_agents:
                # Get or create agent in database
                agent = self.db.query(Agent).filter(Agent.id == opamp_agent.id).first()
                
                if agent is None:
                    # Create new agent
                    agent = Agent(
                        id=opamp_agent.id,
                        name=opamp_agent.name,
                        env=opamp_agent.env,
                        os=opamp_agent.os,
                        arch=opamp_agent.arch,
                        version=opamp_agent.version,
                        first_seen=opamp_agent.last_seen or datetime.utcnow(),
                        last_seen=opamp_agent.last_seen or datetime.utcnow(),
                        last_status=opamp_agent.status,
                        last_config_version=opamp_agent.config_version,
                    )
                    self.db.add(agent)
                    logger.info(f"Created new agent: {agent.id}")
                else:
                    # Update existing agent
                    updated = False
                    
                    if agent.name != opamp_agent.name:
                        agent.name = opamp_agent.name
                        updated = True
                    
                    if agent.env != opamp_agent.env:
                        agent.env = opamp_agent.env
                        updated = True
                    
                    if agent.os != opamp_agent.os:
                        agent.os = opamp_agent.os
                        updated = True
                    
                    if agent.arch != opamp_agent.arch:
                        agent.arch = opamp_agent.arch
                        updated = True
                    
                    if agent.version != opamp_agent.version:
                        agent.version = opamp_agent.version
                        updated = True
                    
                    if opamp_agent.last_seen and agent.last_seen != opamp_agent.last_seen:
                        agent.last_seen = opamp_agent.last_seen
                        updated = True
                    
                    if agent.last_status != opamp_agent.status:
                        # Create status snapshot
                        self._create_status_snapshot(
                            agent.id,
                            opamp_agent.status,
                            f"Status changed from {agent.last_status} to {opamp_agent.status}"
                        )
                        agent.last_status = opamp_agent.status
                        updated = True
                    
                    if agent.last_config_version != opamp_agent.config_version:
                        agent.last_config_version = opamp_agent.config_version
                        updated = True
                    
                    if updated:
                        agent.updated_at = datetime.utcnow()
                        logger.debug(f"Updated agent: {agent.id}")
                
                synced_count += 1
            
            self.db.commit()
            logger.info(f"Synchronized {synced_count} agents from OpAMP server")
            return synced_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to sync agents from OpAMP: {e}")
            raise
    
    def get_agents(
        self,
        pagination: PaginationParams,
        env_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[List[Agent], int]:
        """Get paginated list of agents with filters.
        
        Args:
            pagination: Pagination parameters
            env_filter: Environment filter
            status_filter: Status filter
            search: Search term for name or ID
            
        Returns:
            Tuple of (agents, total_count)
        """
        query = self.db.query(Agent)
        
        # Apply filters
        filters = []
        
        if env_filter:
            filters.append(Agent.env == env_filter)
        
        if status_filter:
            filters.append(Agent.last_status == status_filter)
        
        if search:
            search_term = f"%{search}%"
            filters.append(
                or_(
                    Agent.id.ilike(search_term),
                    Agent.name.ilike(search_term)
                )
            )
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Order by last_seen desc
        query = query.order_by(desc(Agent.last_seen))
        
        return paginate_query(query, pagination)
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent or None if not found
        """
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    async def get_agent_from_opamp(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent details from OpAMP server.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent info or None if not found
        """
        try:
            async with opamp_client:
                return await opamp_client.get_agent(agent_id)
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id} from OpAMP: {e}")
            return None
    
    def get_agent_status_history(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[AgentStatusSnapshot]:
        """Get agent status history.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of snapshots to return
            
        Returns:
            List of status snapshots
        """
        return (
            self.db.query(AgentStatusSnapshot)
            .filter(AgentStatusSnapshot.agent_id == agent_id)
            .order_by(desc(AgentStatusSnapshot.timestamp))
            .limit(limit)
            .all()
        )
    
    def _create_status_snapshot(
        self,
        agent_id: str,
        status: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentStatusSnapshot:
        """Create a status snapshot.
        
        Args:
            agent_id: Agent ID
            status: New status
            reason: Reason for status change
            metadata: Additional metadata
            
        Returns:
            Created status snapshot
        """
        snapshot = AgentStatusSnapshot(
            agent_id=agent_id,
            status=status,
            reason=reason,
            status_metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(snapshot)
        return snapshot
    
    def get_environment_list(self) -> List[str]:
        """Get list of all environments.
        
        Returns:
            List of environment names
        """
        results = (
            self.db.query(Agent.env)
            .filter(Agent.env.isnot(None))
            .distinct()
            .all()
        )
        
        return [env[0] for env in results if env[0]]
    
    def get_agent_counts_by_status(self) -> Dict[str, int]:
        """Get agent counts grouped by status.
        
        Returns:
            Dictionary of status -> count
        """
        results = (
            self.db.query(Agent.last_status, self.db.func.count(Agent.id))
            .group_by(Agent.last_status)
            .all()
        )
        
        return {status or 'unknown': count for status, count in results}
    
    def get_agent_counts_by_env(self) -> Dict[str, int]:
        """Get agent counts grouped by environment.
        
        Returns:
            Dictionary of environment -> count
        """
        results = (
            self.db.query(Agent.env, self.db.func.count(Agent.id))
            .group_by(Agent.env)
            .all()
        )
        
        return {env or 'unknown': count for env, count in results}