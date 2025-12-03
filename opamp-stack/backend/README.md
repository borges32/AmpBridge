# OpAMP Backend API

Complete backend system for managing and synchronizing OpAMP agents, with REST API, JWT authentication, configuration versioning, and automatic synchronization.

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Database Modeling](#database-modeling)
- [Project Structure](#project-structure)
- [Installation and Execution](#installation-and-execution)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [OpAMP Synchronization](#opamp-synchronization)
- [Configuration Versioning](#configuration-versioning)

---

## 🏗️ Architecture

### Chosen Stack: **FastAPI + PostgreSQL + SQLAlchemy**

**Justification for the choice:**

1. **FastAPI**: Modern and high-performance framework for Python APIs
   - Native async/await support
   - Automatic validation with Pydantic
   - Automatic documentation (Swagger/OpenAPI)
   - Excellent performance (comparable to Node.js and Go)

2. **PostgreSQL**: Robust relational database
   - ACID compliance
   - JSON support for flexible data
   - Excellent for versioning and history

3. **SQLAlchemy 2.0**: Modern ORM with async support
   - Migrations with Alembic
   - Complete type hints
   - Optimized performance

### Application Layers

```
┌─────────────────────────────────────┐
│         Routers (API Layer)         │  ← REST Endpoints
├─────────────────────────────────────┤
│      Services (Business Logic)      │  ← Business rules
├─────────────────────────────────────┤
│    Repositories (Data Access)       │  ← Data access
├─────────────────────────────────────┤
│      Models (Database Layer)        │  ← SQLAlchemy Models
└─────────────────────────────────────┘
```

**Main components:**

- **Routers**: Define endpoints and request/response validation
- **Services**: Implement business logic (OpAMP sync, versioning)
- **Repositories**: Encapsulate database operations
- **Models**: Define table structure (SQLAlchemy)
- **Schemas**: Data validation (Pydantic)
- **Core**: Configuration, security, database

---

## 💻 Technology Stack

| Component | Technology | Version |
|------------|-----------|--------|
| Runtime | Python | 3.11+ |
| Framework | FastAPI | 0.104+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.12+ |
| Database | PostgreSQL | 15+ |
| Async Driver | asyncpg | 0.29+ |
| Auth | JWT (python-jose) | 3.3+ |
| Password Hash | bcrypt (passlib) | 1.7+ |
| HTTP Client | httpx | 0.25+ |
| Server | Uvicorn | 0.24+ |

---

## 🗄️ Database Modeling

### ER Diagram

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │
│ name            │
│ email (UNIQUE)  │
│ login (UNIQUE)  │
│ password_hash   │
│ is_active       │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         │ 1:N
         │
         ▼
┌─────────────────────────────┐
│      agent_configs          │
├─────────────────────────────┤
│ id (PK)                     │
│ instance_id (FK) ───────┐   │
│ version                  │   │
│ effective_config (TEXT)  │   │
│ config_hash              │   │
│ source                   │   │
│ updated_by_user_id (FK)  │   │
│ created_at               │   │
│ updated_at               │   │
└──────────────────────────┘   │
                               │
                               │
         ┌─────────────────────┘
         │
         │ N:1
         ▼
┌─────────────────────┐
│      agents         │
├─────────────────────┤
│ id (PK)             │
│ instance_id (UNIQUE)│ ◄──┐
│ host_name           │    │
│ os_type             │    │
│ os_description      │    │
│ healthy             │    │
│ status_sync         │    │ 1:N
│ alert_config        │    │
│ is_connected        │    │
│ started_at          │    │
│ last_seen_at        │    │
│ created_at          │    │
│ updated_at          │    │
└─────────────────────┘    │
                           │
                           │
┌──────────────────────────┘
│
│ 1:N
│
▼
┌─────────────────────────────┐
│      agent_health           │
├─────────────────────────────┤
│ id (PK)                     │
│ instance_id (FK)            │
│ healthy                     │
│ status                      │
│ status_time_unix_nano       │
│ last_error                  │
│ component_health_summary    │
│ created_at                  │
└─────────────────────────────┘
```

### Detailed Tables

#### 1. **users**
Stores backend system users.

| Field | Type | Description |
|-------|------|-----------|
| id | INTEGER | Primary key |
| name | VARCHAR(255) | Full name |
| email | VARCHAR(255) | Email (unique) |
| login | VARCHAR(100) | Login (unique) |
| password_hash | VARCHAR(255) | Bcrypt password hash |
| is_active | BOOLEAN | Active/inactive status |
| created_at | TIMESTAMP | Creation date |
| updated_at | TIMESTAMP | Update date |

**Indexes:**
- `ix_users_email` (UNIQUE)
- `ix_users_login` (UNIQUE)

#### 2. **agents**
Stores OpAMP agent information.

| Field | Type | Description |
|-------|------|-----------|
| id | INTEGER | Primary key |
| instance_id | VARCHAR(255) | Agent ID (unique) |
| host_name | VARCHAR(255) | Host name |
| os_type | VARCHAR(100) | OS type |
| os_description | VARCHAR(500) | OS description |
| healthy | BOOLEAN | Health status |
| status_sync | VARCHAR(50) | IN_SYNC / OUT_OF_SYNC / UNKNOWN |
| alert_config | BOOLEAN | Divergence alert |
| is_connected | BOOLEAN | Connection status |
| started_at | TIMESTAMP | Agent start date |
| last_seen_at | TIMESTAMP | Last seen |
| created_at | TIMESTAMP | Creation date |
| updated_at | TIMESTAMP | Update date |

**Indexes:**
- `ix_agents_instance_id` (UNIQUE)
- `idx_agent_status` (status_sync, is_connected)
- `idx_agent_alert` (alert_config)

#### 3. **agent_health**
Agent health history.

| Field | Type | Description |
|-------|------|-----------|
| id | INTEGER | Primary key |
| instance_id | VARCHAR(255) | FK to agents |
| healthy | BOOLEAN | Health status |
| status | VARCHAR(100) | StatusOK, StatusFailed, etc |
| status_time_unix_nano | BIGINT | Unix nano timestamp |
| last_error | TEXT | Last error |
| component_health_summary | TEXT | Component summary |
| created_at | TIMESTAMP | Creation date |

**Indexes:**
- `ix_agent_health_instance_id`
- `idx_health_instance_created` (instance_id, created_at)

**⚠️ Record Limitation:**
- System automatically maintains only the **last 5 records** per agent
- Cleanup executed at each OpAMP synchronization
- Ensures performance and database growth control

#### 4. **agent_pipeline_health** ⭐ NEW
Current state of components and pipelines for each agent (hierarchical structure).

| Field | Type | Description |
|-------|------|-----------|
| id | INTEGER | Primary key |
| instance_id | VARCHAR(255) | FK to agents |
| component_type | VARCHAR(50) | Type: extensions, pipeline, extension, exporter, processor, receiver |
| component_name | VARCHAR(255) | Component name |
| parent_pipeline | VARCHAR(255) | Parent pipeline (for sub-components) |
| healthy | BOOLEAN | Component health status |
| status | VARCHAR(100) | StatusOK, StatusFailed, etc |
| status_time_unix_nano | BIGINT | Unix nano timestamp |
| last_error | TEXT | Component last error |
| created_at | TIMESTAMP | Creation date |

**Indexes:**
- `ix_agent_pipeline_health_instance_id`
- `idx_pipeline_health_instance_created` (instance_id, created_at)
- `idx_pipeline_health_component` (component_type, component_name)
- `idx_pipeline_health_parent` (parent_pipeline)

**⚠️ Behavior:**
- **Does not maintain history** - each synchronization completely replaces the data
- At each sync, all old agent records are deleted
- Records the current state of ALL agent components in hierarchical structure
- **Collected components:**
  - `extensions` (general group)
  - `extension:xxx` (individual extensions, e.g.: opamp, zpages)
  - `pipeline:xxx` (pipelines, e.g.: metrics/base)
  - `exporter:xxx`, `processor:xxx`, `receiver:xxx` (pipeline sub-components)
- Ideal for current state visualization, not for historical analysis

#### 5. **agent_configs**
Agent configuration versioning.

| Field | Type | Description |
|-------|------|-----------|
| id | INTEGER | Primary key |
| instance_id | VARCHAR(255) | FK to agents |
| version | INTEGER | Version number |
| effective_config | TEXT | YAML/JSON configuration |
| config_hash | VARCHAR(64) | SHA256 hash for detection |
| source | VARCHAR(50) | SYNC_JOB / MANUAL_UPDATE / API_UPDATE |
| updated_by_user_id | INTEGER | FK to users (nullable) |
| created_at | TIMESTAMP | Creation date |
| updated_at | TIMESTAMP | Update date |

**Indexes:**
- `ix_agent_configs_instance_id`
- `idx_config_instance_version` (instance_id, version)
- `idx_config_hash` (config_hash)

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Aplicação FastAPI principal
│   ├── background.py              # Background tasks (sync periódico)
│   ├── dependencies.py            # Dependencies FastAPI (auth, db)
│   ├── schemas.py                 # Pydantic schemas
│   │
│   ├── core/                      # Configurações core
│   │   ├── __init__.py
│   │   ├── config.py              # Settings (Pydantic Settings)
│   │   ├── database.py            # Database session e engine
│   │   └── security.py            # JWT, password hashing
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── models.py              # User, Agent, AgentHealth, AgentPipelineHealth, AgentConfig
│   │
│   ├── repositories/              # Data access layer
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   ├── agent_repository.py
│   │   ├── agent_health_repository.py
│   │   ├── agent_pipeline_health_repository.py  # ⭐ NOVO
│   │   └── agent_config_repository.py
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py        # Autenticação
│   │   └── opamp_service.py       # Integração OpAMP + Pipeline Health
│   │
│   └── routers/                   # API endpoints
│       ├── __init__.py
│       ├── auth.py                # /auth/*
│       ├── agents.py              # /agents/* + /agents/{id}/pipelines/health ⭐
│       ├── config.py              # /config/*
│       └── opamp.py               # /opamp/sync
│
├── alembic/                       # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial.py         # Initial migration
│       └── 002_add_pipeline_health.py  # ⭐ NOVO - Pipeline health table
│
├── alembic.ini                    # Alembic configuration
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container build
├── .env                           # Environment variables
├── .env.example                   # Example env file
└── .gitignore
```

---

## 🚀 Instalação e Execução

### Pré-requisitos

- Docker & Docker Compose
- Git

### 1. Clone o repositório

```bash
git clone <repository-url>
cd AmpBridge/opamp-stack
```

### 2. Configure variáveis de ambiente

```bash
cd backend
cp .env.example .env
```

**Importante:** Altere o `SECRET_KEY` em produção:

```bash
# Gerar nova secret key
openssl rand -hex 32
```

Edite `backend/.env` e substitua:
```env
SECRET_KEY=<sua-chave-gerada>
```

### 3. Suba os containers

```bash
cd ..  # volta para opamp-stack/
docker compose up -d
```

Isso irá subir:
- **postgres**: Banco de dados PostgreSQL
- **opamp-server**: Servidor OpAMP
- **backend**: API Backend FastAPI
- **haproxy**: Load balancer (se configurado)

### 4. Verifique os serviços

```bash
docker compose ps
```

Todos os serviços devem estar "healthy".

### 5. Acesse a documentação da API

Abra no navegador:
```
http://localhost:8000/docs
```

---

## �️ Consultando as Tabelas no PostgreSQL

O banco de dados PostgreSQL roda em um container Docker. Você pode acessá-lo diretamente para consultar as tabelas.

### Método 1: Acessar o PostgreSQL via `psql`

#### Conectar ao container e abrir o terminal `psql`:
```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db
```

#### Comandos úteis do `psql`:

**Listar todas as tabelas:**
```sql
\dt
```

**Descrever estrutura de uma tabela:**
```sql
\d users
\d agents
\d agent_health
\d agent_pipeline_health
\d agent_configs
```

**Listar todos os usuários:**
```sql
SELECT id, name, email, login, is_active, created_at FROM users;
```

**Listar todos os agents:**
```sql
SELECT instance_id, last_connection_time, is_connected, status_sync, alert_config 
FROM agents 
ORDER BY last_connection_time DESC;
```

**Verificar histórico de health de um agent:**
```sql
SELECT instance_id, healthy, status, last_error, created_at 
FROM agent_health 
WHERE instance_id = 'agent-123'
ORDER BY created_at DESC 
LIMIT 10;
```

**Verificar componentes e pipelines de um agent:** ⭐ NOVO
```sql
-- Todos os componentes
SELECT component_type, component_name, parent_pipeline, healthy, status, created_at 
FROM agent_pipeline_health 
WHERE instance_id = 'agent-123'
ORDER BY component_type, component_name;

-- Apenas pipelines principais
SELECT component_name, healthy, status, created_at 
FROM agent_pipeline_health 
WHERE instance_id = 'agent-123' AND component_type = 'pipeline';

-- Componentes de um pipeline específico
SELECT component_type, component_name, healthy, status 
FROM agent_pipeline_health 
WHERE instance_id = 'agent-123' AND parent_pipeline = 'metrics/base';
```

**Nota:** Apenas o estado atual dos componentes é mantido (sem histórico).

**Listar versionamento de configurações:**
```sql
SELECT instance_id, version, source, config_hash, created_at 
FROM agent_configs 
WHERE instance_id = 'agent-123'
ORDER BY version DESC;
```

**Verificar última configuração de cada agent:**
```sql
SELECT DISTINCT ON (instance_id) 
    instance_id, version, source, created_at
FROM agent_configs
ORDER BY instance_id, version DESC;
```

**Agents com alertas ativos:**
```sql
SELECT instance_id, last_connection_time, status_sync 
FROM agents 
WHERE alert_config = true;
```

**Health check dos agents:**
```sql
SELECT a.instance_id, a.is_connected, ah.healthy, ah.status, ah.last_error
FROM agents a
LEFT JOIN LATERAL (
    SELECT healthy, status, last_error, created_at
    FROM agent_health
    WHERE instance_id = a.instance_id
    ORDER BY created_at DESC
    LIMIT 1
) ah ON true
ORDER BY a.last_connection_time DESC;
```

**Sair do psql:**
```sql
\q
```

### Método 2: Executar consultas diretas do terminal

Executar uma consulta SQL sem entrar no `psql`:

```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agents;"
```

```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT instance_id, is_connected FROM agents ORDER BY last_connection_time DESC LIMIT 5;"
```

### Método 3: Backup e Restore

**Fazer backup do banco:**
```bash
docker exec -t opamp-postgres pg_dump -U opamp opamp_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Restaurar backup:**
```bash
cat backup_20251117_100000.sql | docker exec -i opamp-postgres psql -U opamp -d opamp_db
```

### Método 4: Cliente GUI (Opcional)

Você pode usar clientes GUI como **pgAdmin**, **DBeaver** ou **TablePlus** para conectar ao banco:

**Connection credentials:**
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `opamp_db`
- **User:** `opamp`
- **Password:** `opamp123` (as defined in `docker-compose.yml`)

---

## �📡 Endpoints da API

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication

#### `POST /api/v1/auth/register`
Register a new user.

**Request Body:**
```json
{
  "name": "Admin User",
  "email": "admin@example.com",
  "login": "admin",
  "password": "strongpassword123"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "Admin User",
  "email": "admin@example.com",
  "login": "admin",
  "is_active": true,
  "created_at": "2025-11-17T10:00:00Z",
  "updated_at": "2025-11-17T10:00:00Z"
}
```

#### `POST /api/v1/auth/login`
Authenticate user and return JWT token.

**Request Body:**
```json
{
  "login": "admin",
  "password": "strongpassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### `GET /api/v1/auth/me`
Return authenticated user information.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Admin User",
  "email": "admin@example.com",
  "login": "admin",
  "is_active": true,
  "created_at": "2025-11-17T10:00:00Z",
  "updated_at": "2025-11-17T10:00:00Z"
}
```

---

### Agents

#### `GET /api/v1/agents`
List all agents with pagination.

**Query Parameters:**
- `page` (default: 1): Page number
- `page_size` (default: 50, max: 500): Items per page

**Response:** `200 OK`
```json
{
  "total": 150,
  "page": 1,
  "page_size": 50,
  "agents": [
    {
      "id": 1,
      "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
      "host_name": "DESKTOP-C49UQO6",
      "os_type": "windows",
      "os_description": "Microsoft Windows 11 Pro 23H2",
      "healthy": true,
      "status_sync": "IN_SYNC",
      "alert_config": false,
      "is_connected": true,
      "started_at": "2025-11-17T21:40:51Z",
      "last_seen_at": "2025-11-17T22:00:00Z",
      "created_at": "2025-11-17T20:00:00Z",
      "updated_at": "2025-11-17T22:00:00Z"
    }
  ]
}
```

#### `GET /api/v1/agents/{instance_id}`
Details of a specific agent.

**Response:** `200 OK`
```json
{
  "id": 1,
  "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
  "host_name": "DESKTOP-C49UQO6",
  "os_type": "windows",
  "os_description": "Microsoft Windows 11 Pro 23H2",
  "healthy": true,
  "status_sync": "IN_SYNC",
  "alert_config": false,
  "is_connected": true,
  "started_at": "2025-11-17T21:40:51Z",
  "last_seen_at": "2025-11-17T22:00:00Z",
  "created_at": "2025-11-17T20:00:00Z",
  "updated_at": "2025-11-17T22:00:00Z"
}
```

#### `GET /api/v1/agents/{instance_id}/health`
Health history of an agent.

**Query Parameters:**
- `limit` (default: 100, max: 1000): Number of records

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
    "healthy": true,
    "status": "StatusOK",
    "status_time_unix_nano": 1763415651056355200,
    "last_error": null,
    "component_health_summary": null,
    "created_at": "2025-11-17T22:00:00Z"
  }
]
```

**⚠️ Note:** The system automatically maintains only the last 5 records per agent.

#### `GET /api/v1/agents/{instance_id}/pipelines/health` ⭐ NEW
Current health status of agent pipelines.

**Query Parameters:**
- `pipeline_name` (optional): Filter by specific pipeline
- `limit` (default: 100, max: 1000): Number of records

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
    "pipeline_name": "metrics/base",
    "healthy": true,
    "status": "StatusOK",
    "status_time_unix_nano": 1763415651056355200,
    "last_error": null,
    "created_at": "2025-11-18T13:32:00Z"
  }
]
```

**⚠️ Note:** 
- Does not maintain history - returns only current pipeline state
- Data is replaced at each synchronization (60s)
- Ideal for real-time monitoring

**Example - Filter by pipeline:**
```bash
curl "http://localhost:8000/api/v1/agents/{instance_id}/pipelines/health?pipeline_name=metrics/base"
```

#### `GET /api/v1/agents/{instance_id}/configs`
Configuration history of an agent.

**Query Parameters:**
- `limit` (default: 100, max: 1000): Number of versions

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
    "version": 3,
    "effective_config": "receivers:\n  otlp:\n    protocols:...",
    "config_hash": "a1b2c3d4e5f6...",
    "source": "API_UPDATE",
    "updated_by_user_id": 1,
    "created_at": "2025-11-17T22:00:00Z",
    "updated_at": "2025-11-17T22:00:00Z"
  }
]
```

#### `GET /api/v1/agents/{instance_id}/config`
Download YAML configuration file.

**Query Parameters:**
- `version` (optional): Specific version (default: latest)

**Response:** `200 OK`
```
Content-Type: application/x-yaml
Content-Disposition: attachment; filename=agent_<instance_id>_config_v3.yaml

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
...
```

#### `GET /api/v1/agents/csv`
Export all agents to CSV.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```
Content-Type: text/csv
Content-Disposition: attachment; filename=agents_export.csv

Instance ID,Host Name,OS Type,...
019a7534-f534-70ab-bbbc-115e2d231708,DESKTOP-C49UQO6,windows,...
```

---

### Configuration

#### `POST /api/v1/config?instance_id=<id>`
Update agent configuration.

**Headers:**
```
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "config": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Custom configuration updated successfully",
  "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
  "version": 4,
  "status_ready": true
}
```

---

### OpAMP Sync

#### `POST /api/v1/opamp/sync`
Manual synchronization with OpAMP server.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Synchronized 10 agents",
  "agents_processed": 10,
  "agents_updated": 10,
  "configs_versioned": 2,
  "errors": []
}
```

---

## 🔧 Usage Examples

### 1. Registration and Login

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin User",
    "email": "admin@example.com",
    "login": "admin",
    "password": "strongpassword123"
  }'

# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "strongpassword123"
  }' | jq -r '.access_token')

echo $TOKEN
```

### 2. List Agents

```bash
# Without authentication (public endpoint)
curl http://localhost:8000/api/v1/agents?page=1&page_size=10 | jq

# With pagination
curl http://localhost:8000/api/v1/agents?page=2&page_size=20 | jq
```

### 3. Agent Details

```bash
INSTANCE_ID="019a7534-f534-70ab-bbbc-115e2d231708"

curl http://localhost:8000/api/v1/agents/$INSTANCE_ID | jq
```

### 4. Health History

```bash
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/health?limit=50" | jq
```

### 5. Configuration History

```bash
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs?limit=10" | jq
```

### 6. Download Configuration

```bash
# Latest version
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config" \
  -o config.yaml

# Specific version
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config?version=2" \
  -o config_v2.yaml
```

### 7. Export Agents to CSV

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/csv \
  -o agents.csv
```

### 8. Update Agent Configuration

```bash
curl -X POST "http://localhost:8000/api/v1/config?instance_id=$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317\n      http:\n        endpoint: 0.0.0.0:4318"
  }' | jq
