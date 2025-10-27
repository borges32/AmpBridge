"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.settings import settings
from app.db.base import create_tables
from app.telemetry.tracing import setup_tracing
from app.telemetry.metrics import get_metrics, get_content_type, HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION
from app.jobs.runner import job_runner
from app.api.v1 import auth, agents, configs, jobs
from app.security.password import password_manager
from app.db.session import get_db_session
from app.db.models import User, UserRole

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting OpAMP Backend API")
    
    # Setup tracing
    setup_tracing()
    
    # Create database tables
    create_tables()
    
    # Create bootstrap admin user
    await create_bootstrap_admin()
    
    # Start job runner
    await job_runner.start()
    
    logger.info("OpAMP Backend API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down OpAMP Backend API")
    
    # Stop job runner
    await job_runner.stop()
    
    logger.info("OpAMP Backend API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="OpAMP Backend API",
    description="REST API for managing OpAMP agents and configurations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect HTTP metrics."""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    
    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    HTTP_REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response


# Health check endpoints
@app.get("/healthz", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-10-26T12:00:00Z"}


@app.get("/readyz", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint."""
    # Check database connection
    try:
        with get_db_session() as db:
            db.execute("SELECT 1")
        return {"status": "ready", "timestamp": "2024-10-26T12:00:00Z"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(e)}
        )


# Metrics endpoint
@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=get_content_type()
    )


# Include API routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
app.include_router(configs.router, prefix="/api/v1", tags=["Configurations"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])


async def create_bootstrap_admin():
    """Create bootstrap admin user if it doesn't exist."""
    try:
        with get_db_session() as db:
            # Check if admin user exists
            admin_user = db.query(User).filter(User.username == settings.admin_user).first()
            
            if not admin_user:
                # Create admin user
                hashed_password = password_manager.hash_password(settings.admin_pass)
                
                admin_user = User(
                    username=settings.admin_user,
                    hashed_password=hashed_password,
                    role=UserRole.ADMIN,
                    is_active=True
                )
                
                db.add(admin_user)
                db.commit()
                
                logger.info(f"Bootstrap admin user '{settings.admin_user}' created")
            else:
                logger.info(f"Admin user '{settings.admin_user}' already exists")
    
    except Exception as e:
        logger.error(f"Failed to create bootstrap admin user: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )