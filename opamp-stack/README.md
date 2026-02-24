# OpAMP Stack - Complete Management System

Full stack for managing OpAMP agents with a FastAPI backend, automatic synchronization, configuration versioning, and a REST API.

---

## 📋 Stack Components

```
opamp-stack/
├── opamp-server/          # OpAMP Server (opamp-go)
├── backend/               # FastAPI Backend
├── data/                  # Persistent data
│   ├── postgres/          # PostgreSQL data
├── frontend/              # OpAMP Dashboard
└── docker-compose.yml     # Full orchestration
```

### 🔧 Services

| Service | Description | Port | Status |
|---------|-------------|------|--------|
| **postgres** | PostgreSQL 16 | 5432 | ✅ Implemented |
| **opamp-server** | OpAMP Server (Go) | 4320, 4321 | ✅ Available |
| **backend** | FastAPI Backend | 8000 | ✅ Implemented |
| **frontend** | OpAMP Dashboard | 3000 | ✅ Implemented |

---

## 🚀 Quick Start

### 1. Start all services

```bash
cd opamp-stack
docker compose up -d
```

### 2. Check status

```bash
docker compose ps
```

All services should be "healthy" after ~30 seconds.

### 3. Access services

- **Backend API**: http://localhost:8000/docs
- **OpAMP Server**: http://localhost:4321
- **OpAMP Dashboard**: http://localhost:3000

### 4. Create the first user

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

### 5. Log in

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }' | jq
```

**Done!** 🎉 The system is running.

---

## 📦 FastAPI Backend

The backend implements a complete management system for OpAMP:

### ✨ Features

1. **Automatic Synchronization**
   - Background job that syncs with OpAMP every 60s
   - Updates agent data, health, and configurations
   - Automatically marks disconnected agents

2. **Configuration Versioning**
   - Detects changes via SHA256 hash
   - Automatically creates a new version
   - Full change history

3. **Alert System**
   - Detects configuration divergences
   - Alert flags on agents
   - Sync status (IN_SYNC/OUT_OF_SYNC)

4. **Full REST API**
   - 15+ documented endpoints
   - JWT authentication
   - CSV export
   - Config download

5. **Configuration Management**
   - Push configs to agents via OpAMP
   - Audit trail of who made changes
   - Full integration with OpAMP Server

### 📊 Database

PostgreSQL with 4 tables:

- **users**: System users
- **agents**: OpAMP agent data
- **agent_health**: Health history
- **agent_configs**: Configuration versioning

### 📚 Full Documentation

See detailed documentation in `backend/`:

- **[README.md](backend/README.md)** - Full documentation
- **[ARCHITECTURE.md](backend/ARCHITECTURE.md)** - System architecture
- **[QUICKSTART.md](backend/QUICKSTART.md)** - Quick start guide
- **[SUMMARY.md](backend/SUMMARY.md)** - Executive summary

---

## 🏗️ Architecture

```
              External (host)
 ┌────────────────────────────────────────────────────────────────┐
 │  OTel Agents ──ws──► :4320   Frontend ──► :3000   API ──► :8000│
 └───────────────────┬────────────────────────────────────────────┘
                     │ opamp-network (bridge)
 ┌───────────────────▼────────────────────────────────────────────┐
 │                                                                │
 │  ┌─────────────────────────┐      ┌──────────────────────┐    │
 │  │      opamp-server       │◄─────│   Backend FastAPI    │    │
 │  │  OpAMP :4320 (WS/HTTP)  │ sync │       :8000          │    │
 │  │  UI    :4321            │      └──────────┬───────────┘    │
 │  └─────────────────────────┘                 │                │
 │                                              ▼                │
 │                                   ┌──────────────────────┐    │
 │                                   │      PostgreSQL       │    │
 │                                   │        :5432          │    │
 │                                   └──────────────────────┘    │
 │                                                                │
 │  ┌──────────────────────┐                                      │
 │  │   Frontend (nginx)   │                                      │
 │  │   :80 → host :3000   │                                      │
 │  └──────────────────────┘                                      │
 └────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **OTel Agents** connect directly to the **OpAMP Server** via WebSocket (`ws://<host>:4320/v1/opamp`)
