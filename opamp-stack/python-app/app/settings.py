from pydantic import BaseModel
import os

class Settings(BaseModel):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")  # dev|homo|prod (rótulo nas métricas)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Descoberta dos agentes via UI do opamp-server
    OPAMP_SERVER_HTTP_BASE: str = os.getenv("OPAMP_SERVER_HTTP_BASE", "http://opamp-server:4321")
    # Caminhos padrão da UI do example server (ajuste se necessário)
    OPAMP_API_LIST: str = os.getenv("OPAMP_API_LIST", "/api/agents")
    OPAMP_API_AGENT: str = os.getenv("OPAMP_API_AGENT", "/api/agents/{agent_id}")

    # Modo de saída de métricas: "SCRAPE" | "REMOTE_WRITE" | "OTLP"
    METRICS_MODE: str = os.getenv("METRICS_MODE", "SCRAPE").upper()

    # Remote Write via sidecar (otel-bridge) -> essas vars configuram o collector
    REMOTE_WRITE_URL: str = os.getenv("REMOTE_WRITE_URL", "")       # usado pelo otel-bridge
    REMOTE_WRITE_BASIC_AUTH_USER: str = os.getenv("REMOTE_WRITE_BASIC_AUTH_USER", "")
    REMOTE_WRITE_BASIC_AUTH_PASS: str = os.getenv("REMOTE_WRITE_BASIC_AUTH_PASS", "")

    # OTLP Export
    OTLP_ENDPOINT: str = os.getenv("OTLP_ENDPOINT", "http://otel-collector:4317")  # grpc
    OTLP_HEADERS: str = os.getenv("OTLP_HEADERS", "")  # ex: "authorization=Bearer abc,foo=bar"

settings = Settings()
