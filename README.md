# AmpBridge

**Complete OpAMP Management Platform** - Full-stack solution for managing OpenTelemetry agents at scale with modern web dashboard, REST API, and real-time agent configuration.

![status](https://img.shields.io/badge/status-v1.0-success) ![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.11+-yellow) ![react](https://img.shields.io/badge/react-18-blue) ![docker](https://img.shields.io/badge/docker-compose-informational)

---

## 🎯 What is AmpBridge?

AmpBridge is a **production-ready OpAMP management platform** that provides:

* 🖥️ **Modern Web Dashboard** - React-based UI for managing agents, configs, and viewing health
* 🚀 **REST API Backend** - FastAPI backend with authentication, agent management, and config versioning
* 📡 **OpAMP Server** - WebSocket/HTTP OpAMP protocol server for agent communication
* 💾 **PostgreSQL Storage** - Persistent storage for agents, configs, health data, and version history
* 🔐 **Authentication & Authorization** - JWT-based security with user management
* 📊 **Real-time Monitoring** - Live agent status, health checks, and connection tracking

> Designed for enterprise environments managing **hundreds to thousands** of OpenTelemetry agents across multiple environments (DEV / STAGING / PROD).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│                  http://localhost:3000                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ (HTTPS/REST)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + TS)                         │
│  • Login/Auth  • Agent List  • Config Editor  • History         │
└────────────────────────┬────────────────────────────────────────┘
                         │ (REST API)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI + Python)                     │
│  • JWT Auth  • Agent APIs  • Config Management  • Versioning    │
└────────┬──────────────────────────────────────────┬─────────────┘
         │ (SQL)                                     │ (OpAMP/HTTP)
         ↓                                           ↓
┌──────────────────┐                    ┌─────────────────────────┐
│   PostgreSQL     │                    │    OpAMP Server (Go)    │
│  • Agents        │                    │  • WebSocket/HTTP       │
│  • Configs       │                    │  • Agent Connection     │
│  • Health        │                    │  • Config Delivery      │
│  • Users         │                    └───────────┬─────────────┘
└──────────────────┘                                │ (OpAMP Protocol)
                                                    ↓
                                        ┌─────────────────────────┐
                                        │  OpenTelemetry Agents   │
                                        │  (1k - 10k+ hosts)      │
                                        └─────────────────────────┘
```

**Tech Stack**

* **Frontend**: React 18, TypeScript, Ant Design, Monaco Editor, TanStack Query, Vite
* **Backend**: FastAPI, SQLAlchemy, Alembic, Pydantic, JWT Auth
* **Database**: PostgreSQL 16
* **OpAMP Server**: Go-based reference implementation
* **Deployment**: Docker Compose, Nginx, multi-stage builds

---

## ✨ Features

### 🎨 Frontend Dashboard
* ✅ **Modern UI/UX** - Professional dashboard with Ant Design components
* ✅ **Agent Management** - List, filter, search agents by hostname, OS, status, health
* ✅ **Real-time Stats** - Live metrics: total agents, connected, healthy, OS distribution
* ✅ **Config Editor** - VS Code-quality YAML editor with syntax highlighting
* ✅ **Version Control** - Complete config history with restore capability
* ✅ **Responsive Design** - Works on desktop, tablet, mobile
* ✅ **Secure Auth** - Login system with JWT tokens

### 🔧 Backend API
* ✅ **RESTful APIs** - Complete CRUD operations for agents and configs
* ✅ **Authentication** - OAuth2 password flow with JWT tokens
* ✅ **Config Versioning** - Automatic versioning on every config change
* ✅ **Health Tracking** - Monitor agent health and connection status
* ✅ **Pagination & Filtering** - Efficient queries for large agent fleets
* ✅ **Download Configs** - Export agent configs as YAML files
* ✅ **Database Migrations** - Alembic-based schema management

### 📡 OpAMP Integration
* ✅ **OpAMP Protocol** - Full implementation of Open Agent Management Protocol
* ✅ **WebSocket Support** - Real-time bidirectional communication
* ✅ **Config Delivery** - Push configs to agents on-demand
* ✅ **Status Reporting** - Receive agent status updates
* ✅ **Health Monitoring** - Track agent health metrics

### 🐳 Deployment
* ✅ **Docker Compose** - One-command deployment
* ✅ **Multi-stage Builds** - Optimized production images
* ✅ **Health Checks** - Built-in container health monitoring
* ✅ **Volume Persistence** - Data survives container restarts
* ✅ **Production Ready** - Nginx, SSL-ready, secure defaults
* 🔒 TLS/mtls ready behind your reverse proxy (recommended)

---

## Metrics (names & labels)

* `opamp_agent_status{env, agent_id, host, version}` — gauge (1=UP, 0=DOWN)
* `opamp_agent_last_checkin_seconds{env, agent_id}` — gauge (epoch)
* `opamp_agent_config_applied{env, agent_id, config_hash}` — gauge (1 when in use)
* `opamp_agents_total{env}` — gauge
* `opamp_agent_errors_total{env, agent_id}` — counter (reserved for error paths)

**Cardinality guidance**: keep `agent_id` stable (e.g., hostname + collector uid). Avoid dynamic, unbounded label values.

---

## Quick start

### 1) Clone & structure

```
.
├─ docker-compose.yml
├─ .env
├─ opamp-ingestor/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ main.py
└─ metrics-svc/
   ├─ Dockerfile
   ├─ requirements.txt
   ├─ main.py
   ├─ storage.py
   ├─ metrics.py
   └─ exporters/
      ├─ remotewrite.py
      └─ otlp.py
