import asyncio
import json
import os
import time
from typing import Dict, Any, List, Optional

import httpx
import redis
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel

from .settings import settings

app = FastAPI(title="OpAMP Status Exporter", version="1.0.0")

r = redis.from_url(settings.REDIS_URL, decode_responses=True)

# ---- Prometheus registry ----
registry = CollectorRegistry()
g_up = Gauge("opamp_agent_up", "Agente reportado como 'Up' pelo OpAMP Server",
             ["env", "agent_id", "os", "arch", "version"], registry=registry)
g_last_seen = Gauge("opamp_agent_last_seen", "Último contato do agente (epoch seconds)",
                    ["env", "agent_id"], registry=registry)
g_cfg_bytes = Gauge("opamp_agent_config_bytes", "Tamanho (bytes) do config efetivo reportado", 
                    ["env", "agent_id"], registry=registry)
g_total = Gauge("opamp_agents_total", "Total de agentes conhecidos neste ambiente",
                ["env"], registry=registry)

# ---- OTLP (modo 3) opcional ----
otlp_enabled = settings.METRICS_MODE == "OTLP"
if otlp_enabled:
    from opentelemetry import metrics
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    headers = {}
    if settings.OTLP_HEADERS.strip():
        for pair in settings.OTLP_HEADERS.split(","):
            k, v = pair.split("=", 1)
            headers[k.strip()] = v.strip()

    exporter = OTLPMetricExporter(endpoint=settings.OTLP_ENDPOINT, headers=headers)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10000)
    provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter("opamp_status_exporter")

    # instruments
    m_up = meter.create_gauge("opamp_agent_up")
    m_last = meter.create_gauge("opamp_agent_last_seen")
    m_cfg = meter.create_gauge("opamp_agent_config_bytes")
    m_total = meter.create_gauge("opamp_agents_total")

# ---- Modelos ----
class AgentStatus(BaseModel):
    agent_id: str
    up: bool
    os: Optional[str] = ""
    arch: Optional[str] = ""
    version: Optional[str] = ""
    last_seen: Optional[int] = 0
    effective_config: Optional[str] = None

OPAMP_LIST_URL = settings.OPAMP_SERVER_HTTP_BASE.rstrip("/") + settings.OPAMP_API_LIST
OPAMP_AGENT_URL_TMPL = settings.OPAMP_SERVER_HTTP_BASE.rstrip("/") + settings.OPAMP_API_AGENT

async def fetch_agents() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=10) as client:
        # Espera-se que retorne lista de agentes (JSON)
        res = await client.get(OPAMP_LIST_URL)
        res.raise_for_status()
        return res.json()

async def fetch_agent_detail(agent_id: str) -> Dict[str, Any]:
    path = OPAMP_AGENT_URL_TMPL.format(agent_id=agent_id)
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(path)
        res.raise_for_status()
        return res.json()

def persist_agent(status: AgentStatus):
    key = f"agent:{status.agent_id}:status"
    r.hset(key, mapping={
        "up": "1" if status.up else "0",
        "os": status.os or "",
        "arch": status.arch or "",
        "version": status.version or "",
        "last_seen": str(status.last_seen or 0)
    })
    if status.effective_config is not None:
        r.set(f"agent:{status.agent_id}:config", status.effective_config)

def emit_metrics(agents: List[AgentStatus]):
    # Zera e reemite (simplificado)
    for a in agents:
        labels = [settings.ENVIRONMENT, a.agent_id, a.os or "", a.arch or "", a.version or ""]
        g_up.labels(*labels).set(1 if a.up else 0)
        g_last_seen.labels(settings.ENVIRONMENT, a.agent_id).set(a.last_seen or 0)
        cfg = r.get(f"agent:{a.agent_id}:config") or ""
        g_cfg_bytes.labels(settings.ENVIRONMENT, a.agent_id).set(len(cfg.encode("utf-8")))

    g_total.labels(settings.ENVIRONMENT).set(len(agents))

    # OTLP mirrors (se habilitado)
    if otlp_enabled:
        for a in agents:
            attrs = {
                "env": settings.ENVIRONMENT,
                "agent_id": a.agent_id,
                "os": a.os or "",
                "arch": a.arch or "",
                "version": a.version or "",
            }
            m_up.record(1 if a.up else 0, attributes=attrs)
            m_last.record(a.last_seen or 0, attributes={"env": settings.ENVIRONMENT, "agent_id": a.agent_id})
            cfg = r.get(f"agent:{a.agent_id}:config") or ""
            m_cfg.record(len(cfg.encode("utf-8")), attributes={"env": settings.ENVIRONMENT, "agent_id": a.agent_id})
        m_total.record(len(agents), attributes={"env": settings.ENVIRONMENT})

