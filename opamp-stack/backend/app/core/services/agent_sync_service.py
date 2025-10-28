"""Service for synchronizing agents from OpAMP server."""

import logging
from typing import List, Optional, Set
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import Agent, AgentStatusSnapshot
from app.clients.opamp import opamp_client, AgentInfo
from app.settings import settings

logger = logging.getLogger(__name__)


class AgentSyncService:
    """Service for synchronizing agents with OpAMP server."""
    
    def __init__(self, db: Session):
        """Initialize agent sync service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def sync_agents_from_opamp(self) -> dict:
        """Sync agents from OpAMP server.
        
        Returns:
            Dictionary with sync results
        """
        try:
            logger.info("Starting agent synchronization from OpAMP server")
            
            # Get agents from OpAMP server
            opamp_agents = await self._get_opamp_agents()
            
            # Get existing agents from database
            db_agents = self._get_db_agents()
            
            # Process synchronization
            results = await self._process_sync(opamp_agents, db_agents)
            
            logger.info(f"Agent synchronization completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to sync agents from OpAMP server: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_opamp": 0,
                "total_db": 0,
                "created": 0,
                "updated": 0,
                "marked_unhealthy": 0
            }
    
    async def _get_opamp_agents(self) -> List[AgentInfo]:
        """Get agents from OpAMP server.
        
        Returns:
            List of agent information from OpAMP server
        """
        try:
            async with opamp_client:
                agents = await opamp_client.list_agents()
                logger.debug(f"Retrieved {len(agents)} agents from OpAMP server")
                return agents
        except Exception as e:
            logger.error(f"Failed to get agents from OpAMP server: {e}")
            return []
    
    def _get_db_agents(self) -> List[Agent]:
        """Get all agents from database.
        
        Returns:
            List of agents from database
        """
        return self.db.query(Agent).all()
    
    async def _process_sync(self, opamp_agents: List[AgentInfo], db_agents: List[Agent]) -> dict:
        """Process synchronization between OpAMP and database agents.
        
        Args:
            opamp_agents: Agents from OpAMP server
            db_agents: Agents from database
            
        Returns:
            Dictionary with sync results
        """
        # Create sets for efficient lookups
        opamp_agent_ids = {agent.id for agent in opamp_agents}
        db_agent_dict = {agent.id: agent for agent in db_agents}
        
        created_count = 0
        updated_count = 0
        marked_unhealthy_count = 0
        
        # Process agents from OpAMP server
        for opamp_agent in opamp_agents:
            if opamp_agent.id in db_agent_dict:
                # Update existing agent
                if self._update_existing_agent(db_agent_dict[opamp_agent.id], opamp_agent):
                    updated_count += 1
            else:
                # Create new agent
                self._create_new_agent(opamp_agent)
                created_count += 1
        
        # Mark agents as unhealthy if they're not in OpAMP server response
        for db_agent_id, db_agent in db_agent_dict.items():
            if db_agent_id not in opamp_agent_ids:
                if self._mark_agent_unhealthy(db_agent):
                    marked_unhealthy_count += 1
        
        # Commit changes
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to commit agent sync changes: {e}")
            self.db.rollback()
            raise
        
        return {
            "success": True,
            "total_opamp": len(opamp_agents),
            "total_db": len(db_agents),
            "created": created_count,
            "updated": updated_count,
            "marked_unhealthy": marked_unhealthy_count
        }
    
    def _create_new_agent(self, opamp_agent: AgentInfo) -> Agent:
        """Create a new agent in database.
        
        Args:
            opamp_agent: Agent information from OpAMP server
            
        Returns:
            Created agent
        """
        now = datetime.utcnow()
        
        agent = Agent(
            id=opamp_agent.id,
            name=opamp_agent.name,
            env=opamp_agent.env,
            os=opamp_agent.os,
            arch=opamp_agent.arch,
            version=opamp_agent.version,
            first_seen=now,
            last_seen=opamp_agent.last_seen or now,
            last_status=opamp_agent.status,
            last_config_version=opamp_agent.config_version,
            created_at=now,
            updated_at=now
        )
        
        self.db.add(agent)
        
        # Create status snapshot
        self._create_status_snapshot(agent.id, opamp_agent.status, "Agent discovered via sync")
        
        logger.debug(f"Created new agent: {agent.id}")
        return agent
    
    def _update_existing_agent(self, db_agent: Agent, opamp_agent: AgentInfo) -> bool:
        """Update an existing agent with OpAMP server data.
        
        Args:
            db_agent: Agent from database
            opamp_agent: Agent information from OpAMP server
            
        Returns:
            True if agent was updated, False otherwise
        """
        updated = False
        now = datetime.utcnow()
        
        # Update basic information
        if db_agent.name != opamp_agent.name:
            db_agent.name = opamp_agent.name
            updated = True
        
        if db_agent.env != opamp_agent.env:
            db_agent.env = opamp_agent.env
            updated = True
        
        if db_agent.os != opamp_agent.os:
            db_agent.os = opamp_agent.os
            updated = True
        
        if db_agent.arch != opamp_agent.arch:
            db_agent.arch = opamp_agent.arch
            updated = True
        
        if db_agent.version != opamp_agent.version:
            db_agent.version = opamp_agent.version
            updated = True
        
        # Update last seen time
        if opamp_agent.last_seen:
            if db_agent.last_seen != opamp_agent.last_seen:
                db_agent.last_seen = opamp_agent.last_seen
                updated = True
        else:
            # If no last_seen from OpAMP, update to now (agent is active)
            db_agent.last_seen = now
            updated = True
        
        # Update status if changed
        if db_agent.last_status != opamp_agent.status:
            old_status = db_agent.last_status
            db_agent.last_status = opamp_agent.status
            updated = True
            
            # Create status snapshot for status change
            self._create_status_snapshot(
                db_agent.id, 
                opamp_agent.status, 
                f"Status changed from {old_status} to {opamp_agent.status} via sync"
            )
        
        # Update config version
        if db_agent.last_config_version != opamp_agent.config_version:
            db_agent.last_config_version = opamp_agent.config_version
            updated = True
        
        if updated:
            db_agent.updated_at = now
            logger.debug(f"Updated agent: {db_agent.id}")
        
        return updated
    
    def _mark_agent_unhealthy(self, db_agent: Agent) -> bool:
        """Mark an agent as unhealthy if it's not in OpAMP server response.
        
        Args:
            db_agent: Agent from database
            
        Returns:
            True if agent status was changed, False otherwise
        """
        # Only mark as unhealthy if it's not already unhealthy
        if db_agent.last_status != "unhealthy":
            old_status = db_agent.last_status
            db_agent.last_status = "unhealthy"
            db_agent.updated_at = datetime.utcnow()
            
            # Create status snapshot
            self._create_status_snapshot(
                db_agent.id,
                "unhealthy",
                f"Agent not found in OpAMP server response (was {old_status})"
            )
            
            logger.debug(f"Marked agent as unhealthy: {db_agent.id}")
            return True
        
        return False
    
    def _create_status_snapshot(self, agent_id: str, status: str, reason: str):
        """Create a status snapshot for an agent.
        
        Args:
            agent_id: Agent ID
            status: New status
            reason: Reason for status change
        """
        snapshot = AgentStatusSnapshot(
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            status=status,
            reason=reason
        )
        
        self.db.add(snapshot)