```

### 2) Environment variables (`.env`)

```dotenv
# Logical environment tag
ENV_NAME=dev   # dev | homo | prod

# Select exactly ONE mode
METRICS_MODE=scrape
# METRICS_MODE=remotewrite
# METRICS_MODE=otlp

# Remote Write (if enabled)
REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write
REMOTE_WRITE_USERNAME=
REMOTE_WRITE_PASSWORD=

# OTLP (if enabled)
OTLP_ENDPOINT=http://otel-gateway:4317
OTLP_INSECURE=true
```

### 3) Bring up

```bash
docker compose up -d
```

### 4) Point your agents to OpAMP

On each host running `otelcol-contrib`:

```yaml
extensions:
  opamp:
    server:
      ws:
        endpoint: http://<your-opamp-server>:4320
service:
  extensions: [opamp]
```

> Use TLS/mTLS in production.

---

## Service endpoints (metrics-svc)

* `GET /` → service info `{service, mode, env}`
* `GET /status` → HTML table of agents
* `GET /status.json` → JSON snapshot `{env, total, agents[]}`
* `GET /config/{agent_id}` → JSON of effective config stored in Redis
* `GET /config/{agent_id}/download` → attachment (`application/json`)
* `GET /metrics` → Prometheus text exposition (enabled only when `METRICS_MODE=scrape`)

---

## Example PromQL

**Agents down (>5m no check‑in):**

```promql
(opamp_agent_status == 0) or (time() - opamp_agent_last_checkin_seconds > 300)
```

**Total by env:**

```promql
sum(opamp_agents_total) by (env)
```

**Config drift/changes (by hash):**

```promql
count by (env, config_hash) (opamp_agent_config_applied)
```

---

## Configuration flags

| Var                              | Default  | Notes                                            |
| -------------------------------- | -------- | ------------------------------------------------ |
| `ENV_NAME`                       | `dev`    | Logical environment label emitted on all metrics |
| `METRICS_MODE`                   | `scrape` | One of `scrape`, `remotewrite`, `otlp`           |
| `REMOTE_WRITE_URL`               | —        | Required when `remotewrite`                      |
| `REMOTE_WRITE_USERNAME/PASSWORD` | —        | Optional basic auth for RW                       |
| `OTLP_ENDPOINT`                  | —        | gRPC endpoint when `otlp`                        |
| `OTLP_INSECURE`                  | `true`   | Set `false` when using TLS                       |

---

## Scaling & reliability

* **Redis**: enable AOF, snapshots; for production, use **Sentinel** or managed Redis.
* **Sharding**: run multiple `opamp-ingestor` replicas with partitioning by `agent_id` hash.
* **Backpressure**: batch Remote Write pushes; increase scrape interval for very large estates.
* **Security**: place OpAMP and metrics-svc behind a reverse proxy with TLS/mTLS and auth.

---

## Development notes

* `opamp-ingestor` uses WebSocket to the reference OpAMP server (path may vary by image/version, e.g. `/v1/opamp`).
* `metrics-svc` is FastAPI; scrape mode relies on `prometheus-client`. Remote Write uses compact protobuf with snappy.
* **OTLP mode** scaffold is present; for production, prefer stable instruments (Counter/UpDownCounter) plus views.

---

## Roadmap

* [ ] Full OTLP gauge push with async callbacks & views
* [ ] AuthN/AuthZ for status endpoints
* [ ] Multi-tenant Redis keyspace per env/project
* [ ] Native gRPC OpAMP client and retry policies
* [ ] Optional S3/GCS config archival

---

## Contributing

Issues and PRs are welcome! Please open a discussion if you plan major changes (labels/cardinality or storage schema).

---

## License

MIT. See `LICENSE`.

---

## Acknowledgements

* OpenTelemetry community & OpAMP reference server
* Prometheus & Grafana ecosystems

[OpAMP]: https://github.com/open-telemetry/opamp-spec
