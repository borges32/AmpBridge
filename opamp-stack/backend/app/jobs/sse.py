"""Server-Sent Events (SSE) support for job progress streaming."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime

from fastapi import Request
from fastapi.responses import StreamingResponse

from app.jobs.runner import job_runner
from app.db.session import get_db_session
from app.core.services.job_service import JobService

logger = logging.getLogger(__name__)


class SSEManager:
    """Server-Sent Events manager for real-time updates."""
    
    def __init__(self):
        """Initialize SSE manager."""
        self.clients: Dict[str, Dict[str, Any]] = {}
    
    def add_client(self, client_id: str, job_id: str, request: Request):
        """Add a client for job progress updates.
        
        Args:
            client_id: Unique client identifier
            job_id: Job ID to track
            request: FastAPI request object
        """
        self.clients[client_id] = {
            "job_id": job_id,
            "request": request,
            "connected_at": datetime.utcnow()
        }
        
        logger.debug(f"SSE client {client_id} connected for job {job_id}")
    
    def remove_client(self, client_id: str):
        """Remove a client.
        
        Args:
            client_id: Client identifier to remove
        """
        if client_id in self.clients:
            job_id = self.clients[client_id]["job_id"]
            del self.clients[client_id]
            logger.debug(f"SSE client {client_id} disconnected from job {job_id}")
    
    def get_clients_for_job(self, job_id: str) -> List[str]:
        """Get all client IDs listening to a specific job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of client IDs
        """
        return [
            client_id for client_id, info in self.clients.items()
            if info["job_id"] == job_id
        ]
    
    async def broadcast_job_update(self, job_id: str, data: Dict[str, Any]):
        """Broadcast job update to all listening clients.
        
        Args:
            job_id: Job ID
            data: Update data to broadcast
        """
        clients_to_remove = []
        
        for client_id, info in self.clients.items():
            if info["job_id"] == job_id:
                try:
                    # Check if client is still connected
                    if await info["request"].is_disconnected():
                        clients_to_remove.append(client_id)
                        continue
                    
                    # Note: In a real implementation, you would need a way to send data
                    # to the specific client. This is a placeholder for the concept.
                    logger.debug(f"Would broadcast to client {client_id}: {data}")
                    
                except Exception as e:
                    logger.warning(f"Error broadcasting to client {client_id}: {e}")
                    clients_to_remove.append(client_id)
        
        # Clean up disconnected clients
        for client_id in clients_to_remove:
            self.remove_client(client_id)


# Global SSE manager instance
sse_manager = SSEManager()


async def job_progress_stream(job_id: str, request: Request) -> AsyncGenerator[str, None]:
    """Generate SSE stream for job progress updates.
    
    Args:
        job_id: Job ID to track
        request: FastAPI request object
        
    Yields:
        SSE formatted messages
    """
    client_id = f"{job_id}_{datetime.utcnow().timestamp()}"
    sse_manager.add_client(client_id, job_id, request)
    
    try:
        # Send initial data
        with get_db_session() as db:
            job_service = JobService(db)
            job = job_service.get_job_by_id(job_id)
            
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                return
            
            # Send initial job status
            initial_data = {
                "type": "job_status",
                "job_id": job_id,
                "status": job.status,
                "progress": job.progress,
                "total_agents": job.total_agents,
                "successful_agents": job.successful_agents,
                "failed_agents": job.failed_agents,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None
            }
            
            yield f"data: {json.dumps(initial_data)}\n\n"
        
        # Stream progress updates
        last_progress = -1
        
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Get current progress from job runner
            progress_info = job_runner.get_job_progress(job_id)
            
            if progress_info:
                current_progress = progress_info.get("progress", 0)
                
                # Send update if progress changed
                if current_progress != last_progress:
                    update_data = {
                        "type": "progress_update",
                        "job_id": job_id,
                        "progress": current_progress,
                        "completed": progress_info.get("completed", 0),
                        "successful": progress_info.get("successful", 0),
                        "failed": progress_info.get("failed", 0),
                        "total": progress_info.get("total", 0),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    yield f"data: {json.dumps(update_data)}\n\n"
                    last_progress = current_progress
                
                # Check if job completed
                if current_progress >= 100:
                    break
            else:
                # Job not in progress tracking, check database
                with get_db_session() as db:
                    job_service = JobService(db)
                    job = job_service.get_job_by_id(job_id)
                    
                    if not job:
                        break
                    
                    # Send final status if job is completed
                    if job.status in ["completed", "failed", "cancelled"]:
                        final_data = {
                            "type": "job_completed",
                            "job_id": job_id,
                            "status": job.status,
                            "progress": job.progress,
                            "successful_agents": job.successful_agents,
                            "failed_agents": job.failed_agents,
                            "error_message": job.error_message,
                            "finished_at": job.finished_at.isoformat() if job.finished_at else None
                        }
                        
                        yield f"data: {json.dumps(final_data)}\n\n"
                        break
            
            # Wait before next check
            await asyncio.sleep(1)
    
    except asyncio.CancelledError:
        logger.debug(f"SSE stream cancelled for job {job_id}")
    except Exception as e:
        logger.error(f"Error in SSE stream for job {job_id}: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    finally:
        sse_manager.remove_client(client_id)


def create_sse_response(job_id: str, request: Request) -> StreamingResponse:
    """Create SSE streaming response for job progress.
    
    Args:
        job_id: Job ID to track
        request: FastAPI request object
        
    Returns:
        StreamingResponse with SSE headers
    """
    return StreamingResponse(
        job_progress_stream(job_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )