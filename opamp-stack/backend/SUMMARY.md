# OpAMP Backend - Sumário Executivo

## 🎯 Visão Geral

Sistema backend completo em **FastAPI + PostgreSQL** para gerenciamento, sincronização e versionamento de agents OpAMP, com API REST, autenticação JWT e sincronização automática.

---

## ✨ Características Principais

### 1. **Sincronização Automática com OpAMP**
- Job background que sincroniza a cada 60s (configurável)
- Busca dados de agents via `/agents/full`
- Atualiza informações de agents, health e configurações
- Marca agents desconectados automaticamente

### 2. **Versionamento de Configurações**
- Detecta mudanças via SHA256 hash
- Cria nova versão automaticamente
- Rastreabilidade completa (quem alterou, quando, de onde)
- Histórico ilimitado de versões

### 3. **Sistema de Alertas**
- Detecção automática de divergências de config
- Flag `alert_config` para agents fora de sincronia
- Status `IN_SYNC` / `OUT_OF_SYNC` / `UNKNOWN`

### 4. **API REST Completa**
- 15+ endpoints documentados (Swagger/OpenAPI)
- Paginação em listagens
- Export CSV de agents
- Download de configs em YAML
- Autenticação JWT

### 5. **Gestão de Configurações**
- Envio de novas configs para agents via OpAMP
- Registro de quem fez a alteração
- Integração com endpoint `/save_config/json`

---

## 🏗️ Arquitetura

```
┌──────────────┐    sync     ┌──────────────┐
│   OpAMP      │◄────────────┤   Backend    │
│   Server     │             │   FastAPI    │
└──────────────┘             └──────┬───────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │  PostgreSQL  │
                             │  (4 tabelas) │
                             └──────────────┘
```

**Stack:**
- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 15+
- **Auth**: JWT (python-jose + bcrypt)
- **Container**: Docker + Docker Compose

**Camadas:**
```
Routers (API) → Services (Business Logic) → Repositories (Data Access) → Models (Database)
```

---

## 📊 Modelo de Dados

### Tabelas

| Tabela | Descrição | Campos Principais |
|--------|-----------|-------------------|
| `users` | Usuários do sistema | id, login, email, password_hash |
| `agents` | Agents OpAMP | instance_id, host_name, os_*, healthy, status_sync, alert_config |
| `agent_health` | Histórico de saúde | instance_id, healthy, status, status_time_unix_nano |
| `agent_configs` | Versionamento de configs | instance_id, version, effective_config, config_hash, updated_by_user_id |

### Relacionamentos
- `User` 1:N `AgentConfig` (rastreabilidade)
- `Agent` 1:N `AgentHealth` (histórico)
- `Agent` 1:N `AgentConfig` (versões)

---

## 🚀 Instalação

### Pré-requisitos
- Docker & Docker Compose
- Git

### Passos

```bash
# 1. Clone o repo
git clone <repo-url>
cd AmpBridge/opamp-stack

# 2. Configure environment
cd backend
cp .env.example .env
# Edite .env e altere SECRET_KEY

# 3. Suba o stack
cd ..
docker compose up -d

# 4. Verifique
docker compose ps
curl http://localhost:8000/health
```

**Portas:**
- `8000` - Backend API
- `5432` - PostgreSQL
- `4321` - OpAMP Server

---

## 📡 Endpoints Principais

### Autenticação
- `POST /api/v1/auth/register` - Registrar usuário
- `POST /api/v1/auth/login` - Login (retorna JWT)
- `GET /api/v1/auth/me` - Info do usuário atual

### Agents
- `GET /api/v1/agents` - Listar agents (paginado)
- `GET /api/v1/agents/{id}` - Detalhes do agent
- `GET /api/v1/agents/{id}/health` - Histórico de saúde
- `GET /api/v1/agents/{id}/configs` - Histórico de configs
- `GET /api/v1/agents/{id}/config` - Download YAML config
- `GET /api/v1/agents/csv` - Export CSV (requer auth)

### Configuração
- `POST /api/v1/config?instance_id={id}` - Atualizar config (requer auth)

### Sincronização
- `POST /api/v1/opamp/sync` - Sync manual (requer auth)

**Documentação interativa:** http://localhost:8000/docs

---

## 🔧 Uso Básico

### 1. Criar usuário e obter token

```bash
# Registrar
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Admin", "email": "admin@example.com", "login": "admin", "password": "admin123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "admin123"}' | jq -r '.access_token')
```

### 2. Listar agents

```bash
curl http://localhost:8000/api/v1/agents | jq
```

### 3. Sincronizar manualmente

```bash
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 4. Atualizar config de um agent

```bash
curl -X POST "http://localhost:8000/api/v1/config?instance_id=<ID>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317"}'
```

---

## 📈 Funcionalidades de Sincronização

### Sincronização Automática (Background Task)

**Frequência:** 60 segundos (configurável via `OPAMP_SYNC_INTERVAL_SECONDS`)

**Fluxo:**
1. Busca agents de `http://opamp-server:4321/agents/full`
2. Para cada agent:
   - Atualiza/cria registro em `agents`
   - Cria registro de health em `agent_health`
   - Calcula hash SHA256 do `effective_config`
   - Se hash mudou:
     - Cria nova versão em `agent_configs`
     - Marca `alert_config = true`
     - `status_sync = OUT_OF_SYNC`
