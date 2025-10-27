"""Authentication API endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db, get_client_ip, get_user_agent, get_current_user
from app.db.models import User
from app.security.auth import jwt_manager
from app.security.password import password_manager
from app.telemetry.metrics import AUTH_ATTEMPTS_TOTAL, AUTH_TOKEN_ISSUED_TOTAL, increment_counter

router = APIRouter()


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data model."""
    username: str


class UserInfo(BaseModel):
    """User information model."""
    username: str
    role: str
    is_active: bool


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
    client_ip: Annotated[str, Depends(get_client_ip)] = None,
    user_agent: Annotated[str, Depends(get_user_agent)] = None
):
    """Authenticate user and return JWT token.
    
    Args:
        form_data: Login form data (username/password)
        db: Database session
        client_ip: Client IP address
        user_agent: User agent string
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user from database
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Verify user exists and password is correct
    if not user or not password_manager.verify_password(form_data.password, user.hashed_password):
        increment_counter(AUTH_ATTEMPTS_TOTAL, {"status": "failed"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        increment_counter(AUTH_ATTEMPTS_TOTAL, {"status": "failed"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    token_data = {
        "sub": user.username,
        "role": user.role,
        "user_id": user.id
    }
    
    access_token = jwt_manager.create_access_token(token_data)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Update metrics
    increment_counter(AUTH_ATTEMPTS_TOTAL, {"status": "success"})
    increment_counter(AUTH_TOKEN_ISSUED_TOTAL)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_manager.expires_delta.total_seconds()
    )


@router.get("/auth/me", response_model=UserInfo)
async def get_current_user_info(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Get current user information.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return UserInfo(
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active
    )