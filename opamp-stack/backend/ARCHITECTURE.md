# Arquitetura do Sistema OpAMP Backend

## Visão Geral

Este documento descreve a arquitetura completa do sistema backend OpAMP, incluindo decisões de design, fluxos de dados e integrações.

---

## 🎯 Objetivos do Sistema

1. **Sincronizar** dados de agents OpAMP periodicamente
2. **Persistir** informações de agents, health e configurações
3. **Versionar** configurações com detecção automática de mudanças
4. **Alertar** sobre divergências de configuração
5. **Expor API REST** para gestão e consultas
6. **Autenticar** usuários com JWT
7. **Integrar** com OpAMP Server para envio de novas configs

---

## 🏛️ Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐  │
│  │              │      │              │      │           │  │
│  │  OpAMP       │◄─────┤   Backend    │◄─────┤  Web App  │  │
│  │  Server      │      │   FastAPI    │      │  (Future) │  │
│  │              │      │              │      │           │  │
│  └──────┬───────┘      └──────┬───────┘      └───────────┘  │
│         │                     │                              │
│         │                     ▼                              │
│         │              ┌──────────────┐                      │
│         │              │              │                      │
│         │              │  PostgreSQL  │                      │
│         │              │              │                      │
│         │              └──────────────┘                      │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐                                            │
│  │              │                                            │
│  │   Agents     │                                            │
│  │   (OpAMP)    │                                            │
│  │              │                                            │
│  └──────────────┘                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Fluxo de Dados

### 1. Sincronização Periódica (Background Task)

```
┌──────────────────────────────────────────────────────────────┐
│                    Background Task (60s)                      │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ OpAMPService    │
                    │ sync_all_agents │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────────────┐
                    │ GET /agents/full        │
                    │ (OpAMP Server)          │
                    └────────┬────────────────┘
                             │
                             ▼
                    ┌─────────────────────────┐
                    │ Parse agent data:       │
                    │ - instance_id           │
                    │ - host_name, os_*       │
                    │ - health status         │
                    │ - effective_config      │
                    └────────┬────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Upsert Agent    │ │ Create Health   │ │ Check Config    │
│ (agents table)  │ │ (agent_health)  │ │ Hash            │
└─────────────────┘ └─────────────────┘ └────────┬────────┘
                                                  │
                                     Hash changed?│
                                                  │
                             ┌────────────────────┴────────────┐
                             │                                 │
                             ▼                                 ▼
                    ┌─────────────────┐              ┌──────────────┐
                    │ Create new      │              │ Clear alert  │
                    │ config version  │              │ if previous  │
                    │ Set alert=true  │              └──────────────┘
                    └─────────────────┘
```

### 2. Atualização de Configuração (API)

```
┌───────────────────────────────────────────────────────────┐
│  POST /api/v1/config?instance_id=xxx                      │
│  Authorization: Bearer <token>                            │
│  Body: { "config": "receivers:\n..." }                    │
└─────────────────────────┬─────────────────────────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Validate JWT    │
                 │ Get current_user│
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────────────┐
                 │ OpAMPService            │
                 │ send_config_to_opamp    │
                 └────────┬────────────────┘
                          │
                          ▼
                 ┌─────────────────────────┐
                 │ POST /save_config/json  │
                 │ (OpAMP Server)          │
                 │ - instanceid            │
                 │ - config                │
                 └────────┬────────────────┘
                          │
                    Success?
                          │
         ┌────────────────┴────────────────┐
         │                                 │
         ▼                                 ▼
┌─────────────────┐              ┌──────────────────┐
│ Create new      │              │ Return error     │
│ config version  │              └──────────────────┘
│ source=API_     │
│ UPDATE          │
│ updated_by_     │
│ user_id=X       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update agent:   │
│ status_sync=    │
│ IN_SYNC         │
│ alert_config=   │
│ false           │
└─────────────────┘
```

### 3. Consulta de Agents

```
┌───────────────────────────────────────┐
│  GET /api/v1/agents?page=1&size=50    │
└─────────────────┬─────────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ AgentRepository │
         │ get_all(skip,   │
         │         limit)  │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ SELECT * FROM       │
         │ agents ORDER BY     │
         │ updated_at DESC     │
         │ LIMIT X OFFSET Y    │
         └────────┬────────────┘
                  │
                  ▼
         ┌─────────────────────┐
         │ Return paginated    │
         │ AgentListResponse   │
         └─────────────────────┘
```

---

## 🧩 Componentes Principais

### 1. FastAPI Application (`app/main.py`)

**Responsabilidades:**
- Configurar aplicação FastAPI
- Registrar routers
- Configurar CORS
- Gerenciar lifespan (startup/shutdown)
- Iniciar background tasks

**Routers incluídos:**
- `/api/v1/auth` - Autenticação
- `/api/v1/agents` - Gestão de agents
- `/api/v1/config` - Atualização de configs
- `/api/v1/opamp` - Sincronização manual

### 2. Background Tasks (`app/background.py`)

**Responsabilidades:**
- Executar job de sincronização periódica
- Gerenciar lifecycle do job (start/stop)
- Logar estatísticas de sincronização

**Intervalo:**
- Configurável via `OPAMP_SYNC_INTERVAL_SECONDS` (default: 60s)

**Funcionamento:**
```python
while running:
    try:
        # Sync com OpAMP
        result = await opamp_service.sync_all_agents()
        logger.info(f"Synced: {result.agents_processed} agents")
    except Exception as e:
        logger.error(f"Sync error: {e}")
    
    await asyncio.sleep(interval_seconds)
```

### 3. OpAMP Service (`app/services/opamp_service.py`)

**Métodos principais:**

#### `fetch_agents_from_opamp()`
Busca dados de agents do OpAMP Server.

```python
async def fetch_agents_from_opamp() -> List[Dict]:
    url = f"{opamp_url}/agents/full"
    response = await httpx.get(url)
    return response.json()
```

#### `sync_agent(agent_data)`
Sincroniza um agent individual.

**Passos:**
1. Extrai atributos (host_name, os_*, etc)
2. Upsert em `agents`
3. Cria registro em `agent_health`
4. Calcula hash de config
5. Se hash mudou:
   - Cria nova versão em `agent_configs`
   - Marca `alert_config = true`
   - `status_sync = OUT_OF_SYNC`

#### `sync_all_agents()`
Sincroniza todos os agents.

**Passos:**
1. Fetch de `/agents/full`
2. Loop por cada agent → `sync_agent()`
3. Marca agents desconectados (`is_connected = false`)
4. Retorna estatísticas

#### `send_config_to_opamp(instance_id, config, user_id)`
Envia nova configuração para OpAMP.

**Passos:**
1. POST para `/save_config/json`
2. Se sucesso:
   - Cria nova versão em `agent_configs`
   - Limpa `alert_config`
   - `status_sync = IN_SYNC`
   - Registra `updated_by_user_id`

### 4. Repositories

**Padrão Repository:**
- Encapsula acesso a dados
- Retorna models SQLAlchemy
- Usa async/await
- Operações CRUD + queries específicas

**Principais métodos:**

| Repository | Métodos |
|-----------|---------|
| `AgentRepository` | `get_by_instance_id`, `upsert`, `get_all`, `mark_disconnected` |
| `AgentHealthRepository` | `create`, `get_latest_by_instance_id`, `get_history` |
| `AgentConfigRepository` | `create`, `get_latest`, `get_next_version`, `get_history` |
| `UserRepository` | `create`, `get_by_login`, `get_by_email`, `update` |

### 5. Authentication (`app/core/security.py`)

**JWT Token:**
```python
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Password Hashing:**
```python
# Bcrypt via passlib
pwd_context = CryptContext(schemes=["bcrypt"])

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**Dependency:**
```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(401)
    
    return user
```

---

## 🗄️ Modelo de Dados Relacional

### Relacionamentos

```
User (1) ──────► (N) AgentConfig
                      │
                      │ (N)
                      ▼
Agent (1) ────────► (1) AgentConfig (latest)
      │
      │ (1)
      ▼
      (N) AgentHealth
```

### Índices Importantes

| Tabela | Índice | Tipo | Propósito |
|--------|--------|------|-----------|
| `agents` | `instance_id` | UNIQUE | Lookup rápido por ID |
| `agents` | `(status_sync, is_connected)` | COMPOSITE | Filtrar por status |
| `agents` | `alert_config` | SINGLE | Listar agents com alerta |
| `agent_health` | `(instance_id, created_at)` | COMPOSITE | Histórico ordenado |
| `agent_configs` | `(instance_id, version)` | COMPOSITE | Lookup por versão |
| `agent_configs` | `config_hash` | SINGLE | Detecção de duplicatas |

---

## 🔐 Segurança

### Autenticação JWT

**Flow:**
1. User faz POST `/auth/login` com credentials
2. Backend valida e retorna JWT token
3. Cliente inclui token em requests: `Authorization: Bearer <token>`
4. Dependency `get_current_user` valida token e retorna user

**Token Payload:**
```json
{
  "sub": 1,           // user_id
  "login": "admin",
  "exp": 1700000000   // expiration timestamp
}
```

### Endpoints Protegidos

| Endpoint | Auth Required | Motivo |
|----------|--------------|--------|
| `POST /config` | ✅ | Muda configuração de agents |
| `POST /opamp/sync` | ✅ | Dispara sincronização |
| `GET /agents/csv` | ✅ | Exporta dados sensíveis |
| `GET /agents` | ❌ | Leitura pública |
| `GET /agents/{id}` | ❌ | Leitura pública |

