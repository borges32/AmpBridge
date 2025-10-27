"""Job service for managing background jobs."""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.db.models import Job, JobRun, JobStatus, JobType
from app.core.utils.pagination import PaginationParams, paginate_query

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing background jobs."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def create_job(
        self,
        job_type: JobType,
        payload: Dict[str, Any],
        created_by: str,
        agent_ids: Optional[List[str]] = None
    ) -> Job:
        """Create a new background job.
        
        Args:
            job_type: Type of job
            payload: Job payload data
            created_by: Username who created the job
            agent_ids: Optional list of agent IDs for bulk jobs
            
        Returns:
            Created job
        """
        job_id = str(uuid.uuid4())
        
        job = Job(
            id=job_id,
            type=job_type.value,
            payload_json=payload,
            status=JobStatus.PENDING,
            created_by=created_by,
            total_agents=len(agent_ids) if agent_ids else 0,
            created_at=datetime.utcnow()
        )
        
        self.db.add(job)
        
        # Create job runs for each agent if specified
        if agent_ids:
            for agent_id in agent_ids:
                job_run = JobRun(
                    job_id=job_id,
                    agent_id=agent_id,
                    status=JobStatus.PENDING
                )
                self.db.add(job_run)
        
        self.db.commit()
        
        logger.info(f"Created job {job_id} of type {job_type} for {len(agent_ids or [])} agents")
        return job
    
    def get_jobs(
        self,
        pagination: PaginationParams,
        status_filter: Optional[JobStatus] = None,
        type_filter: Optional[JobType] = None,
        created_by_filter: Optional[str] = None
    ) -> tuple[List[Job], int]:
        """Get paginated list of jobs with filters.
        
        Args:
            pagination: Pagination parameters
            status_filter: Job status filter
            type_filter: Job type filter
            created_by_filter: Created by filter
            
        Returns:
            Tuple of (jobs, total_count)
        """
        query = self.db.query(Job)
        
        # Apply filters
        filters = []
        
        if status_filter:
            filters.append(Job.status == status_filter.value)
        
        if type_filter:
            filters.append(Job.type == type_filter.value)
        
        if created_by_filter:
            filters.append(Job.created_by == created_by_filter)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Order by created_at desc
        query = query.order_by(desc(Job.created_at))
        
        return paginate_query(query, pagination)
    
    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """Get job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job or None if not found
        """
        return self.db.query(Job).filter(Job.id == job_id).first()
    
    def get_pending_jobs(self, limit: int = 10) -> List[Job]:
        """Get pending jobs for processing.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of pending jobs
        """
        return (
            self.db.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .order_by(Job.created_at)
            .limit(limit)
            .all()
        )
    
    def start_job(self, job_id: str) -> bool:
        """Mark job as started.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job was started, False if not found or already started
        """
        job = self.get_job_by_id(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Started job {job_id}")
        return True
    
    def complete_job(self, job_id: str, error_message: Optional[str] = None) -> bool:
        """Mark job as completed or failed.
        
        Args:
            job_id: Job ID
            error_message: Error message if job failed
            
        Returns:
            True if job was completed, False if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return False
        
        job.status = JobStatus.FAILED if error_message else JobStatus.COMPLETED
        job.finished_at = datetime.utcnow()
        job.error_message = error_message
        job.progress = 100
        
        self.db.commit()
        
        status_text = "failed" if error_message else "completed"
        logger.info(f"Job {job_id} {status_text}")
        return True
    
    def update_job_progress(
        self,
        job_id: str,
        progress: int,
        successful_agents: int,
        failed_agents: int
    ) -> bool:
        """Update job progress.
        
        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
            successful_agents: Number of successful agents
            failed_agents: Number of failed agents
            
        Returns:
            True if updated, False if job not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return False
        
        job.progress = max(0, min(100, progress))
        job.successful_agents = successful_agents
        job.failed_agents = failed_agents
        
        self.db.commit()
        return True
    
    def get_job_runs(self, job_id: str) -> List[JobRun]:
        """Get all job runs for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of job runs
        """
        return (
            self.db.query(JobRun)
            .filter(JobRun.job_id == job_id)
            .order_by(JobRun.started_at)
            .all()
        )
    
    def get_pending_job_runs(self, job_id: str, limit: int = 50) -> List[JobRun]:
        """Get pending job runs for a job.
        
        Args:
            job_id: Job ID
            limit: Maximum number of runs to return
            
        Returns:
            List of pending job runs
        """
        return (
            self.db.query(JobRun)
            .filter(
                JobRun.job_id == job_id,
                JobRun.status == JobStatus.PENDING
            )
            .limit(limit)
            .all()
        )
    
    def start_job_run(self, job_run_id: int) -> bool:
        """Mark job run as started.
        
        Args:
            job_run_id: Job run ID
            
        Returns:
            True if started, False if not found or already started
        """
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if not job_run or job_run.status != JobStatus.PENDING:
            return False
        
        job_run.status = JobStatus.RUNNING
        job_run.started_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def complete_job_run(
        self,
        job_run_id: int,
        success: bool,
        error_message: Optional[str] = None
    ) -> bool:
        """Mark job run as completed or failed.
        
        Args:
            job_run_id: Job run ID
            success: Whether the run was successful
            error_message: Error message if failed
            
        Returns:
            True if completed, False if not found
        """
        job_run = self.db.query(JobRun).filter(JobRun.id == job_run_id).first()
        if not job_run:
            return False
        
        job_run.status = JobStatus.COMPLETED if success else JobStatus.FAILED
        job_run.finished_at = datetime.utcnow()
        job_run.error_message = error_message
        
        self.db.commit()
        return True
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job statistics.
        
        Returns:
            Job statistics
        """
        total_jobs = self.db.query(Job).count()
        
        # Count by status
        status_counts = {}
        for status in JobStatus:
            count = self.db.query(Job).filter(Job.status == status.value).count()
            status_counts[status.value] = count
        
        # Count by type
        type_counts = {}
        for job_type in JobType:
            count = self.db.query(Job).filter(Job.type == job_type.value).count()
            type_counts[job_type.value] = count
        
        # Recent jobs
        recent_jobs = (
            self.db.query(Job)
            .order_by(desc(Job.created_at))
            .limit(5)
            .all()
        )
        
        return {
            "total_jobs": total_jobs,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "recent_jobs": [
                {
                    "id": job.id,
                    "type": job.type,
                    "status": job.status,
                    "created_by": job.created_by,
                    "created_at": job.created_at.isoformat(),
                    "progress": job.progress
                }
                for job in recent_jobs
            ]
        }