3. Marca agents não presentes como `is_connected = false`

**Logs:**
```
INFO - OpAMP sync completed: 10 processed, 10 updated, 2 configs versioned
```

### Sincronização Manual

Via endpoint `POST /api/v1/opamp/sync` - permite disparar sync sob demanda.

---

## 🔒 Segurança

### Autenticação JWT
- Tokens expiram em 30 minutos
- Senhas hasheadas com bcrypt
- Header: `Authorization: Bearer <token>`

### Endpoints Protegidos
- `POST /api/v1/config` ✅
- `POST /api/v1/opamp/sync` ✅
- `GET /api/v1/agents/csv` ✅
- Listagem de agents ❌ (público)

### Recomendações Produção
1. Alterar `SECRET_KEY` (usar `openssl rand -hex 32`)
2. Configurar CORS para domínios específicos
3. Usar HTTPS (reverse proxy)
4. Senha forte no PostgreSQL

---

## 📚 Documentação Completa

- **[README.md](README.md)** - Documentação completa da API e uso
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detalhes da arquitetura e design
- **[QUICKSTART.md](QUICKSTART.md)** - Guia rápido de início
- **[Swagger UI](http://localhost:8000/docs)** - Documentação interativa

---

## 🧪 Testes

### Script de teste automatizado

```bash
cd backend
chmod +x test_api.sh
./test_api.sh
```

Testa:
- ✅ Registro de usuário
- ✅ Login e JWT
- ✅ Sincronização OpAMP
- ✅ Listagem de agents
- ✅ Histórico health/config
- ✅ Export CSV

---

## 🐛 Troubleshooting

### Backend não inicia
```bash
docker logs opamp-backend
docker compose restart backend
```

### Sync não funciona
```bash
docker logs -f opamp-backend | grep sync
docker exec opamp-backend curl http://opamp-server:4321/agents/full
```

### Acessar database
```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db
```

---

## 📊 Métricas e Monitoramento

### Health Checks
```bash
curl http://localhost:8000/health        # Backend
curl http://localhost:4321/              # OpAMP
docker exec opamp-postgres pg_isready    # PostgreSQL
```

### Logs
```bash
docker logs -f opamp-backend             # Backend logs
docker compose logs -f                   # All services
```

### Database Stats
```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "
SELECT 'agents' as table, COUNT(*) FROM agents
UNION ALL
SELECT 'agent_health', COUNT(*) FROM agent_health
UNION ALL
SELECT 'agent_configs', COUNT(*) FROM agent_configs;
"
```

---

## 🎯 Casos de Uso

### 1. Monitorar agents com divergência de config
```bash
curl http://localhost:8000/api/v1/agents | jq '.agents[] | select(.alert_config == true)'
```

### 2. Auditoria de mudanças de config
```sql
SELECT 
  ac.instance_id,
  a.host_name,
  ac.version,
  ac.source,
  u.login as changed_by,
  ac.created_at
FROM agent_configs ac
JOIN agents a ON a.instance_id = ac.instance_id
LEFT JOIN users u ON u.id = ac.updated_by_user_id
ORDER BY ac.created_at DESC;
```

### 3. Análise de saúde histórica
```bash
curl "http://localhost:8000/api/v1/agents/{ID}/health?limit=100" | \
  jq '[.[] | {time: .created_at, healthy: .healthy, status: .status}]'
```

---

## 🚦 Status do Projeto

### Implementado ✅
- [x] Modelos de dados e migrations
- [x] Autenticação JWT
- [x] CRUD completo de agents
- [x] Sincronização automática OpAMP
- [x] Versionamento de configs
- [x] Detecção de divergências
- [x] API REST completa
- [x] Dockerização
- [x] Documentação completa

### Roadmap 🚀
- [ ] Testes automatizados (pytest)
- [ ] Roles/Permissions (RBAC)
- [ ] Webhooks para alertas
- [ ] Métricas Prometheus
- [ ] Grafana dashboards
- [ ] Rate limiting
- [ ] Audit log UI

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Veja [README.md](README.md) para detalhes.

---

## 📄 Licença

Ver arquivo LICENSE do repositório.

---

## 🎉 Pronto para Usar!

O sistema está **100% funcional** e pronto para uso em desenvolvimento/produção.

**Links rápidos:**
- API: http://localhost:8000/docs
- OpAMP UI: http://localhost:4321
- PostgreSQL: `localhost:5432`

**Comando único para subir tudo:**
```bash
docker compose up -d
```

---

**Desenvolvido com ❤️ usando FastAPI + PostgreSQL + SQLAlchemy + OpAMP**
