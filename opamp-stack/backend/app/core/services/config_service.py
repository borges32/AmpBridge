"""Configuration service for managing agent configurations."""

import logging
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.models import Config, Agent
from app.clients.opamp import opamp_client
from app.core.utils.pagination import PaginationParams, paginate_query

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing agent configurations."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def get_agent_configs(
        self,
        agent_id: str,
        pagination: PaginationParams
    ) -> tuple[List[Config], int]:
        """Get paginated list of configurations for an agent.
        
        Args:
            agent_id: Agent ID
            pagination: Pagination parameters
            
        Returns:
            Tuple of (configs, total_count)
        """
        query = (
            self.db.query(Config)
            .filter(Config.agent_id == agent_id)
            .order_by(desc(Config.timestamp))
        )
        
        return paginate_query(query, pagination)
    
    def get_config_by_id(self, config_id: int) -> Optional[Config]:
        """Get configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Configuration or None if not found
        """
        return self.db.query(Config).filter(Config.id == config_id).first()
    
    def get_latest_config(self, agent_id: str) -> Optional[Config]:
        """Get latest configuration for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Latest configuration or None if not found
        """
        return (
            self.db.query(Config)
            .filter(Config.agent_id == agent_id)
            .order_by(desc(Config.timestamp))
            .first()
        )
    
    async def apply_config(
        self,
        agent_id: str,
        config_yaml: str,
        applied_by: str,
        version: Optional[str] = None
    ) -> Config:
        """Apply configuration to an agent.
        
        Args:
            agent_id: Agent ID
            config_yaml: Configuration in YAML format
            applied_by: Username who applied the config
            version: Optional version string
            
        Returns:
            Created configuration record
            
        Raises:
            ValueError: If agent not found
            Exception: If config application fails
        """
        # Verify agent exists
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Generate version if not provided
        if not version:
            version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Calculate checksum
        checksum = hashlib.sha256(config_yaml.encode()).hexdigest()
        
        # Check if this exact config was already applied
        existing_config = (
            self.db.query(Config)
            .filter(Config.agent_id == agent_id, Config.checksum == checksum)
            .first()
        )
        
        if existing_config:
            logger.info(f"Config with checksum {checksum} already applied to agent {agent_id}")
            return existing_config
        
        try:
            # Apply config via OpAMP
            async with opamp_client:
                result = await opamp_client.apply_config(agent_id, config_yaml, version)
            
            # Create config record
            config = Config(
                agent_id=agent_id,
                version=version,
                config_yaml=config_yaml,
                applied_by=applied_by,
                checksum=checksum,
                timestamp=datetime.utcnow()
            )
            
            self.db.add(config)
            
            # Update agent's last config version
            agent.last_config_version = version
            agent.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Applied config version {version} to agent {agent_id}")
            return config
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to apply config to agent {agent_id}: {e}")
            raise
    
    def compare_configs(self, config1_id: int, config2_id: int) -> Dict[str, Any]:
        """Compare two configurations.
        
        Args:
            config1_id: First configuration ID
            config2_id: Second configuration ID
            
        Returns:
            Comparison result
            
        Raises:
            ValueError: If configurations not found
        """
        config1 = self.get_config_by_id(config1_id)
        config2 = self.get_config_by_id(config2_id)
        
        if not config1:
            raise ValueError(f"Configuration {config1_id} not found")
        
        if not config2:
            raise ValueError(f"Configuration {config2_id} not found")
        
        return {
            "config1": {
                "id": config1.id,
                "version": config1.version,
                "timestamp": config1.timestamp.isoformat(),
                "checksum": config1.checksum,
                "applied_by": config1.applied_by
            },
            "config2": {
                "id": config2.id,
                "version": config2.version,
                "timestamp": config2.timestamp.isoformat(),
                "checksum": config2.checksum,
                "applied_by": config2.applied_by
            },
            "same_content": config1.checksum == config2.checksum,
            "yaml_diff": self._generate_yaml_diff(
                config1.config_yaml,
                config2.config_yaml
            ) if config1.checksum != config2.checksum else None
        }
    
    def _generate_yaml_diff(self, yaml1: str, yaml2: str) -> Dict[str, Any]:
        """Generate a simple diff between two YAML strings.
        
        Args:
            yaml1: First YAML content
            yaml2: Second YAML content
            
        Returns:
            Simple diff information
        """
        lines1 = yaml1.split('\n')
        lines2 = yaml2.split('\n')
        
        # Simple line-by-line comparison
        added_lines = []
        removed_lines = []
        
        # Find lines in yaml2 but not in yaml1
        for i, line in enumerate(lines2):
            if line not in lines1:
                added_lines.append({"line": i + 1, "content": line})
        
        # Find lines in yaml1 but not in yaml2
        for i, line in enumerate(lines1):
            if line not in lines2:
                removed_lines.append({"line": i + 1, "content": line})
        
        return {
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "total_changes": len(added_lines) + len(removed_lines)
        }
    
    def get_config_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics.
        
        Returns:
            Configuration statistics
        """
        total_configs = self.db.query(Config).count()
        
        # Count unique agents with configs
        agents_with_configs = (
            self.db.query(Config.agent_id)
            .distinct()
            .count()
        )
        
        # Get most recent config applications
        recent_configs = (
            self.db.query(Config)
            .order_by(desc(Config.timestamp))
            .limit(5)
            .all()
        )
        
        return {
            "total_configurations": total_configs,
            "agents_with_configs": agents_with_configs,
            "recent_applications": [
                {
                    "agent_id": config.agent_id,
                    "version": config.version,
                    "applied_by": config.applied_by,
                    "timestamp": config.timestamp.isoformat()
                }
                for config in recent_configs
            ]
        }