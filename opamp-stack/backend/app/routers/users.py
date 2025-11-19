"""
Users router.
Provides CRUD endpoints for user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse
)
from app.dependencies import get_current_active_user
from app.models.models import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all users with pagination.
    Requires authentication.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 500)
    """
    user_repo = UserRepository(db)
    
    skip = (page - 1) * page_size
    users = await user_repo.get_all(skip=skip, limit=page_size)
    total = await user_repo.count()
    
    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=users
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed information about a specific user.
    Requires authentication.
    
    - **user_id**: User ID
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found"
        )
    
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new user.
    Requires authentication.
    
    - **name**: User's full name
    - **email**: User's email address (must be unique)
    - **login**: User's login username (must be unique)
    - **password**: User's password (minimum 8 characters)
    """
    user_repo = UserRepository(db)
    
    # Check if user with same email or login already exists
    existing_user = await user_repo.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    existing_user = await user_repo.get_by_login(user_data.login)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this login already exists"
        )
    
    try:
        user = await user_repo.create(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update user information.
    Requires authentication.
    
    - **user_id**: User ID
    - **name**: User's full name (optional)
    - **email**: User's email address (optional)
    - **password**: User's new password (optional)
    - **is_active**: User's active status (optional)
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found"
        )
    
    # Check if email is being changed and if it's already in use
    if user_data.email and user_data.email != user.email:
        existing_user = await user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use by another user"
            )
    
    try:
        updated_user = await user_repo.update(user, user_data)
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a user.
    Requires authentication.
    
    - **user_id**: User ID
    
    Note: Users cannot delete themselves.
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account"
        )
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found"
        )
    
    await user_repo.delete(user)
    return None
