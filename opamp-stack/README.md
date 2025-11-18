# OpAMP Stack - Sistema Completo de Gerenciamento

Stack completo para gerenciamento de agents OpAMP com backend FastAPI, sincronização automática, versionamento de configurações e API REST.

---

## 📋 Componentes do Stack

```
opamp-stack/
├── opamp-server/          # Servidor OpAMP (opamp-go)
├── backend/               # Backend FastAPI (NOVO!)
├── haproxy/               # Load balancer (HAProxy)
├── data/                  # Dados persistentes
│   ├── postgres/          # PostgreSQL data
│   └── redis/             # Redis data
└── docker-compose.yml     # Orquestração completa
```

### 🔧 Serviços

| Serviço | Descrição | Porta | Status |
|---------|-----------|-------|--------|
| **postgres** | PostgreSQL 15 | 5432 | ✅ Implementado |
| **opamp-server** | OpAMP Server (Go) | 4321 | ✅ Existente |
| **backend** | Backend FastAPI | 8000 | ✅ Implementado |
| **haproxy** | Load Balancer | 4320 | ✅ Existente |

---

## 🚀 Quick Start

### 1. Subir todos os serviços

```bash
cd opamp-stack
docker compose up -d
```

### 2. Verificar status

```bash
docker compose ps
```

Todos devem estar "healthy" após ~30 segundos.

### 3. Acessar serviços

- **Backend API**: http://localhost:8000/docs
- **OpAMP Server**: http://localhost:4321
- **HAProxy**: http://localhost:4320

### 4. Criar primeiro usuário

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin User",
    "email": "admin@example.com",
    "login": "admin",
    "password": "admin123"
  }'
```

### 5. Fazer login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }' | jq
```

**Pronto!** 🎉 O sistema está rodando.

---

## 📦 Backend FastAPI - Novo Sistema

O backend implementa um sistema completo de gerenciamento para OpAMP:

### ✨ Funcionalidades

1. **Sincronização Automática**
   - Job background que sincroniza com OpAMP a cada 60s
   - Atualiza dados de agents, health e configurações
   - Marca agents desconectados automaticamente

2. **Versionamento de Configurações**
   - Detecta mudanças via SHA256 hash
   - Cria nova versão automaticamente
   - Histórico completo de alterações

3. **Sistema de Alertas**
   - Detecção de divergências de configuração
   - Flags de alerta em agents
   - Status de sincronização (IN_SYNC/OUT_OF_SYNC)

4. **API REST Completa**
   - 15+ endpoints documentados
   - Autenticação JWT
   - Export CSV
   - Download de configs

5. **Gestão de Configurações**
   - Envio de configs para agents via OpAMP
   - Rastreabilidade de quem alterou
   - Integração completa com OpAMP Server

### 📊 Banco de Dados

PostgreSQL com 4 tabelas:

- **users**: Usuários do sistema
- **agents**: Dados dos agents OpAMP
- **agent_health**: Histórico de saúde
- **agent_configs**: Versionamento de configurações

### 📚 Documentação Completa

Ver documentação detalhada em `backend/`:

- **[README.md](backend/README.md)** - Documentação completa
- **[ARCHITECTURE.md](backend/ARCHITECTURE.md)** - Arquitetura do sistema
- **[QUICKSTART.md](backend/QUICKSTART.md)** - Guia rápido
- **[SUMMARY.md](backend/SUMMARY.md)** - Sumário executivo

---

## 🏗️ Arquitetura Completa

```
┌─────────────────────────────────────────────────────┐
│                  Docker Network                      │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────┐                                    │
│  │              │                                    │
│  │   HAProxy    │                                    │
│  │   :4320      │                                    │
│  │              │                                    │
│  └──────┬───────┘                                    │
│         │                                            │
│         ▼                                            │
│  ┌──────────────┐      ┌──────────────┐             │
│  │              │      │              │             │
│  │  OpAMP       │◄─────┤   Backend    │             │
│  │  Server      │ sync │   FastAPI    │             │
│  │  :4321       │      │   :8000      │             │
│  │              │      │              │             │
│  └──────┬───────┘      └──────┬───────┘             │
│         │                     │                     │
│         │                     ▼                     │
│         │              ┌──────────────┐             │
│         │              │              │             │
│         │              │  PostgreSQL  │             │
│         │              │  :5432       │             │
│         │              │              │             │
│         │              └──────────────┘             │
│         │                                            │
│         ▼                                            │
│  ┌──────────────┐                                    │
│  │              │                                    │
│  │   Agents     │                                    │
│  │   (OpAMP)    │                                    │
│  │              │                                    │
│  └──────────────┘                                    │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### Fluxo de Dados

1. **Agents** conectam ao **OpAMP Server** (porta 4321 ou via HAProxy 4320)
2. **Backend** sincroniza periodicamente com **OpAMP Server**
3. **Backend** persiste dados no **PostgreSQL**
4. Usuários acessam **Backend API** (porta 8000) para gestão

---

## 🔧 Configuração

### Variáveis de Ambiente (Backend)

Edite `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://opamp:opamp_password@postgres:5432/opamp_db

