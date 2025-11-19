# 🚀 Quick Start Guide - OpAMP Backend

First steps to get the system up and running and test functionalities.

---

## ⚡ Quick Start (5 minutes)

### 1. Start the stack

```bash
cd opamp-stack
docker compose up -d
```

Wait for all containers to become healthy (~30 seconds):
```bash
docker compose ps
```

### 2. Create first user

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

### 3. Login and obtain token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 4. Trigger manual synchronization

```bash
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5. List agents

```bash
curl http://localhost:8000/api/v1/agents | jq
```

**Done!** 🎉 The system is running.

---

## 📖 Common Scenarios

### Scenario 1: Monitor agents with config alerts

```bash
# List all agents
curl http://localhost:8000/api/v1/agents | jq '.agents[] | select(.alert_config == true)'
```

### Scenario 2: View history of a specific agent

```bash
INSTANCE_ID="019a7534-f534-70ab-bbbc-115e2d231708"

# Agent data
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID | jq

# Health history
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID/health | jq

# Config versions
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs | jq
```

### Scenario 3: Download agent configuration

```bash
# Latest version
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID/config -o config.yaml

# Specific version
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config?version=2" -o config_v2.yaml
```

### Scenario 4: Update agent configuration

```bash
# Prepare config in file
cat > new_config.yaml << 'EOF'
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

exporters:
  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging]
EOF

# Convert to JSON string (escape newlines)
CONFIG_JSON=$(cat new_config.yaml | jq -Rs .)

# Send to API
curl -X POST "http://localhost:8000/api/v1/config?instance_id=$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"config\": $CONFIG_JSON}" | jq
```

### Scenario 5: Export agents for analysis

```bash
# CSV export
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/csv -o agents.csv

# Open in Excel/LibreOffice
libreoffice agents.csv
```

---

## 🔍 Quick Troubleshooting

### Backend doesn't start

```bash
# View logs
docker logs opamp-backend

# Check if postgres is up
docker compose ps postgres

# Restart backend
docker compose restart backend
```

### Sync not working

```bash
# View sync logs
docker logs -f opamp-backend | grep "OpAMP sync"

# Test connection with OpAMP
docker exec opamp-backend curl http://opamp-server:4321/agents/full

# Force manual sync
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN"
```

### Authentication error

```bash
# Check token
echo $TOKEN

# If empty, login again
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }' | jq -r '.access_token')
```

### Database queries

```bash
# Connect to postgres
docker exec -it opamp-postgres psql -U opamp -d opamp_db

# View agents
# opamp_db=# SELECT instance_id, host_name, healthy, alert_config FROM agents;

# View configs with alerts
# opamp_db=# SELECT a.instance_id, c.version, c.created_at 
#            FROM agents a 
#            JOIN agent_configs c ON a.instance_id = c.instance_id 
#            WHERE a.alert_config = true;
```

---

## 🧪 Development Tests

### Test endpoints without authentication

```bash
# Health check
curl http://localhost:8000/health

# Root
curl http://localhost:8000/

# Agents (public)
curl http://localhost:8000/api/v1/agents
```

### Test endpoints WITH authentication

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "admin123"}' | jq -r '.access_token')

# Test protected endpoints
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/agents/csv
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/opamp/sync
```

---

## 📊 Monitoring

### View sync statistics

```bash
# Real-time logs
docker logs -f opamp-backend | grep "sync"

# Last sync line
docker logs opamp-backend | grep "OpAMP sync completed" | tail -1
```

### Health checks

```bash
# Backend
curl http://localhost:8000/health

# OpAMP Server
curl http://localhost:4321/

# Postgres
docker exec opamp-postgres pg_isready -U opamp
```

### Database metrics

```bash
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "
SELECT 
  'agents' as table_name, 
  COUNT(*) as count 
FROM agents
UNION ALL
SELECT 
  'agent_health', 
  COUNT(*) 
FROM agent_health
UNION ALL
SELECT 
  'agent_configs', 
  COUNT(*) 
FROM agent_configs
UNION ALL
SELECT 
  'users', 
  COUNT(*) 
FROM users;
"
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
docker compose logs -f backend

# Restart service
docker compose restart backend

# Stop everything
docker compose down

# Stop and remove volumes (WARNING: loses data)
docker compose down -v
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it opamp-postgres psql -U opamp -d opamp_db

# List all tables
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "\dt"

# Check if tables were created
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"

# Count records in each table
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM users;"
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agents;"
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agent_health;"
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agent_configs;"

# View last synchronized agents
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT instance_id, is_connected, last_connection_time FROM agents ORDER BY last_connection_time DESC LIMIT 5;"

# Backup
docker exec opamp-postgres pg_dump -U opamp opamp_db > backup.sql

# Restore
cat backup.sql | docker exec -i opamp-postgres psql -U opamp -d opamp_db
```

### Migrations

```bash
# View status
docker exec opamp-backend alembic current

# Apply all
docker exec opamp-backend alembic upgrade head

# Rollback one version
docker exec opamp-backend alembic downgrade -1
```

---

## 🎯 Next Steps

1. ✅ System running
2. 📱 Explore API via Swagger: http://localhost:8000/docs
3. 🔐 Create additional users
4. 📊 Configure automatic synchronization
5. 🚀 Integrate with frontend application (future)

---

**Need help?** Check the complete [README.md](README.md) or [ARCHITECTURE.md](ARCHITECTURE.md) for details.
