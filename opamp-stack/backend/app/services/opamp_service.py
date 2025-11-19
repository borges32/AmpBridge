"""
Service layer for OpAMP synchronization and integration.
Handles communication with OpAMP server and data synchronization.

PERFORMANCE OPTIMIZATION for 10k+ agents:
- Batch processing with asyncio.gather
- Bulk database operations (bulk_upsert, bulk_create)
- Single commit per batch
- Parallel processing of independent operations
- Reduced N+1 query patterns
"""
import asyncio
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import settings
from app.repositories.agent_repository import AgentRepository
from app.repositories.agent_health_repository import AgentHealthRepository
from app.repositories.agent_config_repository import AgentConfigRepository
from app.repositories.agent_pipeline_health_repository import AgentPipelineHealthRepository
from app.schemas import (
    OpAMPAgentData, 
    SyncResponse, 
    AgentHealthCreate,
    AgentConfigCreate,
    AgentPipelineHealthCreate
)

logger = logging.getLogger(__name__)


class OpAMPService:
    """Service for OpAMP server integration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.health_repo = AgentHealthRepository(db)
        self.config_repo = AgentConfigRepository(db)
        self.pipeline_health_repo = AgentPipelineHealthRepository(db)
        self.opamp_url = settings.OPAMP_SERVER_URL
    
    async def fetch_agents_from_opamp(self) -> List[Dict[str, Any]]:
        """
        Fetch all agents from OpAMP server.
        
        Returns:
            List of agent data from OpAMP
        """
        url = f"{self.opamp_url}/agents/full"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch agents from OpAMP: {e}")
            raise
    
    def extract_agent_attributes(self, status: Dict) -> Dict[str, Any]:
        """
        Extract agent attributes from OpAMP status.
        
        Args:
            status: Status dict from OpAMP response
            
        Returns:
            Dict with extracted attributes
        """
        attributes = {}
        
        agent_desc = status.get("agent_description", {})
        
        # Extract from identifying_attributes (service.name, service.version)
        id_attrs = agent_desc.get("identifying_attributes", [])
        for attr in id_attrs:
            key = attr.get("key")
            value_obj = attr.get("value", {}).get("Value", {})
            
            if key == "service.name":
                attributes["service_name"] = value_obj.get("StringValue")
            elif key == "service.version":
                attributes["service_version"] = value_obj.get("StringValue")
        
        # Extract from non_identifying_attributes (host.name, os.type, os.description, host.arch)
        non_id_attrs = agent_desc.get("non_identifying_attributes", [])
        for attr in non_id_attrs:
            key = attr.get("key")
            value_obj = attr.get("value", {}).get("Value", {})
            
            if key == "host.name":
                attributes["host_name"] = value_obj.get("StringValue")
            elif key == "os.type":
                attributes["os_type"] = value_obj.get("StringValue")
            elif key == "os.description":
                attributes["os_description"] = value_obj.get("StringValue")
            elif key == "host.arch":
                attributes["host_arch"] = value_obj.get("StringValue")
        
        return attributes
    
    def compute_config_hash(self, config: str) -> str:
        """Compute SHA256 hash of configuration."""
        return hashlib.sha256(config.encode()).hexdigest()
    
    def clean_config(self, config: str) -> str:
        """
        Remove trailing blank lines and newlines from configuration string.
        Does NOT add any newline at the end - keeps the config clean.
        
        This removes all trailing:
        - Newlines (\n)
        - Carriage returns (\r)
        - Spaces
        
        Args:
            config: Configuration string
            
        Returns:
            Cleaned configuration string without trailing whitespace
        """
        if not config:
            return config
        return config.rstrip('\n\r ')
    
    async def _save_component_health_async(
        self,
        instance_id: str,
        component_type: str,
        component_name: str,
        parent_pipeline: Optional[str],
        component_data: Dict[str, Any]
    ) -> None:
        """
        Helper method to save component health data.
        
        Args:
            instance_id: Agent instance ID
            component_type: Type of component (pipeline, extension, exporter, processor, receiver)
            component_name: Name of the component
            parent_pipeline: Parent pipeline name (if this is a sub-component)
            component_data: Health data from OpAMP
        """
        component_healthy = component_data.get("healthy", False)
        component_status = component_data.get("status", "UNKNOWN")
        component_status_time = component_data.get("status_time_unix_nano")
        component_last_error = component_data.get("last_error")
        
        health_create = AgentPipelineHealthCreate(
            instance_id=instance_id,
            component_type=component_type,
            component_name=component_name,
            parent_pipeline=parent_pipeline,
            healthy=component_healthy,
            status=component_status,
            status_time_unix_nano=component_status_time,
            last_error=component_last_error
        )
        await self.pipeline_health_repo.create(health_create)
    
    async def sync_agent(
        self, 
        agent_data: Dict[str, Any],
        source: str = "SYNC_JOB"
    ) -> Dict[str, Any]:
        """
        Synchronize a single agent from OpAMP data.
        
        Returns:
            Dict with sync results
        """
        instance_id = agent_data.get("instanceId")
        status = agent_data.get("status", {})
        effective_config = agent_data.get("effectiveConfig", "")
        started_at_str = agent_data.get("startedAt")
        
        # Parse started_at
        started_at = None
        if started_at_str:
            try:
                started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            except:
                pass
        
        # Extract attributes
        attributes = self.extract_agent_attributes(status)
        
        # Extract health
        health_data = status.get("health", {})
        healthy = health_data.get("healthy", False)
        health_status = health_data.get("status", "UNKNOWN")
        status_time_unix_nano = health_data.get("status_time_unix_nano")
        
        # Upsert agent
        agent_dict = {
            "instance_id": instance_id,
            "host_name": attributes.get("host_name"),
            "os_type": attributes.get("os_type"),
            "os_description": attributes.get("os_description"),
            "service_name": attributes.get("service_name"),
            "service_version": attributes.get("service_version"),
            "host_arch": attributes.get("host_arch"),
            "healthy": healthy,
            "is_connected": True,
            "started_at": started_at
        }
        
        agent = await self.agent_repo.upsert(instance_id, agent_dict)
        
        # Create health record
        health_create = AgentHealthCreate(
            instance_id=instance_id,
            healthy=healthy,
            status=health_status,
            status_time_unix_nano=status_time_unix_nano
        )
        await self.health_repo.create(health_create)
        
        # Cleanup old health records - keep only last 10
        await self.health_repo.cleanup_old_records(instance_id, keep_last=10)
        
        # Extract and save pipeline/component health
        component_health_map = health_data.get("component_health_map", {})
        if component_health_map:
            # Delete all existing pipeline health records for this agent
            # We only keep the current state, no history
            await self.pipeline_health_repo.delete_all_by_instance_id(instance_id)
            
            # Process each top-level component (extensions, pipelines)
            for component_key, component_data in component_health_map.items():
                if component_key == "extensions":
                    # Extensions is a special group - save as a single component
                    await self._save_component_health_async(
                        instance_id=instance_id,
                        component_type="extensions",
                        component_name="extensions",
                        parent_pipeline=None,
                        component_data=component_data
                    )
                    
                    # Also save individual extensions as sub-components
                    ext_health_map = component_data.get("component_health_map", {})
                    for ext_key, ext_data in ext_health_map.items():
                        ext_name = ext_key.replace("extension:", "", 1)
                        await self._save_component_health_async(
                            instance_id=instance_id,
                            component_type="extension",
                            component_name=ext_name,
                            parent_pipeline="extensions",
                            component_data=ext_data
                        )
                
                elif component_key.startswith("pipeline:"):
                    # Extract pipeline name (remove "pipeline:" prefix)
                    pipeline_name = component_key.replace("pipeline:", "", 1)
                    
                    # Save the pipeline itself
                    await self._save_component_health_async(
                        instance_id=instance_id,
                        component_type="pipeline",
                        component_name=pipeline_name,
                        parent_pipeline=None,
                        component_data=component_data
                    )
                    
                    # Save pipeline sub-components (exporters, processors, receivers)
                    pipeline_health_map = component_data.get("component_health_map", {})
                    for sub_key, sub_data in pipeline_health_map.items():
                        # Extract component type and name (e.g., "exporter:otlp/loadbalancing")
                        if ":" in sub_key:
                            comp_type, comp_name = sub_key.split(":", 1)
                            await self._save_component_health_async(
                                instance_id=instance_id,
                                component_type=comp_type,
                                component_name=comp_name,
                                parent_pipeline=pipeline_name,
                                component_data=sub_data
                            )
        
        # Check config versioning
        config_versioned = False
        if effective_config:
            # Clean trailing blank lines and newlines from config
            effective_config_original = effective_config
            effective_config = self.clean_config(effective_config)
            
            logger.info(f"[SYNC] Config from OpAMP - Original len: {len(effective_config_original)}, Cleaned len: {len(effective_config)}, Last 20 hex: {effective_config[-20:].encode().hex() if len(effective_config) >= 20 else effective_config.encode().hex()}")
            
            config_hash = self.compute_config_hash(effective_config)
            latest_config = await self.config_repo.get_latest_by_instance_id(instance_id)
            
            # Create new version if config changed
            should_version = False
            if not latest_config:
                should_version = True
                logger.info(f"No previous config found for {instance_id}, creating first version")
            else:
                # Clean the stored config before comparing to avoid false positives
                # from trailing whitespace differences added by OpAMP server
                stored_config_cleaned = self.clean_config(latest_config.effective_config)
                stored_config_hash = self.compute_config_hash(stored_config_cleaned)
                
                logger.info(f"[SYNC] Stored config - Ver: {latest_config.version}, Len: {len(latest_config.effective_config)}, Cleaned len: {len(stored_config_cleaned)}, Last 20 hex: {stored_config_cleaned[-20:].encode().hex() if len(stored_config_cleaned) >= 20 else stored_config_cleaned.encode().hex()}")
                logger.info(f"[SYNC] Hash comparison - New: {config_hash[:16]}..., Stored: {stored_config_hash[:16]}..., Equal: {stored_config_hash == config_hash}")
                
                if stored_config_hash != config_hash:
                    should_version = True
                    logger.info(f"Config changed for {instance_id}, creating new version")
            
            if should_version:
                next_version = await self.config_repo.get_next_version(instance_id)
                
                config_create = AgentConfigCreate(
                    instance_id=instance_id,
                    version=next_version,
                    effective_config=effective_config,
                    config_hash=config_hash,
                    source=source
                )
                await self.config_repo.create(config_create)
                
                # Set alert
                agent.alert_config = True
                agent.status_sync = "OUT_OF_SYNC"
                config_versioned = True
            else:
                # Config unchanged
                if agent.alert_config:
                    agent.status_sync = "IN_SYNC"
                    agent.alert_config = False
        
        await self.db.commit()
        
        return {
            "instance_id": instance_id,
            "updated": True,
            "config_versioned": config_versioned
        }
    
    async def sync_all_agents(self) -> SyncResponse:
        """
        Synchronize all agents from OpAMP server.
        
        OPTIMIZED FOR 10k+ AGENTS:
        - Processes agents in batches (OPAMP_SYNC_BATCH_SIZE)
        - Uses asyncio.gather for parallel processing within batches
        - Bulk database operations to minimize commits
        - Single query to fetch latest configs for all agents
        
        Returns:
            SyncResponse with results
        """
        errors = []
        agents_processed = 0
        agents_updated = 0
        configs_versioned = 0
        
        try:
            # Fetch agents from OpAMP
            logger.info("Fetching agents from OpAMP server...")
            opamp_agents = await self.fetch_agents_from_opamp()
            
            # Handle None or empty response from OpAMP server
            if opamp_agents is None:
                opamp_agents = []
            
            total_agents = len(opamp_agents)
            logger.info(f"Received {total_agents} agents from OpAMP server")
            
            # Track instance IDs from OpAMP
            opamp_instance_ids = []
            
            # Process in batches for optimal performance
            batch_size = settings.OPAMP_SYNC_BATCH_SIZE
            
            for batch_start in range(0, total_agents, batch_size):
                batch_end = min(batch_start + batch_size, total_agents)
                batch = opamp_agents[batch_start:batch_end]
                
                logger.info(f"Processing batch {batch_start//batch_size + 1}/{(total_agents + batch_size - 1)//batch_size} ({len(batch)} agents)")
                
                # Process batch
                batch_result = await self._sync_batch(batch)
                
                agents_processed += batch_result['processed']
                agents_updated += batch_result['updated']
                configs_versioned += batch_result['configs_versioned']
                opamp_instance_ids.extend(batch_result['instance_ids'])
                errors.extend(batch_result['errors'])
            
            # Mark disconnected agents
            logger.info("Marking disconnected agents...")
            disconnected_count = await self.agent_repo.mark_disconnected(opamp_instance_ids)
            if disconnected_count > 0:
                logger.info(f"Marked {disconnected_count} agent(s) as disconnected")
            
            logger.info(
                f"Sync completed: {agents_processed} processed, "
                f"{agents_updated} updated, {configs_versioned} configs versioned"
            )
            
            return SyncResponse(
                success=True,
                message=f"Synchronized {agents_processed} agents",
                agents_processed=agents_processed,
                agents_updated=agents_updated,
                configs_versioned=configs_versioned,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Failed to sync agents: {e}", exc_info=True)
            return SyncResponse(
                success=False,
                message=f"Sync failed: {str(e)}",
                agents_processed=agents_processed,
                agents_updated=agents_updated,
                configs_versioned=configs_versioned,
                errors=[str(e)]
            )
    
    async def _sync_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronize a batch of agents efficiently.
        
        Uses bulk operations to minimize database round-trips:
        1. Extract all data from batch
        2. Bulk upsert agents
        3. Bulk create health records
        4. Bulk process configs (fetch existing configs in one query)
        5. Bulk create pipeline health
        6. Single commit per batch
        
        Args:
            batch: List of agent data from OpAMP
            
        Returns:
            Dict with batch processing results
        """
        instance_ids = []
        agents_data = []
        health_data_list = []
        pipeline_health_data_list = []
        config_creates = []
        errors = []
        
        # Phase 1: Extract and prepare all data
        for agent_data in batch:
            try:
                instance_id = agent_data.get("instanceId")
                if not instance_id:
                    continue
                
                instance_ids.append(instance_id)
                status = agent_data.get("status", {})
                started_at_str = agent_data.get("startedAt")
                
                # Parse started_at
                started_at = None
                if started_at_str:
                    try:
                        started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                    except:
                        pass
                
                # Extract attributes
                attributes = self.extract_agent_attributes(status)
                
                # Extract health
                health_data = status.get("health", {})
                healthy = health_data.get("healthy", False)
                health_status = health_data.get("status", "UNKNOWN")
                status_time_unix_nano = health_data.get("status_time_unix_nano")
                
                # Prepare agent data
                agent_dict = {
                    "instance_id": instance_id,
                    "host_name": attributes.get("host_name"),
                    "os_type": attributes.get("os_type"),
                    "os_description": attributes.get("os_description"),
                    "service_name": attributes.get("service_name"),
                    "service_version": attributes.get("service_version"),
                    "host_arch": attributes.get("host_arch"),
                    "healthy": healthy,
                    "is_connected": True,
                    "started_at": started_at
                }
                agents_data.append(agent_dict)
                
                # Prepare health data
                health_create = AgentHealthCreate(
                    instance_id=instance_id,
                    healthy=healthy,
                    status=health_status,
                    status_time_unix_nano=status_time_unix_nano
                )
                health_data_list.append(health_create)
                
                # Extract pipeline health
                component_health_map = health_data.get("component_health_map", {})
                if component_health_map:
                    pipeline_healths = self._extract_pipeline_health(instance_id, component_health_map)
                    pipeline_health_data_list.extend(pipeline_healths)
                
            except Exception as e:
                logger.error(f"Error preparing agent data: {e}")
                errors.append(str(e))
        
        if not instance_ids:
            return {
                'processed': 0,
                'updated': 0,
                'configs_versioned': 0,
                'instance_ids': [],
                'errors': errors
            }
        
        # Phase 2: Bulk upsert agents
        logger.debug(f"Bulk upserting {len(agents_data)} agents")
        agents = await self.agent_repo.bulk_upsert(agents_data)
        
        # Phase 3: Bulk create health records
        logger.debug(f"Bulk creating {len(health_data_list)} health records")
        await self.health_repo.bulk_create(health_data_list)
        
        # Phase 4: Bulk delete and create pipeline health
        if pipeline_health_data_list:
            logger.debug(f"Deleting old pipeline health for {len(instance_ids)} agents")
            await self.pipeline_health_repo.bulk_delete_by_instance_ids(instance_ids)
            
            logger.debug(f"Bulk creating {len(pipeline_health_data_list)} pipeline health records")
            await self.pipeline_health_repo.bulk_create(pipeline_health_data_list)
        
        # Phase 5: Process configs - fetch all latest configs in one query
        logger.debug(f"Fetching latest configs for {len(instance_ids)} agents")
        latest_configs = await self.config_repo.get_latest_configs_bulk(instance_ids)
        
        configs_versioned = 0
        agents_to_update = []
        
        for i, agent_data in enumerate(batch):
            instance_id = agent_data.get("instanceId")
            if not instance_id:
                continue
            
            effective_config = agent_data.get("effectiveConfig", "")
            
            if effective_config:
                effective_config = self.clean_config(effective_config)
                config_hash = self.compute_config_hash(effective_config)
                latest_config = latest_configs.get(instance_id)
                
                should_version = False
                if not latest_config:
                    should_version = True
                else:
                    stored_config_cleaned = self.clean_config(latest_config.effective_config)
                    stored_config_hash = self.compute_config_hash(stored_config_cleaned)
                    
                    if stored_config_hash != config_hash:
                        should_version = True
                
                if should_version:
                    # Prepare config for bulk creation later
                    next_version = (latest_config.version + 1) if latest_config else 1
                    
                    config_create = AgentConfigCreate(
                        instance_id=instance_id,
                        version=next_version,
                        effective_config=effective_config,
                        config_hash=config_hash,
                        source="SYNC_JOB"
                    )
                    config_creates.append(config_create)
                    configs_versioned += 1
                    
                    # Mark agent for status update
                    agent = next((a for a in agents if a.instance_id == instance_id), None)
                    if agent:
                        agent.alert_config = True
                        agent.status_sync = "OUT_OF_SYNC"
                        agents_to_update.append(agent)
                else:
                    # Config unchanged
                    agent = next((a for a in agents if a.instance_id == instance_id), None)
                    if agent and agent.alert_config:
                        agent.status_sync = "IN_SYNC"
                        agent.alert_config = False
                        agents_to_update.append(agent)
        
        # Phase 6: Bulk create new config versions
        if config_creates:
            logger.debug(f"Bulk creating {len(config_creates)} new config versions")
            await self.config_repo.bulk_create(config_creates)
        
        # Phase 7: Commit all changes
        await self.db.commit()
        
        return {
            'processed': len(instance_ids),
            'updated': len(agents),
            'configs_versioned': configs_versioned,
            'instance_ids': instance_ids,
            'errors': errors
        }
    
    def _extract_pipeline_health(
        self, 
        instance_id: str, 
        component_health_map: Dict[str, Any]
    ) -> List[AgentPipelineHealthCreate]:
        """
        Extract pipeline health data for bulk creation.
        
        Args:
            instance_id: Agent instance ID
            component_health_map: Component health map from OpAMP
            
        Returns:
            List of AgentPipelineHealthCreate objects
        """
        pipeline_healths = []
        
        for component_key, component_data in component_health_map.items():
            if component_key == "extensions":
                # Extensions group
                pipeline_healths.append(
                    self._create_pipeline_health_obj(
                        instance_id=instance_id,
                        component_type="extensions",
                        component_name="extensions",
                        parent_pipeline=None,
                        component_data=component_data
                    )
                )
                
                # Individual extensions
                ext_health_map = component_data.get("component_health_map", {})
                for ext_key, ext_data in ext_health_map.items():
                    ext_name = ext_key.replace("extension:", "", 1)
                    pipeline_healths.append(
                        self._create_pipeline_health_obj(
                            instance_id=instance_id,
                            component_type="extension",
                            component_name=ext_name,
                            parent_pipeline="extensions",
                            component_data=ext_data
                        )
                    )
            
            elif component_key.startswith("pipeline:"):
                pipeline_name = component_key.replace("pipeline:", "", 1)
                
                # Pipeline itself
                pipeline_healths.append(
                    self._create_pipeline_health_obj(
                        instance_id=instance_id,
                        component_type="pipeline",
                        component_name=pipeline_name,
                        parent_pipeline=None,
                        component_data=component_data
                    )
                )
                
                # Pipeline sub-components
                pipeline_health_map = component_data.get("component_health_map", {})
                for sub_key, sub_data in pipeline_health_map.items():
                    if ":" in sub_key:
                        comp_type, comp_name = sub_key.split(":", 1)
                        pipeline_healths.append(
                            self._create_pipeline_health_obj(
                                instance_id=instance_id,
                                component_type=comp_type,
                                component_name=comp_name,
                                parent_pipeline=pipeline_name,
                                component_data=sub_data
                            )
                        )
        
        return pipeline_healths
    
    def _create_pipeline_health_obj(
        self,
        instance_id: str,
        component_type: str,
        component_name: str,
        parent_pipeline: Optional[str],
        component_data: Dict[str, Any]
    ) -> AgentPipelineHealthCreate:
        """Create a pipeline health object for bulk insertion."""
        return AgentPipelineHealthCreate(
            instance_id=instance_id,
            component_type=component_type,
            component_name=component_name,
            parent_pipeline=parent_pipeline,
            healthy=component_data.get("healthy", False),
            status=component_data.get("status", "UNKNOWN"),
            status_time_unix_nano=component_data.get("status_time_unix_nano"),
            last_error=component_data.get("last_error")
        )
    
    async def send_config_to_opamp(
        self, 
        instance_id: str, 
        config: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send new configuration to OpAMP server for a specific agent.
        
        Args:
            instance_id: Agent instance ID
            config: YAML configuration content
            user_id: ID of user making the change (optional)
            
        Returns:
            Dict with operation results
        """
        url = f"{self.opamp_url}/save_config/json"
        
        # Clean trailing blank lines from config
        config_original = config
        config = self.clean_config(config)
        
        logger.info(f"[API] Sending config to OpAMP - Original len: {len(config_original)}, Cleaned len: {len(config)}, Last 20 hex: {config[-20:].encode().hex() if len(config) >= 20 else config.encode().hex()}")
        
        try:
            # Send to OpAMP
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data={
                        "instanceid": instance_id,
                        "config": config
                    }
                )
                response.raise_for_status()
                opamp_response = response.json()
            
            # If successful, create new config version
            if opamp_response.get("success"):
                config_hash = self.compute_config_hash(config)
                next_version = await self.config_repo.get_next_version(instance_id)
                
                config_create = AgentConfigCreate(
                    instance_id=instance_id,
                    version=next_version,
                    effective_config=config,
                    config_hash=config_hash,
                    source="API_UPDATE" if user_id else "MANUAL_UPDATE",
                    updated_by_user_id=user_id
                )
                new_config = await self.config_repo.create(config_create)
                
                # Update agent status
                agent = await self.agent_repo.get_by_instance_id(instance_id)
                if agent:
                    agent.status_sync = "IN_SYNC"
                    agent.alert_config = False
                    await self.db.commit()
                
                return {
                    "success": True,
                    "message": opamp_response.get("message", "Config updated successfully"),
                    "instance_id": instance_id,
                    "version": new_config.version,
                    "status_ready": opamp_response.get("statusReady", False)
                }
            else:
                return {
                    "success": False,
                    "message": opamp_response.get("message", "Failed to update config"),
                    "instance_id": instance_id,
                    "version": 0,
                    "status_ready": False
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to send config to OpAMP: {e}")
            raise ValueError(f"Failed to communicate with OpAMP server: {str(e)}")
