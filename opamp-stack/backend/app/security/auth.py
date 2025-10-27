"""JWT authentication utilities."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import PyJWTError

from app.settings import settings


class JWTManager:
    """JWT token management."""
    
    def __init__(self):
        """Initialize JWT manager with settings."""
        self.secret_key = settings.jwt_secret
        self.algorithm = "HS256"
        self.expires_delta = timedelta(minutes=settings.jwt_expires_min)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT access token.
        
        Args:
            data: Dictionary of claims to include in token
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + self.expires_delta
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token.
        
        Args:
            token: JWT token string to decode
            
        Returns:
            Dictionary of claims if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            
            # Verify token type
            if payload.get("type") != "access":
                return None
                
            return payload
        except PyJWTError:
            return None
    
    def verify_token(self, token: str) -> bool:
        """Verify if a token is valid.
        
        Args:
            token: JWT token string
            
        Returns:
            True if token is valid, False otherwise
        """
        return self.decode_token(token) is not None
    
    def get_token_claims(self, token: str) -> Dict[str, Any]:
        """Get claims from a token without verification.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary of claims (use with caution)
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
        except PyJWTError:
            return {}


# Global JWT manager instance
jwt_manager = JWTManager()