# OpAMP Server
OPAMP_SERVER_URL=http://opamp-server:4321
OPAMP_SYNC_INTERVAL_SECONDS=60

# Security (ALTERAR EM PRODUÇÃO!)
SECRET_KEY=change-this-secret-key-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Importante:** Gerar nova `SECRET_KEY` em produção:
```bash
openssl rand -hex 32
```

### Portas Expostas

| Serviço | Porta Interna | Porta Externa | Descrição |
|---------|---------------|---------------|-----------|
| Backend | 8000 | 8000 | API REST |
| OpAMP Server | 4321 | 4321 | UI e API OpAMP |
| HAProxy | 4320 | 4320 | Load balancer |
| PostgreSQL | 5432 | 5432 | Database |

---

## 📡 Endpoints da API

### Base URL
```
http://localhost:8000/api/v1
```

### Principais Endpoints

#### Autenticação
- `POST /auth/register` - Registrar usuário
- `POST /auth/login` - Login (retorna JWT)
- `GET /auth/me` - Info usuário atual

#### Agents
- `GET /agents` - Listar agents (paginado)
- `GET /agents/{id}` - Detalhes do agent
- `GET /agents/{id}/health` - Histórico de saúde
- `GET /agents/{id}/configs` - Histórico de configs
- `GET /agents/{id}/config` - Download YAML config
- `GET /agents/csv` - Export CSV (auth)

#### Configuração
- `POST /config?instance_id={id}` - Atualizar config (auth)

#### Sincronização
- `POST /opamp/sync` - Sync manual (auth)

**Documentação interativa:** http://localhost:8000/docs

---

## 🔒 Segurança

### Autenticação JWT

1. Registre um usuário: `POST /auth/register`
2. Faça login: `POST /auth/login`
3. Use o token retornado: `Authorization: Bearer <token>`

### Endpoints Protegidos

Requerem autenticação:
- ✅ `POST /config`
- ✅ `POST /opamp/sync`
- ✅ `GET /agents/csv`

Públicos:
- ❌ `GET /agents`
- ❌ `GET /agents/{id}`

---

## 🧪 Testes

### Teste Rápido

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:4321/

# Listar agents
curl http://localhost:8000/api/v1/agents | jq
```

### Script Completo de Testes

```bash
cd backend
chmod +x test_api.sh
./test_api.sh
```

---

## 📊 Monitoramento

### Logs

```bash
# Todos os serviços
docker compose logs -f

# Backend apenas
docker logs -f opamp-backend

# OpAMP Server
docker logs -f opamp-server

# PostgreSQL
docker logs -f opamp-postgres
```

### Health Checks

```bash
# Verificar status de todos os serviços
docker compose ps

# Health check individual
curl http://localhost:8000/health         # Backend
curl http://localhost:4321/               # OpAMP
docker exec opamp-postgres pg_isready     # PostgreSQL
```

### Database

```bash
# Conectar ao PostgreSQL
docker exec -it opamp-postgres psql -U opamp -d opamp_db

# Ver estatísticas
# opamp_db=# SELECT 'agents', COUNT(*) FROM agents;
# opamp_db=# SELECT instance_id, host_name, alert_config FROM agents;
```

---

## 🛠️ Comandos Úteis

### Docker Compose

```bash
# Subir tudo
docker compose up -d

# Ver status
docker compose ps

# Ver logs
docker compose logs -f

# Restart serviço específico
docker compose restart backend

# Parar tudo
docker compose down

# Parar e remover volumes (CUIDADO: apaga dados!)
docker compose down -v

# Rebuild e restart
docker compose up -d --build backend
```

### Migrations (Backend)

```bash
# Ver status atual
docker exec opamp-backend alembic current

# Aplicar todas as migrations
docker exec opamp-backend alembic upgrade head

# Voltar uma migration
docker exec opamp-backend alembic downgrade -1

# Criar nova migration
docker exec opamp-backend alembic revision -m "description"
```

### Database Backup/Restore

```bash
# Backup
docker exec opamp-postgres pg_dump -U opamp opamp_db > backup.sql

# Restore
cat backup.sql | docker exec -i opamp-postgres psql -U opamp -d opamp_db
```

---

## 🐛 Troubleshooting

### Backend não inicia

```bash
# Ver logs
docker logs opamp-backend

