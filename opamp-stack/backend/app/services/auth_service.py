"""
Service layer for authentication business logic.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.core.security import verify_password, create_access_token
from app.models.models import User
from app.schemas import LoginRequest, Token


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def authenticate_user(self, login: str, password: str) -> Optional[User]:
        """
        Authenticate a user by login and password.
        
        Returns:
            User object if authentication successful, None otherwise
        """
        user = await self.user_repo.get_by_login(login)
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    async def login(self, login_data: LoginRequest) -> Token:
        """
        Process login request and generate JWT token.
        
        Raises:
            ValueError: If authentication fails
        """
        user = await self.authenticate_user(login_data.login, login_data.password)
        
        if not user:
            raise ValueError("Incorrect login or password")
        
        # Create access token - sub must be a string
        access_token = create_access_token(data={"sub": str(user.id), "login": user.login})
        
        return Token(access_token=access_token, token_type="bearer")