```

### 9. Manual Synchronization

```bash
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 🔄 OpAMP Synchronization

### 1. Automatic Job (Background Task)

The backend automatically executes a synchronization job every **60 seconds** (configurable via `OPAMP_SYNC_INTERVAL_SECONDS`).

**How it works:**

1. Makes GET to `http://opamp-server:4321/agents/full`
2. For each returned agent:
   - Updates/inserts basic data in `agents`
   - Creates health record in `agent_health`
   - Checks if `effective_config` changed (via SHA256 hash)
   - If changed:
     - Creates new version in `agent_configs`
     - Marks `alert_config = true` and `status_sync = OUT_OF_SYNC`
   - If not changed and there was an alert:
     - Clears `alert_config` and marks `status_sync = IN_SYNC`
3. Marks as disconnected (`is_connected = false`) agents that are no longer in OpAMP

**Logs:**
```
INFO - Running OpAMP sync...
INFO - OpAMP sync completed: 10 processed, 10 updated, 2 configs versioned
```

### 2. Manual Synchronization Endpoint

Allows triggering synchronization on demand via:
```bash
POST /api/v1/opamp/sync
```

Useful for:
- Testing synchronization
- Forcing immediate update
- Integration with external webhooks

---

## 📦 Configuration Versioning

### How It Works

1. **Change Detection:**
   - Calculates SHA256 hash of `effective_config`
   - Compares with hash of last stored version

2. **Creating New Version:**
   - If different hash:
     - Increments `version`
     - Saves new entry in `agent_configs`
     - Records `source` (SYNC_JOB, API_UPDATE, MANUAL_UPDATE)
     - If from API, records `updated_by_user_id`

3. **Divergence Alert:**
   - Marks `alert_config = true` on agent
   - Updates `status_sync = OUT_OF_SYNC`

4. **Resolution:**
   - When config is updated via API (`POST /config`)
   - Backend sends to OpAMP (`/save_config/json`)
   - If successful, clears alert and marks `status_sync = IN_SYNC`

### Example Flow

```
┌──────────────┐
│ OpAMP Sync   │
│  (Job)       │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Fetch /agents/full   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐      Different hash?
│ Compute config hash  │────────► YES ─────┐
└──────────────────────┘                   │
                                           ▼
                                  ┌─────────────────┐
                                  │ Create new      │
                                  │ version in DB   │
                                  └────────┬────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │ Set alert_      │
                                  │ config = true   │
                                  └─────────────────┘
```

### Query Agents with Alerts

```bash
# Via API (future endpoint or filter)
curl "http://localhost:8000/api/v1/agents?alert_config=true" | jq

# Via direct SQL
docker exec -it opamp-postgres psql -U opamp -d opamp_db \
  -c "SELECT instance_id, host_name, alert_config FROM agents WHERE alert_config = true;"
```