2. **Backend** periodically syncs with the **OpAMP Server** (internal port 4321)
3. **Backend** persists data in **PostgreSQL**
4. Users access the **Frontend** (port 3000) or the **Backend API** (port 8000) for management

---

## 🔧 Configuration

### Environment Variables (Backend)

Edit `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://opamp:opamp_password@postgres:5432/opamp_db

# OpAMP Server
OPAMP_SERVER_URL=http://opamp-server:4321
OPAMP_SYNC_INTERVAL_SECONDS=60

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=change-this-secret-key-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important:** Generate a new `SECRET_KEY` for production:
```bash
openssl rand -hex 32
```

### Exposed Ports

| Service | Internal Port | External Port | Description |
|---------|---------------|---------------|-------------|
| OpAMP Server | 4320 | 4320 | OpAMP Protocol (WebSocket/HTTP) |
| OpAMP Server | 4321 | 4321 | Management UI and API |
| Backend | 8000 | 8000 | FastAPI REST API |
| Frontend | 80 | 3000 | Web dashboard |
| PostgreSQL | 5432 | 5432 | Database |

---

## 📡 API Endpoints

### Base URL
```
http://localhost:8000/api/v1
```

### Main Endpoints

#### Authentication
- `POST /auth/register` - Register user
- `POST /auth/login` - Login (returns JWT)
- `GET /auth/me` - Current user info

#### Agents
- `GET /agents` - List agents (paginated)
- `GET /agents/{id}` - Agent details
- `GET /agents/{id}/health` - Health history
- `GET /agents/{id}/configs` - Config history
- `GET /agents/{id}/config` - Download YAML config
- `GET /agents/csv` - CSV export (auth required)

#### Configuration
- `POST /config?instance_id={id}` - Update config (auth required)

#### Synchronization
- `POST /opamp/sync` - Manual sync (auth required)

**Interactive docs:** http://localhost:8000/docs

---

## 🔒 Security

### JWT Authentication

1. Register a user: `POST /auth/register`
2. Log in: `POST /auth/login`
3. Use the returned token: `Authorization: Bearer <token>`

### Protected Endpoints

Require authentication:
- ✅ `POST /config`
- ✅ `POST /opamp/sync`
- ✅ `GET /agents/csv`

Public:
- ❌ `GET /agents`
- ❌ `GET /agents/{id}`

---

## 🧪 Testing

### Quick Test

```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:4321/

# Verify OpAMP port
curl -i -N -H "Upgrade: websocket" -H "Connection: Upgrade" \
  http://localhost:4320/v1/opamp 2>&1 | head -5

# List agents
curl http://localhost:8000/api/v1/agents | jq
```

### Full Test Script

```bash
cd backend
chmod +x test_api.sh
./test_api.sh
```

---

## 📊 Monitoring

### Logs

```bash
# All services
docker compose logs -f

# Backend only
docker logs -f opamp-backend

# OpAMP Server
docker logs -f opamp-server

# PostgreSQL
docker logs -f opamp-postgres
```

### Health Checks

```bash
# Check all services status
docker compose ps

# Individual health check
curl http://localhost:8000/health         # Backend
curl http://localhost:4321/               # OpAMP
docker exec opamp-postgres pg_isready     # PostgreSQL
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it opamp-postgres psql -U opamp -d opamp_db

# View statistics
# opamp_db=# SELECT 'agents', COUNT(*) FROM agents;
# opamp_db=# SELECT instance_id, host_name, alert_config FROM agents;
```

---

## 🛠️ Useful Commands

### Docker Compose

```bash
# Start everything
docker compose up -d

# View status
docker compose ps

# View logs
docker compose logs -f

# Restart a specific service
docker compose restart backend

# Stop everything
docker compose down

# Stop and remove volumes (CAUTION: deletes data!)
docker compose down -v

# Rebuild and restart
docker compose up -d --build backend
```

### Migrations (Backend)

```bash
# View current status
docker exec opamp-backend alembic current

# Apply all migrations
docker exec opamp-backend alembic upgrade head

# Roll back one migration
docker exec opamp-backend alembic downgrade -1

# Create a new migration
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

### Backend does not start

```bash
# View logs
docker logs opamp-backend

# Check if postgres is healthy
docker compose ps postgres

# Check environment variables
docker exec opamp-backend env | grep DATABASE_URL

# Restart
docker compose restart backend
```

### Synchronization not working

```bash
# View sync logs
docker logs -f opamp-backend | grep sync

# Test connection to OpAMP
docker exec opamp-backend curl http://opamp-server:4321/agents/full

# Force manual sync
TOKEN=<your-token>
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN"
```

### Authentication issues

```bash
# Check if user exists
docker exec -it opamp-postgres psql -U opamp -d opamp_db \
  -c "SELECT id, login, email, is_active FROM users;"

# Create a new user if needed
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "email": "test@example.com", "login": "test", "password": "test123"}'
```

### Full rebuild

```bash
# Stop everything
docker compose down

# Rebuild images
docker compose build --no-cache backend

# Start again
docker compose up -d

# Apply migrations
docker exec opamp-backend alembic upgrade head
```

---

## 📈 Performance

### Expectations (average hardware)

- **List agents (50 items)**: < 100ms
- **Get agent by ID**: < 50ms
- **Config update**: < 500ms
- **Sync job (100 agents)**: < 5s

### Optimizations

- async/await throughout the stack
- Database indexes
- Pagination for large queries
- Connection pooling

---

## 🔄 Automatic Synchronization

### How It Works

1. Background task runs every 60s
2. Sends GET to `/agents/full` on the OpAMP Server
3. For each agent:
   - Updates basic data
   - Creates a health record
   - Checks if config changed (SHA256 hash)
   - If changed: creates a new version and sets alert flag
4. Marks absent agents as disconnected

### Configure Interval

Edit `backend/.env`:
```env
OPAMP_SYNC_INTERVAL_SECONDS=30  # 30 seconds
```

Restart:
```bash
docker compose restart backend
```

---

## 📚 Additional Documentation

- **Backend API**: See `backend/README.md`
- **Architecture**: See `backend/ARCHITECTURE.md`
- **Quick Start**: See `backend/QUICKSTART.md`
- **Summary**: See `backend/SUMMARY.md`
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🎯 Use Cases

### 1. Monitor Agents

```bash
# List all
curl http://localhost:8000/api/v1/agents | jq

# Agents with alerts
curl http://localhost:8000/api/v1/agents | \
  jq '.agents[] | select(.alert_config == true)'

# Export for analysis
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/csv -o agents.csv
```

### 2. Check Agent Health

```bash
INSTANCE_ID="019a7534-f534-70ab-bbbc-115e2d231708"

# Current data
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID | jq

# Health history
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/health?limit=50" | jq
```

### 3. Manage Configurations

```bash
# View config history
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs" | jq

# Download current config
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config" -o config.yaml

# Push new config
curl -X POST "http://localhost:8000/api/v1/config?instance_id=$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317"}' | jq
```

---

## 🚦 Project Status

### Components

| Component | Status | Description |
|-----------|--------|-------------|
| OpAMP Server | ✅ Working | OpAMP server (direct port 4320) |
| PostgreSQL | ✅ Working | Database |
| Backend API | ✅ Implemented | Full FastAPI system |
| Frontend | ✅ Implemented | Web dashboard |

### Backend Features

- ✅ Data models
- ✅ Migrations (Alembic)
- ✅ JWT authentication
- ✅ Agent CRUD
- ✅ OpAMP synchronization
- ✅ Config versioning
- ✅ Alert system
- ✅ Full REST API
- ✅ Dockerized
- ✅ Documentation

---

## 🎉 Summary

**OpAMP Stack** provides a complete and functional backend with:

- ✨ Automatic synchronization
- 📦 Config versioning
- 🔔 Alert system
- 🔐 JWT authentication
- 📊 Documented REST API
- 🐳 Fully containerized

**All working and ready to use!**

---

## 📞 Support

For questions and support:
- Issues in the repository
- Documentation: `backend/README.md`
- API Docs: http://localhost:8000/docs

---

**Built with ❤️ using FastAPI + PostgreSQL + OpAMP**