# Verificar se postgres está healthy
docker compose ps postgres

# Verificar variáveis de ambiente
docker exec opamp-backend env | grep DATABASE_URL

# Restart
docker compose restart backend
```

### Sincronização não funciona

```bash
# Ver logs de sync
docker logs -f opamp-backend | grep sync

# Testar conexão com OpAMP
docker exec opamp-backend curl http://opamp-server:4321/agents/full

# Forçar sync manual
TOKEN=<seu-token>
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN"
```

### Problemas de autenticação

```bash
# Verificar se usuário existe
docker exec -it opamp-postgres psql -U opamp -d opamp_db \
  -c "SELECT id, login, email, is_active FROM users;"

# Criar novo usuário se necessário
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "email": "test@example.com", "login": "test", "password": "test123"}'
```

### Rebuild completo

```bash
# Parar tudo
docker compose down

# Rebuild imagens
docker compose build --no-cache backend

# Subir novamente
docker compose up -d

# Aplicar migrations
docker exec opamp-backend alembic upgrade head
```

---

## 📈 Performance

### Expectativas (hardware médio)

- **Listagem de agents (50 items)**: < 100ms
- **Get agent por ID**: < 50ms
- **Atualização de config**: < 500ms
- **Job de sync (100 agents)**: < 5s

### Otimizações

- Uso de async/await em toda stack
- Índices no database
- Paginação em queries grandes
- Connection pooling

---

## 🔄 Sincronização Automática

### Como Funciona

1. Background task roda a cada 60s
2. Faz GET para `/agents/full` do OpAMP
3. Para cada agent:
   - Atualiza dados básicos
   - Cria registro de health
   - Verifica se config mudou (hash SHA256)
   - Se mudou: cria nova versão e marca alerta
4. Marca agents ausentes como desconectados

### Configurar Intervalo

Edite `backend/.env`:
```env
OPAMP_SYNC_INTERVAL_SECONDS=30  # 30 segundos
```

Restart:
```bash
docker compose restart backend
```

---

## 📚 Documentação Adicional

- **Backend API**: Ver `backend/README.md`
- **Arquitetura**: Ver `backend/ARCHITECTURE.md`
- **Quick Start**: Ver `backend/QUICKSTART.md`
- **Sumário**: Ver `backend/SUMMARY.md`
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🎯 Casos de Uso

### 1. Monitorar Agents

```bash
# Listar todos
curl http://localhost:8000/api/v1/agents | jq

# Agents com alertas
curl http://localhost:8000/api/v1/agents | \
  jq '.agents[] | select(.alert_config == true)'

# Export para análise
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/csv -o agents.csv
```

### 2. Verificar Saúde de um Agent

```bash
INSTANCE_ID="019a7534-f534-70ab-bbbc-115e2d231708"

# Dados atuais
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID | jq

# Histórico de saúde
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/health?limit=50" | jq
```

### 3. Gerenciar Configurações

```bash
# Ver histórico de configs
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs" | jq

# Baixar config atual
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config" -o config.yaml

# Enviar nova config
curl -X POST "http://localhost:8000/api/v1/config?instance_id=$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317"}' | jq
```

---

## 🚦 Status do Projeto

### Componentes

| Componente | Status | Descrição |
|------------|--------|-----------|
| OpAMP Server | ✅ Funcionando | Servidor OpAMP existente |
| HAProxy | ✅ Funcionando | Load balancer |
| PostgreSQL | ✅ Funcionando | Database |
| Backend API | ✅ Implementado | Sistema completo FastAPI |
| Frontend | 🔲 Planejado | Interface web (futuro) |

### Features Backend

- ✅ Modelos de dados
- ✅ Migrations (Alembic)
- ✅ Autenticação JWT
- ✅ CRUD agents
- ✅ Sincronização OpAMP
- ✅ Versionamento configs
- ✅ Sistema de alertas
- ✅ API REST completa
- ✅ Dockerização
- ✅ Documentação

---

## 🎉 Conclusão

O **OpAMP Stack** agora possui um backend completo e funcional com:

- ✨ Sincronização automática
- 📦 Versionamento de configs
- 🔔 Sistema de alertas
- 🔐 Autenticação JWT
- 📊 API REST documentada
- 🐳 Totalmente containerizado

**Tudo funcionando e pronto para uso!**

---

## 📞 Suporte

Para questões e suporte:
- Issues no repositório
- Documentação: `backend/README.md`
- API Docs: http://localhost:8000/docs

---

**Desenvolvido com ❤️ usando FastAPI + PostgreSQL + OpAMP**
