"""
Background tasks for periodic operations.
Implements scheduled synchronization with OpAMP server.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.opamp_service import OpAMPService

logger = logging.getLogger(__name__)


class BackgroundTasks:
    """Manager for background tasks."""
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def sync_opamp_periodically(self):
        """
        Periodically sync with OpAMP server.
        Runs every OPAMP_SYNC_INTERVAL_SECONDS.
        """
        logger.info("Starting OpAMP sync background task")
        
        while self.running:
            try:
                logger.info("Running OpAMP sync...")
                
                async with AsyncSessionLocal() as db:
                    opamp_service = OpAMPService(db)
                    result = await opamp_service.sync_all_agents()
                    
                    if result.success:
                        logger.info(
                            f"OpAMP sync completed: "
                            f"{result.agents_processed} processed, "
                            f"{result.agents_updated} updated, "
                            f"{result.configs_versioned} configs versioned"
                        )
                    else:
                        logger.error(f"OpAMP sync failed: {result.message}")
                        
            except Exception as e:
                logger.error(f"Error in OpAMP sync task: {e}", exc_info=True)
            
            # Wait for next sync interval
            await asyncio.sleep(settings.OPAMP_SYNC_INTERVAL_SECONDS)
    
    async def start(self):
        """Start all background tasks."""
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self.sync_opamp_periodically())
            logger.info("Background tasks started")
    
    async def stop(self):
        """Stop all background tasks."""
        if self.running:
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            logger.info("Background tasks stopped")


# Global instance
background_tasks = BackgroundTasks()


@asynccontextmanager
async def lifespan_context():
    """
    Context manager for application lifespan.
    Starts background tasks on startup and stops them on shutdown.
    """
    # Startup
    await background_tasks.start()
    yield
    # Shutdown
    await background_tasks.stop()
