"""Role-Based Access Control (RBAC) utilities."""

from enum import Enum
from typing import List, Optional
from functools import wraps

from fastapi import HTTPException, status

from app.db.models import UserRole


class Permission(str, Enum):
    """System permissions."""
    READ_AGENTS = "read:agents"
    WRITE_AGENTS = "write:agents"
    READ_CONFIGS = "read:configs"
    WRITE_CONFIGS = "write:configs"
    READ_JOBS = "read:jobs"
    WRITE_JOBS = "write:jobs"
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    READ_AUDIT = "read:audit"
    ADMIN_ALL = "admin:all"


class RolePermissions:
    """Role to permissions mapping."""
    
    PERMISSIONS = {
        UserRole.ADMIN: [
            Permission.READ_AGENTS,
            Permission.WRITE_AGENTS,
            Permission.READ_CONFIGS,
            Permission.WRITE_CONFIGS,
            Permission.READ_JOBS,
            Permission.WRITE_JOBS,
            Permission.READ_USERS,
            Permission.WRITE_USERS,
            Permission.READ_AUDIT,
            Permission.ADMIN_ALL,
        ],
        UserRole.VIEWER: [
            Permission.READ_AGENTS,
            Permission.READ_CONFIGS,
            Permission.READ_JOBS,
        ],
    }
    
    @classmethod
    def get_permissions(cls, role: UserRole) -> List[Permission]:
        """Get permissions for a role.
        
        Args:
            role: User role
            
        Returns:
            List of permissions for the role
        """
        return cls.PERMISSIONS.get(role, [])
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: Permission) -> bool:
        """Check if role has a specific permission.
        
        Args:
            role: User role
            permission: Permission to check
            
        Returns:
            True if role has permission, False otherwise
        """
        role_permissions = cls.get_permissions(role)
        return permission in role_permissions or Permission.ADMIN_ALL in role_permissions


def require_permission(permission: Permission):
    """Decorator to require a specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (injected by dependency)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permission
            if not RolePermissions.has_permission(
                UserRole(current_user.role), 
                permission
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """Decorator to require admin role."""
    return require_permission(Permission.ADMIN_ALL)


def require_role(role: UserRole):
    """Decorator to require a specific role.
    
    Args:
        role: Required user role
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if UserRole(current_user.role) != role and UserRole(current_user.role) != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {role.value}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator