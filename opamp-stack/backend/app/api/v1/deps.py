"""API dependencies for FastAPI routes."""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.security.auth import jwt_manager
from app.security.rbac import Permission, RolePermissions, UserRole

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user.
    
    Args:
        credentials: JWT credentials
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Decode JWT token
    payload = jwt_manager.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get username from token
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (alias for backward compatibility)."""
    return current_user


def require_permission(permission: Permission):
    """Create dependency that requires a specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    async def permission_dependency(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not RolePermissions.has_permission(UserRole(current_user.role), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        return current_user
    
    return permission_dependency


def require_admin():
    """Create dependency that requires admin role."""
    return require_permission(Permission.ADMIN_ALL)


def require_role(role: UserRole):
    """Create dependency that requires a specific role.
    
    Args:
        role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_dependency(
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_role = UserRole(current_user.role)
        if user_role != role and user_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {role.value}"
            )
        return current_user
    
    return role_dependency


async def get_user_agent(
    user_agent: Optional[str] = Header(default=None)
) -> Optional[str]:
    """Get User-Agent header."""
    return user_agent


async def get_client_ip(
    x_forwarded_for: Optional[str] = Header(default=None),
    x_real_ip: Optional[str] = Header(default=None)
) -> Optional[str]:
    """Get client IP address from headers."""
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return x_real_ip


# Common dependency annotations
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin())]
DatabaseSession = Annotated[Session, Depends(get_db)]