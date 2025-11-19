# OpAMP Backend API

Sistema backend completo para gerenciamento e sincronização de agents OpAMP, com API REST, autenticação JWT, versionamento de configurações e sincronização automática.

---

## 📋 Índice

- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Modelagem do Banco de Dados](#modelagem-do-banco-de-dados)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Instalação e Execução](#instalação-e-execução)
- [Endpoints da API](#endpoints-da-api)
- [Exemplos de Uso](#exemplos-de-uso)
- [Sincronização com OpAMP](#sincronização-com-opamp)
- [Versionamento de Configurações](#versionamento-de-configurações)

---

## 🏗️ Arquitetura

### Stack Escolhida: **FastAPI + PostgreSQL + SQLAlchemy**

**Justificativa da escolha:**

1. **FastAPI**: Framework moderno e de alto desempenho para APIs em Python
   - Suporte nativo a async/await
   - Validação automática com Pydantic
   - Documentação automática (Swagger/OpenAPI)
   - Excelente performance (comparável a Node.js e Go)

2. **PostgreSQL**: Banco de dados relacional robusto
   - ACID compliance
   - Suporte a JSON para dados flexíveis
   - Excelente para versionamento e histórico

3. **SQLAlchemy 2.0**: ORM moderno com suporte async
   - Migrations com Alembic
   - Type hints completos
   - Performance otimizada

### Camadas da Aplicação

```
┌─────────────────────────────────────┐
│         Routers (API Layer)         │  ← Endpoints REST
├─────────────────────────────────────┤
│      Services (Business Logic)      │  ← Regras de negócio
├─────────────────────────────────────┤
│    Repositories (Data Access)       │  ← Acesso a dados
├─────────────────────────────────────┤
│      Models (Database Layer)        │  ← SQLAlchemy Models
└─────────────────────────────────────┘
```

**Componentes principais:**

- **Routers**: Definem endpoints e validação de requests/responses
- **Services**: Implementam lógica de negócio (sync OpAMP, versionamento)
- **Repositories**: Encapsulam operações de banco de dados
- **Models**: Definem estrutura das tabelas (SQLAlchemy)
- **Schemas**: Validação de dados (Pydantic)
- **Core**: Configuração, segurança, database

---

## 💻 Stack Tecnológica

| Componente | Tecnologia | Versão |
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

## 🗄️ Modelagem do Banco de Dados

### Diagrama ER

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

### Tabelas Detalhadas

#### 1. **users**
Armazena usuários do sistema backend.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER | Chave primária |
| name | VARCHAR(255) | Nome completo |
| email | VARCHAR(255) | Email (único) |
| login | VARCHAR(100) | Login (único) |
| password_hash | VARCHAR(255) | Hash bcrypt da senha |
| is_active | BOOLEAN | Status ativo/inativo |
| created_at | TIMESTAMP | Data de criação |
| updated_at | TIMESTAMP | Data de atualização |

**Índices:**
- `ix_users_email` (UNIQUE)
- `ix_users_login` (UNIQUE)

#### 2. **agents**
Armazena informações dos agents OpAMP.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER | Chave primária |
| instance_id | VARCHAR(255) | ID do agent (único) |
| host_name | VARCHAR(255) | Nome do host |
| os_type | VARCHAR(100) | Tipo de SO |
| os_description | VARCHAR(500) | Descrição do SO |
| healthy | BOOLEAN | Status de saúde |
| status_sync | VARCHAR(50) | IN_SYNC / OUT_OF_SYNC / UNKNOWN |
| alert_config | BOOLEAN | Alerta de divergência |
| is_connected | BOOLEAN | Status de conexão |
| started_at | TIMESTAMP | Data de início do agent |
| last_seen_at | TIMESTAMP | Última vez visto |
| created_at | TIMESTAMP | Data de criação |
| updated_at | TIMESTAMP | Data de atualização |

**Índices:**
- `ix_agents_instance_id` (UNIQUE)
- `idx_agent_status` (status_sync, is_connected)
- `idx_agent_alert` (alert_config)

#### 3. **agent_health**
Histórico de saúde dos agents.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER | Chave primária |
| instance_id | VARCHAR(255) | FK para agents |
| healthy | BOOLEAN | Status de saúde |
| status | VARCHAR(100) | StatusOK, StatusFailed, etc |
| status_time_unix_nano | BIGINT | Timestamp Unix nano |
| last_error | TEXT | Último erro |
| component_health_summary | TEXT | Resumo de componentes |
| created_at | TIMESTAMP | Data de criação |

**Índices:**
- `ix_agent_health_instance_id`
- `idx_health_instance_created` (instance_id, created_at)

**⚠️ Limitação de Registros:**
- Sistema mantém automaticamente apenas os **últimos 10 registros** por agent
- Limpeza executada a cada sincronização com OpAMP
- Garante performance e controle do crescimento do banco

#### 4. **agent_pipeline_health** ⭐ NOVO
Estado atual dos componentes e pipelines de cada agent (estrutura hierárquica).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER | Chave primária |
| instance_id | VARCHAR(255) | FK para agents |
| component_type | VARCHAR(50) | Tipo: extensions, pipeline, extension, exporter, processor, receiver |
| component_name | VARCHAR(255) | Nome do componente |
| parent_pipeline | VARCHAR(255) | Pipeline pai (para sub-componentes) |
| healthy | BOOLEAN | Status de saúde do componente |
| status | VARCHAR(100) | StatusOK, StatusFailed, etc |
| status_time_unix_nano | BIGINT | Timestamp Unix nano |
| last_error | TEXT | Último erro do componente |
| created_at | TIMESTAMP | Data de criação |

**Índices:**
- `ix_agent_pipeline_health_instance_id`
- `idx_pipeline_health_instance_created` (instance_id, created_at)
- `idx_pipeline_health_component` (component_type, component_name)
- `idx_pipeline_health_parent` (parent_pipeline)

**⚠️ Comportamento:**
- **Não mantém histórico** - cada sincronização substitui completamente os dados
- A cada sync, todos os registros antigos do agent são deletados
- Grava o estado atual de TODOS os componentes do agent em estrutura hierárquica
- **Componentes coletados:**
  - `extensions` (grupo geral)
  - `extension:xxx` (extensões individuais, ex: opamp, zpages)
  - `pipeline:xxx` (pipelines, ex: metrics/base)
  - `exporter:xxx`, `processor:xxx`, `receiver:xxx` (sub-componentes dos pipelines)
- Ideal para visualização do estado atual, não para análise histórica

#### 5. **agent_configs**
Versionamento de configurações dos agents.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER | Chave primária |
| instance_id | VARCHAR(255) | FK para agents |
| version | INTEGER | Número da versão |
| effective_config | TEXT | Configuração YAML/JSON |
| config_hash | VARCHAR(64) | SHA256 hash para detecção |
| source | VARCHAR(50) | SYNC_JOB / MANUAL_UPDATE / API_UPDATE |
| updated_by_user_id | INTEGER | FK para users (nullable) |
| created_at | TIMESTAMP | Data de criação |
| updated_at | TIMESTAMP | Data de atualização |

**Índices:**
- `ix_agent_configs_instance_id`
- `idx_config_instance_version` (instance_id, version)
- `idx_config_hash` (config_hash)

---

## 📁 Estrutura do Projeto

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

**Credenciais de conexão:**
- **Host:** `localhost`
- **Porta:** `5432`
- **Database:** `opamp_db`
- **Usuário:** `opamp`
- **Senha:** `opamp123` (conforme definido no `docker-compose.yml`)

---

## �📡 Endpoints da API

### Base URL
```
http://localhost:8000/api/v1
```

### Autenticação

#### `POST /api/v1/auth/register`
Registra um novo usuário.

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
Autentica usuário e retorna token JWT.

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
Retorna informações do usuário autenticado.

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
Lista todos os agents com paginação.

**Query Parameters:**
- `page` (default: 1): Número da página
- `page_size` (default: 50, max: 500): Itens por página

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
Detalhes de um agent específico.

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
Histórico de saúde de um agent.

**Query Parameters:**
- `limit` (default: 100, max: 1000): Número de registros

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

**⚠️ Nota:** O sistema mantém automaticamente apenas os últimos 10 registros por agent.

#### `GET /api/v1/agents/{instance_id}/pipelines/health` ⭐ NOVO
Estado atual da saúde dos pipelines de um agent.

**Query Parameters:**
- `pipeline_name` (optional): Filtrar por pipeline específico
- `limit` (default: 100, max: 1000): Número de registros

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

**⚠️ Nota:** 
- Não mantém histórico - retorna apenas o estado atual dos pipelines
- Dados são substituídos a cada sincronização (60s)
- Ideal para monitoramento em tempo real

**Exemplo - Filtrar por pipeline:**
```bash
curl "http://localhost:8000/api/v1/agents/{instance_id}/pipelines/health?pipeline_name=metrics/base"
```

#### `GET /api/v1/agents/{instance_id}/configs`
Histórico de configurações de um agent.

**Query Parameters:**
- `limit` (default: 100, max: 1000): Número de versões

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
Download do arquivo YAML de configuração.

**Query Parameters:**
- `version` (optional): Versão específica (default: última)

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
Exporta todos os agents para CSV.

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
Atualiza configuração de um agent.

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
Sincronização manual com OpAMP server.

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

## 🔧 Exemplos de Uso

### 1. Registro e Login

```bash
# Registrar usuário
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

### 2. Listar Agents

```bash
# Sem autenticação (endpoint público)
curl http://localhost:8000/api/v1/agents?page=1&page_size=10 | jq

# Com paginação
curl http://localhost:8000/api/v1/agents?page=2&page_size=20 | jq
```

### 3. Detalhes de um Agent

```bash
INSTANCE_ID="019a7534-f534-70ab-bbbc-115e2d231708"

curl http://localhost:8000/api/v1/agents/$INSTANCE_ID | jq
```

### 4. Histórico de Saúde

```bash
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/health?limit=50" | jq
```

### 5. Histórico de Configurações

```bash
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs?limit=10" | jq
```

### 6. Download de Configuração

```bash
# Última versão
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config" \
  -o config.yaml

# Versão específica
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config?version=2" \
  -o config_v2.yaml
```

### 7. Exportar Agents para CSV

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/csv \
  -o agents.csv
```

### 8. Atualizar Configuração de um Agent

```bash
curl -X POST "http://localhost:8000/api/v1/config?instance_id=$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317\n      http:\n        endpoint: 0.0.0.0:4318"
  }' | jq
```

### 9. Sincronização Manual

```bash
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 🔄 Sincronização com OpAMP

### 1. Job Automático (Background Task)

O backend executa automaticamente um job de sincronização a cada **60 segundos** (configurável via `OPAMP_SYNC_INTERVAL_SECONDS`).

**Funcionamento:**

1. Faz GET para `http://opamp-server:4321/agents/full`
2. Para cada agent retornado:
   - Atualiza/insere dados básicos em `agents`
   - Cria registro de health em `agent_health`
   - Verifica se o `effective_config` mudou (via hash SHA256)
   - Se mudou:
     - Cria nova versão em `agent_configs`
     - Marca `alert_config = true` e `status_sync = OUT_OF_SYNC`
   - Se não mudou e havia alerta:
     - Limpa `alert_config` e marca `status_sync = IN_SYNC`
3. Marca como desconectados (`is_connected = false`) agents que não estão mais no OpAMP

**Logs:**
```
INFO - Running OpAMP sync...
INFO - OpAMP sync completed: 10 processed, 10 updated, 2 configs versioned
```

### 2. Endpoint de Sincronização Manual

Permite disparar sincronização sob demanda via:
```bash
POST /api/v1/opamp/sync
```

Útil para:
- Testar sincronização
- Forçar atualização imediata
- Integração com webhooks externos

---

## 📦 Versionamento de Configurações

### Como Funciona

1. **Detecção de Mudança:**
   - Calcula SHA256 hash do `effective_config`
   - Compara com o hash da última versão armazenada

2. **Criação de Nova Versão:**
   - Se hash diferente:
     - Incrementa `version`
     - Salva nova entrada em `agent_configs`
     - Registra `source` (SYNC_JOB, API_UPDATE, MANUAL_UPDATE)
     - Se vindo da API, registra `updated_by_user_id`

3. **Alerta de Divergência:**
   - Marca `alert_config = true` no agent
   - Atualiza `status_sync = OUT_OF_SYNC`

4. **Resolução:**
   - Quando config é atualizado via API (`POST /config`)
   - Backend envia para OpAMP (`/save_config/json`)
   - Se sucesso, limpa alerta e marca `status_sync = IN_SYNC`

### Exemplo de Fluxo

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
┌──────────────────────┐      Hash diferente?
│ Compute config hash  │────────► SIM ─────┐
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

### Consultar Agents com Alertas

```bash
# Via API (endpoint futuro ou filtro)
curl "http://localhost:8000/api/v1/agents?alert_config=true" | jq

# Via SQL direto
docker exec -it opamp-postgres psql -U opamp -d opamp_db \
  -c "SELECT instance_id, host_name, alert_config FROM agents WHERE alert_config = true;"
```

---

## 🧪 Testes e Desenvolvimento

### Executar localmente (sem Docker)

```bash
cd backend

# Criar virtual env
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env com configurações locais

# Rodar migrations
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

### Acessar banco de dados

```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db
```

Queries úteis:
```sql
-- Ver todos os agents
SELECT instance_id, host_name, healthy, status_sync, alert_config FROM agents;

-- Ver configs com alertas
SELECT a.instance_id, a.host_name, c.version, c.created_at
FROM agents a
JOIN agent_configs c ON a.instance_id = c.instance_id
WHERE a.alert_config = true
ORDER BY c.created_at DESC;

-- Histórico de health
SELECT instance_id, healthy, status, created_at
FROM agent_health
WHERE instance_id = '019a7534-f534-70ab-bbbc-115e2d231708'
ORDER BY created_at DESC
LIMIT 10;
```

### Logs dos containers

```bash
# Backend
docker logs -f opamp-backend

# OpAMP Server
docker logs -f opamp-server

# PostgreSQL
docker logs -f opamp-postgres
```

---

## 🔒 Segurança

### JWT Authentication

- Tokens expiram em 30 minutos (configurável)
- Senhas hasheadas com bcrypt
- Secret key deve ser alterada em produção

### Endpoints Protegidos

Requerem header `Authorization: Bearer <token>`:
- `POST /api/v1/config`
- `POST /api/v1/opamp/sync`
- `GET /api/v1/agents/csv`
- `GET /api/v1/auth/me`

### Recomendações para Produção

1. **Secret Key:**
   ```bash
   openssl rand -hex 32
   ```

2. **CORS:**
   Edite `app/main.py` e configure origins permitidos:
   ```python
   allow_origins=["https://seu-frontend.com"]
   ```

3. **HTTPS:**
   Use reverse proxy (nginx, Traefik) com certificados SSL

4. **Rate Limiting:**
   Adicione middleware de rate limiting

5. **Database:**
   Use senha forte e acesso restrito

---

## 📊 Monitoramento

### Health Checks

```bash
# Backend
curl http://localhost:8000/health

# OpAMP Server
curl http://localhost:4321/

# PostgreSQL
docker exec opamp-postgres pg_isready -U opamp
```

### Métricas

O background task loga estatísticas a cada sync:
- Agents processados
- Agents atualizados
- Configs versionados
- Erros

---

## 🐛 Troubleshooting

### Backend não conecta ao banco

```bash
# Verificar se postgres está healthy
docker compose ps

# Verificar conexão
docker exec opamp-backend env | grep DATABASE_URL
```

### Sincronização não acontece

```bash
# Verificar logs
docker logs -f opamp-backend

# Verificar se OpAMP está acessível
docker exec opamp-backend curl http://opamp-server:4321/agents/full
```

### Erro de autenticação

```bash
# Verificar se token é válido
echo $TOKEN

# Tentar login novamente
# Verificar se usuário está ativo
```

---

## 📝 TODO / Melhorias Futuras

- [ ] Implementar roles/permissions (admin, viewer, etc.)
- [ ] Adicionar filtros avançados na listagem de agents
- [ ] Implementar webhooks para notificações de alertas
- [ ] Dashboard de métricas (Grafana integration)
- [ ] Testes automatizados (pytest)
- [ ] CI/CD pipeline
- [ ] Rate limiting
- [ ] Audit log de ações de usuários

---

## 📄 Licença

Este projeto está sob a licença especificada no arquivo LICENSE do repositório.

---

## 👥 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📧 Suporte

Para questões e suporte, abra uma issue no repositório.

---

**Desenvolvido com ❤️ usando FastAPI**