---

## 🧪 Testing and Development

### Run locally (without Docker)

```bash
cd backend

# Create virtual env
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
# Edit .env with local settings

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

### Access database

```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db
```

Useful queries:
```sql
-- View all agents
SELECT instance_id, host_name, healthy, status_sync, alert_config FROM agents;

-- View configs with alerts
SELECT a.instance_id, a.host_name, c.version, c.created_at
FROM agents a
JOIN agent_configs c ON a.instance_id = c.instance_id
WHERE a.alert_config = true
ORDER BY c.created_at DESC;

-- Health history
SELECT instance_id, healthy, status, created_at
FROM agent_health
WHERE instance_id = '019a7534-f534-70ab-bbbc-115e2d231708'
ORDER BY created_at DESC
LIMIT 10;
```

### Container logs

```bash
# Backend
docker logs -f opamp-backend

# OpAMP Server
docker logs -f opamp-server

# PostgreSQL
docker logs -f opamp-postgres
```

---

## 🔒 Security

### JWT Authentication

- Tokens expire in 30 minutes (configurable)
- Passwords hashed with bcrypt
- Secret key must be changed in production

### Protected Endpoints

Require header `Authorization: Bearer <token>`:
- `POST /api/v1/config`
- `POST /api/v1/opamp/sync`
- `GET /api/v1/agents/csv`
- `GET /api/v1/auth/me`

### Production Recommendations

1. **Secret Key:**
   ```bash
   openssl rand -hex 32
   ```

2. **CORS:**
   Edit `app/main.py` and configure allowed origins:
   ```python
   allow_origins=["https://your-frontend.com"]
   ```

3. **HTTPS:**
   Use reverse proxy (nginx, Traefik) with SSL certificates

4. **Rate Limiting:**
   Add rate limiting middleware

5. **Database:**
   Use strong password and restricted access

---

## 📊 Monitoring

### Health Checks

```bash
# Backend
curl http://localhost:8000/health

