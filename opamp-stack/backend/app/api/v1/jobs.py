"""Job management API endpoints."""

from typing import List, Optional, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import CurrentUser, require_permission, get_db
from app.core.services.job_service import JobService
from app.core.utils.pagination import PaginationParams, PaginatedResponse
from app.security.rbac import Permission
from app.db.models import JobStatus, JobType
from app.jobs.sse import create_sse_response

router = APIRouter()


class JobResponse(BaseModel):
    """Job response model."""
    id: str
    type: str
    status: str
    progress: int
    total_agents: int
    successful_agents: int
    failed_agents: int
    created_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class JobRunResponse(BaseModel):
    """Job run response model."""
    id: int
    job_id: str
    agent_id: str
    status: str
    attempt: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/jobs", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_JOBS))],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status: Optional[str] = Query(None, description="Filter by status"),
    job_type: Optional[str] = Query(None, description="Filter by type"),
    created_by: Optional[str] = Query(None, description="Filter by creator")
):
    """List jobs with optional filtering and pagination.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        page: Page number
        size: Page size
        status: Status filter
        job_type: Job type filter
        created_by: Created by filter
        
    Returns:
        Paginated list of jobs
    """
    job_service = JobService(db)
    pagination = PaginationParams(page=page, size=size)
    
    # Convert string filters to enums
    status_filter = JobStatus(status) if status else None
    type_filter = JobType(job_type) if job_type else None
    
    jobs, total = job_service.get_jobs(
        pagination=pagination,
        status_filter=status_filter,
        type_filter=type_filter,
        created_by_filter=created_by
    )
    
    return PaginatedResponse.create(jobs, total, pagination)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_JOBS))]
):
    """Get job details by ID.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Job details
        
    Raises:
        HTTPException: If job not found
    """
    job_service = JobService(db)
    job = job_service.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return job


@router.get("/jobs/{job_id}/runs", response_model=List[JobRunResponse])
async def get_job_runs(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_JOBS))]
):
    """Get job runs for a specific job.
    
    Args:
        job_id: Job ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of job runs
        
    Raises:
        HTTPException: If job not found
    """
    job_service = JobService(db)
    
    # Verify job exists
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    runs = job_service.get_job_runs(job_id)
    return runs


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_JOBS))]
):
    """Stream job progress updates via Server-Sent Events.
    
    Args:
        job_id: Job ID to stream
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        SSE streaming response
        
    Raises:
        HTTPException: If job not found
    """
    job_service = JobService(db)
    
    # Verify job exists
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return create_sse_response(job_id, request)


@router.post("/jobs/sync-agents")
async def trigger_agent_sync(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.WRITE_JOBS))]
):
    """Trigger manual agent synchronization from OpAMP server.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created job information
    """
    from app.db.models import Job
    
    # Check if there's already a pending/running sync job
    existing_job = db.query(Job).filter(
        Job.type == JobType.SYNC_AGENTS.value,
        Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
    ).first()
    
    if existing_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent sync job already running: {existing_job.id}"
        )
    
    # Generate job ID
    import uuid
    
    # Create new sync job
    job = Job(
        id=str(uuid.uuid4()),
        type=JobType.SYNC_AGENTS.value,
        status=JobStatus.PENDING.value,
        total_agents=0,  # Not applicable for sync jobs
        created_by=current_user.username,
        payload_json={}  # Empty payload for sync jobs
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return JobResponse.from_orm(job)


@router.get("/jobs/stats")
async def get_job_statistics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[CurrentUser, Depends(require_permission(Permission.READ_JOBS))]
):
    """Get job statistics.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Job statistics
    """
    job_service = JobService(db)
    return job_service.get_job_statistics()