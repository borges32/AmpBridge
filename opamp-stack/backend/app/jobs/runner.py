"""Background job runner with concurrency control."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from app.db.session import get_db_session
from app.db.models import Job, JobRun, JobStatus, JobType
from app.core.services.job_service import JobService
from app.core.services.config_service import ConfigService
from app.clients.opamp import opamp_client
from app.settings import settings
from app.telemetry.metrics import (
    JOB_TOTAL, JOB_DURATION, JOB_PROGRESS,
    BULK_APPLY_SUCCESS_TOTAL, BULK_APPLY_FAIL_TOTAL,
    increment_counter, set_gauge, track_time
)

logger = logging.getLogger(__name__)


class JobRunner:
    """Background job processor with concurrency control."""
    
    def __init__(self):
        """Initialize job runner."""
        self.running = False
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
        self.active_jobs: Dict[str, asyncio.Task] = {}
        self.job_progress: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the job runner."""
        if self.running:
            return
        
        self.running = True
        logger.info("Job runner started")
        
        # Start the main processing loop
        asyncio.create_task(self._process_jobs())
    
    async def stop(self):
        """Stop the job runner and wait for active jobs to complete."""
        self.running = False
        
        # Cancel all active jobs
        for job_id, task in self.active_jobs.items():
            task.cancel()
        
        # Wait for cancellation
        if self.active_jobs:
            await asyncio.gather(*self.active_jobs.values(), return_exceptions=True)
        
        logger.info("Job runner stopped")
    
    async def _process_jobs(self):
        """Main job processing loop."""
        while self.running:
            try:
                with get_db_session() as db:
                    job_service = JobService(db)
                    pending_jobs = job_service.get_pending_jobs(limit=10)
                
                for job in pending_jobs:
                    if job.id not in self.active_jobs:
                        # Start job processing
                        task = asyncio.create_task(self._process_job(job.id))
                        self.active_jobs[job.id] = task
                        
                        # Clean up completed tasks
                        task.add_done_callback(
                            lambda t, job_id=job.id: self.active_jobs.pop(job_id, None)
                        )
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in job processing loop: {e}")
                await asyncio.sleep(10)
    
    async def _process_job(self, job_id: str):
        """Process a single job.
        
        Args:
            job_id: Job ID to process
        """
        async with self.semaphore:
            start_time = datetime.utcnow()
            
            try:
                with get_db_session() as db:
                    job_service = JobService(db)
                    job = job_service.get_job_by_id(job_id)
                    
                    if not job or job.status != JobStatus.PENDING:
                        return
                    
                    # Start the job
                    if not job_service.start_job(job_id):
                        return
                    
                    logger.info(f"Processing job {job_id} of type {job.type}")
                    
                    # Initialize progress tracking
                    self.job_progress[job_id] = {
                        "total": job.total_agents,
                        "completed": 0,
                        "successful": 0,
                        "failed": 0,
                        "progress": 0
                    }
                    
                    # Process based on job type
                    success = False
                    error_message = None
                    
                    if job.type == JobType.BULK_CONFIG_UPDATE.value:
                        success, error_message = await self._process_bulk_config_job(job_id, job)
                    else:
                        error_message = f"Unknown job type: {job.type}"
                    
                    # Complete the job
                    job_service.complete_job(job_id, error_message)
                    
                    # Update metrics
                    duration = (datetime.utcnow() - start_time).total_seconds()
                    status = "completed" if success else "failed"
                    
                    increment_counter(JOB_TOTAL, {
                        "type": job.type,
                        "status": status
                    })
                    
                    JOB_DURATION.labels(
                        type=job.type,
                        status=status
                    ).observe(duration)
                    
                    # Clear progress tracking
                    self.job_progress.pop(job_id, None)
                    
                    logger.info(f"Job {job_id} {status} in {duration:.2f}s")
                    
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}")
                
                # Mark job as failed
                with get_db_session() as db:
                    job_service = JobService(db)
                    job_service.complete_job(job_id, str(e))
                
                # Clear progress tracking
                self.job_progress.pop(job_id, None)
    
    async def _process_bulk_config_job(self, job_id: str, job: Job) -> tuple[bool, Optional[str]]:
        """Process a bulk configuration update job.
        
        Args:
            job_id: Job ID
            job: Job instance
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            payload = job.payload_json
            config_yaml = payload.get('config_yaml')
            agent_ids = payload.get('agent_ids', [])
            applied_by = payload.get('applied_by', 'system')
            
            if not config_yaml:
                return False, "No configuration provided"
            
            if not agent_ids:
                return False, "No agents specified"
            
            with get_db_session() as db:
                job_service = JobService(db)
                config_service = ConfigService(db)
                
                # Get job runs
                job_runs = job_service.get_job_runs(job_id)
                
                # Process each agent
                successful = 0
                failed = 0
                
                # Use semaphore to limit concurrent config applications
                config_semaphore = asyncio.Semaphore(min(10, settings.max_concurrent_jobs))
                
                async def apply_config_to_agent(job_run: JobRun):
                    nonlocal successful, failed
                    
                    async with config_semaphore:
                        try:
                            # Start job run
                            job_service.start_job_run(job_run.id)
                            
                            # Apply configuration
                            await config_service.apply_config(
                                job_run.agent_id,
                                config_yaml,
                                applied_by
                            )
                            
                            # Mark as successful
                            job_service.complete_job_run(job_run.id, True)
                            successful += 1
                            
                            increment_counter(BULK_APPLY_SUCCESS_TOTAL)
                            
                        except Exception as e:
                            logger.error(f"Failed to apply config to agent {job_run.agent_id}: {e}")
                            
                            # Mark as failed
                            job_service.complete_job_run(job_run.id, False, str(e))
                            failed += 1
                            
                            increment_counter(BULK_APPLY_FAIL_TOTAL)
                        
                        finally:
                            # Update progress
                            completed = successful + failed
                            progress = int((completed / len(job_runs)) * 100) if job_runs else 100
                            
                            job_service.update_job_progress(job_id, progress, successful, failed)
                            
                            # Update progress tracking
                            if job_id in self.job_progress:
                                self.job_progress[job_id].update({
                                    "completed": completed,
                                    "successful": successful,
                                    "failed": failed,
                                    "progress": progress
                                })
                            
                            # Update metrics
                            set_gauge(JOB_PROGRESS, progress, {
                                "job_id": job_id,
                                "type": job.type
                            })
                
                # Process all job runs concurrently
                tasks = [apply_config_to_agent(job_run) for job_run in job_runs]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Return success if at least one agent succeeded
                return successful > 0, None if successful > 0 else "All agents failed"
                
        except Exception as e:
            logger.error(f"Error in bulk config job {job_id}: {e}")
            return False, str(e)
    
    def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Progress information or None if not found
        """
        return self.job_progress.get(job_id)
    
    def get_active_jobs(self) -> List[str]:
        """Get list of active job IDs.
        
        Returns:
            List of active job IDs
        """
        return list(self.active_jobs.keys())


# Global job runner instance
job_runner = JobRunner()