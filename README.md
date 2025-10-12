# AmpBridge

Bridge OpenTelemetry **OpAMP → Redis → Metrics** with multi-mode export (Prometheus scrape, Remote Write, or OTLP), plus status HTML/JSON views and per-host config download.

![status](https://img.shields.io/badge/status-MVP-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.11+-yellow) ![docker](https://img.shields.io/badge/docker-compose-informational)

---

## Why AmpBridge?

Large estates (1k–10k+ OTel agents) need a simple way to **observe agent health and effective config** via [OpAMP], persist that state, and expose **low‑cardinality metrics** ready for Prometheus/Grafana. AmpBridge does exactly that:

* Ingests OpAMP envelopes and **persists** agent status/config in **Redis**
* Exposes metrics via **one** of three delivery modes:

  1. **Scrape** (`/metrics`)  2) **Remote Write**  3) **OTLP** (to an upstream Collector)
* Presents **status HTML/JSON** pages and **per‑agent config download**

> Designed for multi‑env setups (DEV / HOMO / PROD) with ~1,800 hosts per env.

---

## Architecture

```
[ OTel Agents (opamp extension) ]
           |  (OpAMP)
           v
   [opamp-server]  --->  [opamp-ingestor (Python)]  --->  [Redis]
                                       |                    ^
                                       v                    |
                                   [metrics-svc (FastAPI)] ---(scrape|RW|OTLP)---> Prometheus / Gateway / OTel Collector
```

**Components**

* **opamp-server**: reference OpAMP server (WebSocket/HTTP).
* **opamp-ingestor**: Python client that consumes OpAMP envelopes and stores them in Redis.
* **metrics-svc**: FastAPI service that reads Redis and exposes metrics (scrape / remote write / OTLP) and status+config endpoints.

---

## Features

* ✅ OpAMP→Redis persistence of **status** and **effective config**
* ✅ **Prometheus‑ready metrics** with conservative labels (low cardinality)
* ✅ **Three export modes** (select exactly one via env var)
* ✅ **Status UI** (`/status`) & **JSON** (`/status.json`)
* ✅ **Per‑agent config viewer & download** (`/config/{agent_id}`)
* ✅ Docker‑Compose one‑command bring‑up
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
