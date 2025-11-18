"""
OpAMP synchronization router.
Provides endpoints for manual synchronization with OpAMP server.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.opamp_service import OpAMPService
from app.schemas import SyncResponse
from app.dependencies import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/opamp", tags=["OpAMP Sync"])


@router.post("/sync", response_model=SyncResponse)
async def manual_sync(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger synchronization with OpAMP server.
    Fetches all agents from OpAMP and updates the database.
    Requires authentication.
    
    This endpoint:
    - Fetches all agents from OpAMP /agents/full
    - Updates agent information
    - Creates health records
    - Versions configurations when changes are detected
    - Marks disconnected agents
    """
    opamp_service = OpAMPService(db)
    result = await opamp_service.sync_all_agents()
    
    return result
