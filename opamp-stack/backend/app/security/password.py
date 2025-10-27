"""Password hashing utilities using Argon2."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError


class PasswordManager:
    """Password hashing and verification using Argon2id."""
    
    def __init__(self):
        """Initialize password hasher with secure defaults."""
        self.hasher = PasswordHasher(
            time_cost=3,       # Number of iterations
            memory_cost=65536, # Memory usage in KB (64MB)
            parallelism=1,     # Number of parallel threads
            hash_len=32,       # Length of hash in bytes
            salt_len=16,       # Length of salt in bytes
        )
    
    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
            
        Raises:
            HashingError: If hashing fails
        """
        try:
            return self.hasher.hash(password)
        except Exception as e:
            raise HashingError(f"Failed to hash password: {str(e)}")
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed_password: Hashed password from database
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            self.hasher.verify(hashed_password, password)
            return True
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password hash needs to be updated.
        
        Args:
            hashed_password: Current hash from database
            
        Returns:
            True if hash should be updated
        """
        try:
            return self.hasher.check_needs_rehash(hashed_password)
        except Exception:
            return True


# Global password manager instance
password_manager = PasswordManager()