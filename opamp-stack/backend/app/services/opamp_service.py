"""
Service layer for OpAMP synchronization and integration.
Handles communication with OpAMP server and data synchronization.

PERFORMANCE OPTIMIZATION for 10k+ agents:
- Singleton httpx client (connection pooling)
- Delta sync via /agents/status (skip sync when no changes)
- In-memory config hash cache (avoid DB reads for unchanged configs)
- Dict lookups instead of linear search
- Cleanup runs once after all batches, not per-batch
- Repositories flush only; single commit per batch from service layer
- Pipeline health bulk upsert (single DELETE+INSERT per batch)
"""
import asyncio
import hashlib
import json
import logging
import time
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


# ---------------------------------------------------------------------------
# Module-level singleton httpx client (2.1)
# Created lazily, reused across all OpAMPService instances.
# ---------------------------------------------------------------------------
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Return the module-level singleton httpx.AsyncClient."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=settings.OPAMP_HTTP_TIMEOUT,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )
    return _http_client


async def close_http_client() -> None:
    """Close the singleton httpx client (call on app shutdown)."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


# ---------------------------------------------------------------------------
# In-memory config hash cache (2.7)
# Maps instance_id -> config_hash (SHA256 hex digest)
# Populated on first sync, updated when config changes.
# ---------------------------------------------------------------------------
_config_hash_cache: Dict[str, str] = {}


class OpAMPService:
    """Service for OpAMP server integration."""

    # Class-level delta sync state (2.5)
    _last_known_modified_nano: int = 0

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_repo = AgentRepository(db)
        self.health_repo = AgentHealthRepository(db)
        self.config_repo = AgentConfigRepository(db)
        self.pipeline_health_repo = AgentPipelineHealthRepository(db)
        self.opamp_url = settings.OPAMP_SERVER_URL

    # ------------------------------------------------------------------
    # HTTP helpers — use singleton client (2.1)
    # ------------------------------------------------------------------

    async def fetch_agents_from_opamp(self) -> List[Dict[str, Any]]:
        """Fetch all agents from OpAMP server."""
        url = f"{self.opamp_url}/agents/full"

        try:
            client = await get_http_client()
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch agents from OpAMP: {e}")
            raise

    async def fetch_single_agent_from_opamp(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single agent from OpAMP server using the individual endpoint (2.10)."""
        url = f"{self.opamp_url}/agent/full"

        try:
            client = await get_http_client()
            response = await client.get(url, params={"instanceid": instance_id})

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch agent {instance_id} from OpAMP: {e}")
            raise

    async def fetch_agents_status(self) -> Dict[str, Any]:
        """Fetch lightweight status (count + lastModifiedNano) for delta sync (2.5)."""
        url = f"{self.opamp_url}/agents/status"

        try:
            client = await get_http_client()
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch agents status from OpAMP: {e}")
            raise

    # ------------------------------------------------------------------
    # Pure helpers
    # ------------------------------------------------------------------

    def extract_agent_attributes(self, status: Dict) -> Dict[str, Any]:
        """Extract agent attributes from OpAMP status."""
        attributes = {}

        agent_desc = status.get("agent_description", {})

        id_attrs = agent_desc.get("identifying_attributes", [])
        for attr in id_attrs:
            key = attr.get("key")
            value_obj = attr.get("value", {}).get("Value", {})

            if key == "service.name":
                attributes["service_name"] = value_obj.get("StringValue")
            elif key == "service.version":
                attributes["service_version"] = value_obj.get("StringValue")

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
        """Remove trailing blank lines and newlines from configuration string."""
        if not config:
            return config
        return config.rstrip('\n\r ')

    # ------------------------------------------------------------------
    # Health cleanup (runs ONCE after all batches — 2.2)
    # ------------------------------------------------------------------

    async def _cleanup_old_health_records(self) -> int:
        """Cleanup old health records for all agents, keeping only the last N per agent."""
        from sqlalchemy import text

        keep = settings.OPAMP_HEALTH_CLEANUP_KEEP
        query = text("""
            DELETE FROM agent_health
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY instance_id
                               ORDER BY created_at DESC
                           ) AS row_num
                    FROM agent_health
                ) AS ranked
                WHERE row_num <= :keep
            )
        """)

        result = await self.db.execute(query, {"keep": keep})
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old health records")

        return deleted_count

    # ------------------------------------------------------------------
    # Single agent sync (used by manual sync endpoint)
    # ------------------------------------------------------------------

    async def sync_agent(
        self,
        agent_data: Dict[str, Any],
        source: str = "SYNC_JOB"
    ) -> Dict[str, Any]:
        """Synchronize a single agent from OpAMP data."""
        instance_id = agent_data.get("instanceId")
        status = agent_data.get("status", {})
        effective_config = agent_data.get("effectiveConfig", "")
        started_at_str = agent_data.get("startedAt")

        # Parse started_at
        started_at = None
        if started_at_str:
            try:
                started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            except Exception:
                pass

        # Extract attributes
        attributes = self.extract_agent_attributes(status)
        host_name = attributes.get("host_name")

        # Extract health
        health_data = status.get("health", {})
        healthy = health_data.get("healthy", False)
        health_status = health_data.get("status", "UNKNOWN")
        status_time_unix_nano = health_data.get("status_time_unix_nano")
        start_time_unix_nano = health_data.get("start_time_unix_nano")

        # Upsert agent
        agent_dict = {
            "instance_id": instance_id,
            "host_name": host_name,
            "os_type": attributes.get("os_type"),
            "os_description": attributes.get("os_description"),
            "service_name": attributes.get("service_name"),
            "service_version": attributes.get("service_version"),
            "host_arch": attributes.get("host_arch"),
            "healthy": healthy,
            "is_connected": True,
            "started_at": started_at
        }

        if settings.USE_HOSTNAME_AS_SYNC_KEY and host_name:
            logger.debug(f"Using host_name '{host_name}' as sync key for instance_id '{instance_id}'")
            agent = await self.agent_repo.upsert_by_hostname(instance_id, host_name, agent_dict)
        else:
            agent = await self.agent_repo.upsert(instance_id, agent_dict)

        # Create health record
        health_create = AgentHealthCreate(
            instance_id=instance_id,
            healthy=healthy,
            status=health_status,
            status_time_unix_nano=status_time_unix_nano,
            start_time_unix_nano=start_time_unix_nano
        )
        await self.health_repo.create(health_create)

        # Extract and save pipeline/component health
        component_health_map = health_data.get("component_health_map", {})
        if component_health_map:
            await self.pipeline_health_repo.delete_all_by_instance_id(instance_id)

            for component_key, component_data in component_health_map.items():
                if component_key == "extensions":
                    await self._save_component_health_async(
                        instance_id=instance_id,
                        component_type="extensions",
                        component_name="extensions",
                        parent_pipeline=None,
                        component_data=component_data
                    )

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
                    pipeline_name = component_key.replace("pipeline:", "", 1)

                    await self._save_component_health_async(
                        instance_id=instance_id,
                        component_type="pipeline",
                        component_name=pipeline_name,
                        parent_pipeline=None,
                        component_data=component_data
                    )

                    pipeline_health_map = component_data.get("component_health_map", {})
                    for sub_key, sub_data in pipeline_health_map.items():
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
            effective_config = self.clean_config(effective_config)
            config_hash = self.compute_config_hash(effective_config)
            latest_config = await self.config_repo.get_latest_by_instance_id(instance_id)

            should_version = False
            if not latest_config:
                should_version = True
            else:
                stored_config_cleaned = self.clean_config(latest_config.effective_config)
                stored_config_hash = self.compute_config_hash(stored_config_cleaned)
                if stored_config_hash != config_hash:
                    should_version = True

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
                agent.alert_config = True
                agent.status_sync = "OUT_OF_SYNC"
                config_versioned = True
                # Update cache
                _config_hash_cache[instance_id] = config_hash
            else:
                if agent.alert_config:
                    agent.status_sync = "IN_SYNC"
                    agent.alert_config = False

        await self.db.commit()

        return {
            "instance_id": instance_id,
            "updated": True,
            "config_versioned": config_versioned
        }

    async def _save_component_health_async(
        self,
        instance_id: str,
        component_type: str,
        component_name: str,
        parent_pipeline: Optional[str],
        component_data: Dict[str, Any]
    ) -> None:
        """Helper method to save component health data."""
        health_create = AgentPipelineHealthCreate(
            instance_id=instance_id,
            component_type=component_type,
            component_name=component_name,
            parent_pipeline=parent_pipeline,
            healthy=component_data.get("healthy", False),
            status=component_data.get("status", "UNKNOWN"),
            status_time_unix_nano=component_data.get("status_time_unix_nano"),
            last_error=component_data.get("last_error")
        )
        await self.pipeline_health_repo.create(health_create)

    async def sync_single_agent(self, instance_id: str) -> Dict[str, Any]:
        """Synchronize a single agent by instance_id using the individual endpoint."""
        try:
            logger.info(f"Fetching agent {instance_id} from OpAMP server...")
            agent_data = await self.fetch_single_agent_from_opamp(instance_id)

            if not agent_data:
                logger.warning(f"Agent {instance_id} not found in OpAMP server")
                return {
                    "success": False,
                    "message": f"Agent {instance_id} not found in OpAMP server",
                    "instance_id": instance_id,
                    "updated": False,
                    "config_versioned": False
                }

            logger.info(f"Synchronizing agent {instance_id}...")
            result = await self.sync_agent(agent_data, source="MANUAL_SYNC")

            logger.info(f"Agent {instance_id} synchronized successfully")
            return {
                "success": True,
                "message": f"Agent {instance_id} synchronized successfully",
                "instance_id": instance_id,
                "updated": result.get("updated", False),
                "config_versioned": result.get("config_versioned", False)
            }

        except Exception as e:
            logger.error(f"Failed to sync agent {instance_id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to sync agent: {str(e)}",
                "instance_id": instance_id,
                "updated": False,
                "config_versioned": False
            }

    # ------------------------------------------------------------------
    # Full sync — the main periodic sync method
    # ------------------------------------------------------------------

    async def sync_all_agents(self) -> SyncResponse:
        """
        Synchronize all agents from OpAMP server.

        Improvements over original:
        - Delta sync: checks /agents/status first, skips if no changes (2.5)
        - Cleanup runs ONCE after all batches (2.2)
        - Dict lookup for agent matching (2.3)
        - Config hash cache avoids DB reads (2.7)
        - Single commit per batch (2.8)
        - Pipeline health bulk upsert (2.6)
        """
        errors: List[str] = []
        agents_processed = 0
        agents_updated = 0
        configs_versioned = 0

        try:
            # --- Delta sync check (2.5) ---
            if settings.OPAMP_DELTA_SYNC_ENABLED:
                status = await self.fetch_agents_status()
                remote_modified = status.get("lastModifiedNano", 0)
                remote_count = status.get("count", 0)

                if remote_modified == OpAMPService._last_known_modified_nano and remote_modified != 0:
                    logger.info(
                        f"Delta sync: no changes detected "
                        f"(lastModifiedNano={remote_modified}, count={remote_count}). Skipping full sync."
                    )
                    return SyncResponse(
                        success=True,
                        message="No changes detected, sync skipped",
                        agents_processed=0,
                        agents_updated=0,
                        configs_versioned=0,
                        errors=[]
                    )

                logger.info(
                    f"Delta sync: changes detected "
                    f"(prev={OpAMPService._last_known_modified_nano}, "
                    f"new={remote_modified}, count={remote_count})"
                )

            # Fetch all agents from OpAMP
            logger.info("Fetching agents from OpAMP server...")
            sync_start = time.monotonic()
            opamp_agents = await self.fetch_agents_from_opamp()

            if opamp_agents is None:
                opamp_agents = []

            total_agents = len(opamp_agents)
            logger.info(f"Received {total_agents} agents from OpAMP server")

            # Track instance IDs from OpAMP
            opamp_instance_ids: List[str] = []

            # Process in batches
            batch_size = settings.OPAMP_SYNC_BATCH_SIZE

            for batch_start in range(0, total_agents, batch_size):
                batch_end = min(batch_start + batch_size, total_agents)
                batch = opamp_agents[batch_start:batch_end]

                logger.info(
                    f"Processing batch {batch_start // batch_size + 1}/"
                    f"{(total_agents + batch_size - 1) // batch_size} ({len(batch)} agents)"
                )

                batch_result = await self._sync_batch(batch)

                agents_processed += batch_result['processed']
                agents_updated += batch_result['updated']
                configs_versioned += batch_result['configs_versioned']
                opamp_instance_ids.extend(batch_result['instance_ids'])
                errors.extend(batch_result['errors'])

            # --- Cleanup ONCE after all batches (2.2) ---
            logger.debug("Cleaning up old health records (post-sync)")
            await self._cleanup_old_health_records()
            await self.db.commit()

            # Mark disconnected agents
            logger.info("Marking disconnected agents...")
            disconnected_count = await self.agent_repo.mark_disconnected(opamp_instance_ids)
            if disconnected_count > 0:
                logger.info(f"Marked {disconnected_count} agent(s) as disconnected")

            # Update delta sync timestamp (2.5)
            if settings.OPAMP_DELTA_SYNC_ENABLED:
                try:
                    status_after = await self.fetch_agents_status()
                    OpAMPService._last_known_modified_nano = status_after.get("lastModifiedNano", 0)
                except Exception:
                    pass  # Non-critical; next sync will just do a full sync

            elapsed = time.monotonic() - sync_start
            logger.info(
                f"Sync completed in {elapsed:.1f}s: {agents_processed} processed, "
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

    # ------------------------------------------------------------------
    # Batch sync
    # ------------------------------------------------------------------

    async def _sync_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronize a batch of agents efficiently.

        Changes from original:
        - Dict lookup for agent matching (2.3)
        - Config hash cache (2.7)
        - Pipeline health bulk upsert (2.6)
        - No cleanup per batch (moved to caller — 2.2)
        - Single commit at end (2.8)
        """
        instance_ids: List[str] = []
        agents_data: List[dict] = []
        health_data_list: List[AgentHealthCreate] = []
        pipeline_health_data_list: List[AgentPipelineHealthCreate] = []
        config_creates: List[AgentConfigCreate] = []
        errors: List[str] = []

        # Phase 1: Extract and prepare all data
        for agent_data in batch:
            try:
                instance_id = agent_data.get("instanceId")
                if not instance_id:
                    continue

                instance_ids.append(instance_id)
                status = agent_data.get("status", {})
                started_at_str = agent_data.get("startedAt")

                started_at = None
                if started_at_str:
                    try:
                        started_at = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                attributes = self.extract_agent_attributes(status)

                health_data = status.get("health", {})
                healthy = health_data.get("healthy", False)
                health_status = health_data.get("status", "UNKNOWN")
                status_time_unix_nano = health_data.get("status_time_unix_nano")
                start_time_unix_nano = health_data.get("start_time_unix_nano")

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

                health_create = AgentHealthCreate(
                    instance_id=instance_id,
                    healthy=healthy,
                    status=health_status,
                    status_time_unix_nano=status_time_unix_nano,
                    start_time_unix_nano=start_time_unix_nano
                )
                health_data_list.append(health_create)

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

        # Build dict for O(1) lookup (2.3)
        agents_by_id: Dict[str, Any] = {a.instance_id: a for a in agents}

        # Phase 3: Bulk create health records (no commit — 2.8)
        logger.debug(f"Bulk creating {len(health_data_list)} health records")
        await self.health_repo.bulk_create(health_data_list)

        # Phase 4: Pipeline health bulk upsert (2.6 — single DELETE+INSERT, no commit)
        if pipeline_health_data_list:
            logger.debug(f"Bulk upserting {len(pipeline_health_data_list)} pipeline health records")
            await self.pipeline_health_repo.bulk_upsert(pipeline_health_data_list)

        # Phase 5: Process configs with in-memory hash cache (2.7)
        configs_versioned = 0

        # Determine which agents need DB lookup for config
        # (those not in cache or with no cache entry)
        ids_needing_db_lookup: List[str] = []
        for agent_data in batch:
            instance_id = agent_data.get("instanceId")
            if not instance_id:
                continue
            effective_config = agent_data.get("effectiveConfig", "")
            if effective_config:
                effective_config = self.clean_config(effective_config)
                config_hash = self.compute_config_hash(effective_config)
                cached_hash = _config_hash_cache.get(instance_id)

                if cached_hash == config_hash:
                    # Config unchanged — check if we need to clear alert
                    agent = agents_by_id.get(instance_id)
                    if agent and agent.alert_config:
                        agent.status_sync = "IN_SYNC"
                        agent.alert_config = False
                    continue

                # Cache miss or hash differs — need DB lookup
                ids_needing_db_lookup.append(instance_id)

        # Fetch latest configs from DB only for agents that need it
        latest_configs: Dict[str, Any] = {}
        if ids_needing_db_lookup:
            logger.debug(f"Fetching latest configs for {len(ids_needing_db_lookup)} agents (cache miss)")
            latest_configs = await self.config_repo.get_latest_configs_bulk(ids_needing_db_lookup)

        for agent_data in batch:
            instance_id = agent_data.get("instanceId")
            if not instance_id or instance_id not in ids_needing_db_lookup:
                continue

            effective_config = agent_data.get("effectiveConfig", "")
            if not effective_config:
                continue

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

                agent = agents_by_id.get(instance_id)
                if agent:
                    agent.alert_config = True
                    agent.status_sync = "OUT_OF_SYNC"

                # Update cache with new hash
                _config_hash_cache[instance_id] = config_hash
            else:
                # Config unchanged — update cache and clear alert
                _config_hash_cache[instance_id] = config_hash
                agent = agents_by_id.get(instance_id)
                if agent and agent.alert_config:
                    agent.status_sync = "IN_SYNC"
                    agent.alert_config = False

        # Phase 6: Bulk create new config versions (no commit — 2.8)
        if config_creates:
            logger.debug(f"Bulk creating {len(config_creates)} new config versions")
            await self.config_repo.bulk_create(config_creates)

        # Phase 7: Single commit for entire batch (2.8)
        await self.db.commit()

        return {
            'processed': len(instance_ids),
            'updated': len(agents),
            'configs_versioned': configs_versioned,
            'instance_ids': instance_ids,
            'errors': errors
        }

    # ------------------------------------------------------------------
    # Pipeline health extraction (pure, no I/O)
    # ------------------------------------------------------------------

    def _extract_pipeline_health(
        self,
        instance_id: str,
        component_health_map: Dict[str, Any]
    ) -> List[AgentPipelineHealthCreate]:
        """Extract pipeline health data for bulk creation."""
        pipeline_healths = []

        for component_key, component_data in component_health_map.items():
            if component_key == "extensions":
                pipeline_healths.append(
                    self._create_pipeline_health_obj(
                        instance_id=instance_id,
                        component_type="extensions",
                        component_name="extensions",
                        parent_pipeline=None,
                        component_data=component_data
                    )
                )

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

                pipeline_healths.append(
                    self._create_pipeline_health_obj(
                        instance_id=instance_id,
                        component_type="pipeline",
                        component_name=pipeline_name,
                        parent_pipeline=None,
                        component_data=component_data
                    )
                )

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

    # ------------------------------------------------------------------
    # Config push
    # ------------------------------------------------------------------

    async def send_config_to_opamp(
        self,
        instance_id: str,
        config: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send new configuration to OpAMP server for a specific agent."""
        url = f"{self.opamp_url}/save_config/json"

        config = self.clean_config(config)

        try:
            client = await get_http_client()
            response = await client.post(
                url,
                data={
                    "instanceid": instance_id,
                    "config": config
                }
            )
            response.raise_for_status()
            opamp_response = response.json()

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

                # Update cache
                _config_hash_cache[instance_id] = config_hash

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
