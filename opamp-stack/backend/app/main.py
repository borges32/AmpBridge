"""
Main FastAPI application.
OpAMP Backend API - Sistema backend para gerenciamento de agents OpAMP.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.routers import auth, agents, config, opamp
from app.background import background_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting application...")
    await background_tasks.start()
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await background_tasks.stop()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    Sistema backend completo para gerenciamento de agents OpAMP.
    
    ## Recursos
    
    * **Autenticação JWT** - Sistema de login e autenticação de usuários
    * **Gestão de Agents** - Consulta e monitoramento de agents OpAMP
    * **Versionamento de Configurações** - Histórico completo de configs
    * **Sincronização Automática** - Sync periódico com OpAMP server
    * **Alertas de Divergência** - Detecção automática de mudanças de config
    * **Exportação de Dados** - Export de agents em CSV
    
    ## Autenticação
    
    A maioria dos endpoints requer autenticação via JWT token.
    
    1. Registre um usuário em `/api/v1/auth/register`
    2. Faça login em `/api/v1/auth/login` para obter o token
    3. Use o token no header: `Authorization: Bearer <token>`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware (configure conforme necessário)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(agents.router, prefix=settings.API_V1_PREFIX)
app.include_router(config.router, prefix=settings.API_V1_PREFIX)
app.include_router(opamp.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "OpAMP Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "opamp-backend",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
