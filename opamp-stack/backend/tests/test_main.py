"""Basic tests for the OpAMP Backend API."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base, get_db
from app.db.models import User, UserRole
from app.security.password import password_manager

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a test user."""
    db = TestingSessionLocal()
    
    # Create admin user
    hashed_password = password_manager.hash_password("testpass123")
    user = User(
        username="testadmin",
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    yield user
    
    # Cleanup
    db.delete(user)
    db.commit()
    db.close()


@pytest.fixture
def auth_headers(test_user):
    """Get authentication headers."""
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "testadmin", "password": "testpass123"}
    )
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_readiness_check(self):
        """Test readiness check endpoint."""
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_login_success(self, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testadmin", "password": "testpass123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "invalid", "password": "invalid"}
        )
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_protected_route_without_token(self):
        """Test accessing protected route without token."""
        response = client.get("/api/v1/agents")
        assert response.status_code == 401
    
    def test_protected_route_with_token(self, auth_headers):
        """Test accessing protected route with valid token."""
        with patch('app.core.services.agent_service.AgentService.get_agents') as mock_get_agents:
            mock_get_agents.return_value = ([], 0)
            
            response = client.get("/api/v1/agents", headers=auth_headers)
            assert response.status_code == 200


class TestAgentEndpoints:
    """Test agent-related endpoints."""
    
    @patch('app.core.services.agent_service.AgentService.sync_agents_from_opamp')
    @patch('app.core.services.agent_service.AgentService.get_agents')
    def test_list_agents(self, mock_get_agents, mock_sync, auth_headers):
        """Test listing agents."""
        # Mock service responses
        mock_get_agents.return_value = ([], 0)
        mock_sync.return_value = 0
        
        response = client.get("/api/v1/agents", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
    
    @patch('app.core.services.agent_service.AgentService.get_agent_by_id')
    def test_get_agent_not_found(self, mock_get_agent, auth_headers):
        """Test getting non-existent agent."""
        mock_get_agent.return_value = None
        
        response = client.get("/api/v1/agents/nonexistent", headers=auth_headers)
        assert response.status_code == 404
    
    @patch('app.core.services.agent_service.AgentService.sync_agents_from_opamp')
    def test_sync_agents(self, mock_sync, auth_headers):
        """Test manual agent sync."""
        mock_sync.return_value = 5
        
        response = client.post("/api/v1/agents/sync", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["synced_agents"] == 5


class TestPasswordSecurity:
    """Test password security functionality."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        
        # Hash password
        hashed = password_manager.hash_password(password)
        assert hashed != password
        assert len(hashed) > 50  # Argon2 hashes are long
        
        # Verify correct password
        assert password_manager.verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert password_manager.verify_password("wrong_password", hashed) is False
    
    def test_password_rehash_check(self):
        """Test password rehash requirement check."""
        password = "test_password_123"
        hashed = password_manager.hash_password(password)
        
        # Should not need rehash for newly created hash
        assert password_manager.needs_rehash(hashed) is False


class TestOpAMPClient:
    """Test OpAMP client functionality."""
    
    @patch('app.clients.opamp.httpx.AsyncClient')
    async def test_opamp_client_list_agents(self, mock_client):
        """Test OpAMP client agent listing."""
        from app.clients.opamp import OpAMPClient
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "agents": [
                {
                    "id": "agent1",
                    "name": "Test Agent 1",
                    "status": "healthy"
                }
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        client = OpAMPClient()
        agents = await client.list_agents()
        
        assert len(agents) == 1
        assert agents[0].id == "agent1"
        assert agents[0].name == "Test Agent 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])