### Boas Práticas

1. **Secret Key:** Usar chave aleatória forte (32+ bytes)
2. **HTTPS:** Em produção, sempre usar TLS
3. **Token Expiration:** 30 minutos (configurável)
4. **Password Policy:** Mínimo 8 caracteres (ajustar conforme necessário)
5. **CORS:** Restringir origins permitidos

---

## 🚀 Performance

### Otimizações Implementadas

1. **Async I/O:**
   - FastAPI com async/await
   - asyncpg driver (PostgreSQL)
   - httpx async client

2. **Database:**
   - Índices em campos de lookup frequente
   - Connection pooling via SQLAlchemy
   - Queries otimizadas (select specific columns)

3. **Paginação:**
   - Todos os endpoints de listagem suportam pagination
   - Default: 50 items, max: 500

4. **Caching Potencial:**
   - Redis pode ser adicionado para cache de queries
   - Cache de configs frequentemente acessados

### Métricas de Referência

**Expectativas** (depende de hardware):
- List agents (50 items): < 100ms
- Get agent by ID: < 50ms
- Update config: < 500ms (depende de OpAMP)
- Sync job (100 agents): < 5s

---

## 🔄 Escalabilidade

### Horizontal Scaling

**Backend API:**
- Stateless (exceto background task)
- Pode rodar múltiplas instâncias atrás de load balancer
- Sessões JWT são stateless (não precisam de shared storage)

**Background Task:**
- Executar em apenas 1 instância (usar leader election)
- Alternativa: Usar job scheduler externo (Celery, APScheduler distribuído)

**Database:**
- PostgreSQL com replicação read-replica
- Conexões via connection pool

### Vertical Scaling

**Limites esperados** (instância única):
- ~1000 agents sincronizados
- ~100 requisições/segundo (API)
- Database: depende de hardware

---

## 📈 Monitoramento e Observabilidade

### Logs

**Níveis:**
- `INFO`: Operações normais (syncs, requests)
- `ERROR`: Falhas de sync, erros de API
- `DEBUG`: Detalhes de queries (se DEBUG=true)

**Estrutura de log:**
```
2025-11-17 10:00:00 - app.background - INFO - OpAMP sync completed: 10 processed, 10 updated, 2 configs versioned
2025-11-17 10:00:30 - app.services.opamp_service - ERROR - Failed to fetch agents from OpAMP: Connection timeout
```

### Health Checks

- `GET /health` - Backend health
- `GET /` - API info
- Container healthcheck via curl

### Métricas Futuras

Adicionar:
- Prometheus metrics endpoint
- Grafana dashboards
- Alertmanager para notificações

**Métricas relevantes:**
- Requests por segundo (por endpoint)
- Latência de sync jobs
- Taxa de erro de sync
- Número de agents com alertas
- Database connection pool status

---

## 🧪 Testes

### Estratégia de Testes

**Unit Tests:**
- Repositories (mocked database)
- Services (mocked repositories)
- Security functions

**Integration Tests:**
- API endpoints (TestClient)
- Database operations (test database)

**E2E Tests:**
- Full sync flow
- Config update flow

### Estrutura de Testes (futura)

```
tests/
├── unit/
│   ├── test_repositories.py
│   ├── test_services.py
│   └── test_security.py
├── integration/
│   ├── test_api_auth.py
│   ├── test_api_agents.py
│   └── test_api_config.py
└── e2e/
    ├── test_sync_flow.py
    └── test_config_update_flow.py
```

---

## 🔮 Roadmap

### Fase 1: MVP ✅
- [x] Modelos de dados
- [x] Migrations
- [x] Autenticação JWT
- [x] CRUD agents
- [x] Sincronização OpAMP
- [x] Versionamento de configs
- [x] Detecção de divergências
- [x] API REST completa
- [x] Dockerização

### Fase 2: Melhorias
- [ ] Testes automatizados
- [ ] Roles e permissões (RBAC)
- [ ] Filtros avançados (search, filters)
- [ ] Webhooks para alertas
- [ ] Rate limiting
- [ ] Audit log

### Fase 3: Observabilidade
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Distributed tracing (Jaeger/Tempo)
- [ ] Alerting (Alertmanager)

### Fase 4: Escalabilidade
- [ ] Redis caching
- [ ] Celery para background jobs
- [ ] Read replicas
- [ ] Load balancer config

---

## 📚 Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [OpAMP Specification](https://github.com/open-telemetry/opamp-spec)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**Última atualização:** 2025-11-17  
**Versão da Arquitetura:** 1.0.0