async def poll_loop():
    await asyncio.sleep(3)  # grace
    while True:
        try:
            agents_raw = await fetch_agents()
            agents: List[AgentStatus] = []
            # Para cada agente, carregar detalhes (inclui effective config)
            tasks = []
            for a in agents_raw:
                agent_id = a.get("id") or a.get("agent_id") or a.get("uid") or ""
                if not agent_id:
                    continue
                tasks.append(fetch_agent_detail(agent_id))
            details = await asyncio.gather(*tasks, return_exceptions=True)

            for det in details:
                if isinstance(det, Exception):
                    continue
                agent_id = det.get("id") or det.get("agent_id") or det.get("uid") or ""
                up = bool(det.get("up") or det.get("status", {}).get("up") or det.get("status", {}).get("healthy"))
                os_ = det.get("os") or det.get("runtime", {}).get("os") or ""
                arch = det.get("arch") or det.get("runtime", {}).get("arch") or ""
                version = det.get("version") or det.get("agent_version") or ""
                last_seen = int(det.get("last_seen") or det.get("lastSeen") or time.time())
                effective_config = det.get("effective_config") or det.get("effectiveConfig") or None

                st = AgentStatus(
                    agent_id=agent_id, up=up, os=os_, arch=arch, version=version,
                    last_seen=last_seen, effective_config=effective_config
                )
                persist_agent(st)
                agents.append(st)

            emit_metrics(agents)
        except Exception as e:
            # Evita matar o loop
            print(f"[poll] erro: {e}")
        await asyncio.sleep(10)

@app.on_event("startup")
async def on_startup():
    if settings.METRICS_MODE not in {"SCRAPE", "REMOTE_WRITE", "OTLP"}:
        raise RuntimeError("METRICS_MODE inválido. Use SCRAPE, REMOTE_WRITE ou OTLP.")
    # inicia poller
    asyncio.create_task(poll_loop())

@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"

@app.get("/metrics")
async def metrics():
    # No modo REMOTE_WRITE, o collector sidecar irá fazer scrape desta rota
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)

@app.get("/config")
async def get_config(agent_id: str, format: str = "json"):
    cfg = r.get(f"agent:{agent_id}:config")
    key = f"agent:{agent_id}:status"
    st = r.hgetall(key)
    if cfg is None and not st:
        raise HTTPException(404, "Agente não encontrado")
    payload = {
        "agent_id": agent_id,
        "status": st,
        "config": cfg or ""
    }
    if format.lower() == "html":
        html = f"""
        <html><body>
        <h2>Agente {agent_id}</h2>
        <h3>Status</h3>
        <pre>{json.dumps(st, indent=2, ensure_ascii=False)}</pre>
        <h3>Config Efetivo</h3>
        <pre>{(cfg or "").replace("<", "&lt;").replace(">", "&gt;")}</pre>
        <a href="/config/download?agent_id={agent_id}">Download do config</a>
        </body></html>
        """
        return HTMLResponse(content=html)
    return payload

@app.get("/config/download")
async def download_config(agent_id: str):
    cfg = r.get(f"agent:{agent_id}:config")
    if cfg is None:
        raise HTTPException(404, "Config não disponível")
    async def streamer():
        yield cfg.encode("utf-8")
    filename = f"{agent_id}_effective_config.yaml"
    return StreamingResponse(streamer(), media_type="application/octet-stream",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