# OpAMP Server
curl http://localhost:4321/

# PostgreSQL
docker exec opamp-postgres pg_isready -U opamp
```

### Metrics

The background task logs statistics at each sync:
- Processed agents
- Updated agents
- Versioned configs
- Errors

---

## 🐛 Troubleshooting

### Backend doesn't connect to database

```bash
# Check if postgres is healthy
docker compose ps

# Check connection
docker exec opamp-backend env | grep DATABASE_URL
```

### Synchronization doesn't happen

```bash
# Check logs
docker logs -f opamp-backend

# Check if OpAMP is accessible
docker exec opamp-backend curl http://opamp-server:4321/agents/full
```

### Authentication error

```bash
# Check if token is valid
echo $TOKEN

# Try login again
# Check if user is active
```

---

## 📝 TODO / Future Improvements

- [ ] Implement roles/permissions (admin, viewer, etc.)
- [ ] Add advanced filters in agent listing
- [ ] Implement webhooks for alert notifications
- [ ] Metrics dashboard (Grafana integration)
- [ ] Automated tests (pytest)
- [ ] CI/CD pipeline
- [ ] Rate limiting
- [ ] User action audit log

---

## 📄 License

This project is under the license specified in the repository LICENSE file.

---

## 👥 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## 📧 Support

For questions and support, open an issue in the repository.

---

**Developed with ❤️ using FastAPI**
