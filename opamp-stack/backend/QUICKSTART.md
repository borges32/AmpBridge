# 🚀 Guia Rápido - OpAMP Backend

Primeiros passos para colocar o sistema no ar e testar funcionalidades.

---

## ⚡ Quick Start (5 minutos)

### 1. Subir o stack

```bash
cd opamp-stack
docker compose up -d
```

Aguarde todos os containers ficarem healthy (~30 segundos):
```bash
docker compose ps
```

### 2. Criar primeiro usuário

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

### 3. Fazer login e obter token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### 4. Disparar sincronização manual

```bash
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN" | jq
```

### 5. Listar agents

```bash
curl http://localhost:8000/api/v1/agents | jq
```

**Pronto!** 🎉 O sistema está funcionando.

---

## 📖 Cenários Comuns

### Cenário 1: Monitorar agents com alertas de config

```bash
# Listar todos os agents
curl http://localhost:8000/api/v1/agents | jq '.agents[] | select(.alert_config == true)'
```

### Cenário 2: Ver histórico de um agent específico

```bash
INSTANCE_ID="019a7534-f534-70ab-bbbc-115e2d231708"

# Dados do agent
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID | jq

# Health history
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID/health | jq

# Config versions
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID/configs | jq
```

### Cenário 3: Baixar configuração de um agent

```bash
# Última versão
curl http://localhost:8000/api/v1/agents/$INSTANCE_ID/config -o config.yaml

# Versão específica
curl "http://localhost:8000/api/v1/agents/$INSTANCE_ID/config?version=2" -o config_v2.yaml
```

### Cenário 4: Atualizar configuração de um agent

```bash
# Preparar config em arquivo
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

# Converter para JSON string (escapar newlines)
CONFIG_JSON=$(cat new_config.yaml | jq -Rs .)

# Enviar para API
curl -X POST "http://localhost:8000/api/v1/config?instance_id=$INSTANCE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"config\": $CONFIG_JSON}" | jq
```

### Cenário 5: Exportar agents para análise

```bash
# CSV export
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/csv -o agents.csv

# Abrir em Excel/LibreOffice
libreoffice agents.csv
```

---

## 🔍 Troubleshooting Rápido

### Backend não inicia

```bash
# Ver logs
docker logs opamp-backend

# Verificar se postgres está up
docker compose ps postgres

# Restart backend
docker compose restart backend
```

### Sync não está funcionando

```bash
# Ver logs de sync
docker logs -f opamp-backend | grep "OpAMP sync"

# Testar conexão com OpAMP
docker exec opamp-backend curl http://opamp-server:4321/agents/full

# Forçar sync manual
curl -X POST http://localhost:8000/api/v1/opamp/sync \
  -H "Authorization: Bearer $TOKEN"
```

### Erro de autenticação

```bash
# Verificar token
echo $TOKEN

# Se vazio, fazer login novamente
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login": "admin",
    "password": "admin123"
  }' | jq -r '.access_token')
```

### Database queries

```bash
# Conectar ao postgres
docker exec -it opamp-postgres psql -U opamp -d opamp_db

# Ver agents
# opamp_db=# SELECT instance_id, host_name, healthy, alert_config FROM agents;

# Ver configs com alertas
# opamp_db=# SELECT a.instance_id, c.version, c.created_at 
#            FROM agents a 
#            JOIN agent_configs c ON a.instance_id = c.instance_id 
#            WHERE a.alert_config = true;
```

---

## 🧪 Testes de Desenvolvimento

### Testar endpoints sem autenticação

```bash
# Health check
curl http://localhost:8000/health

# Root
curl http://localhost:8000/

# Agents (público)
curl http://localhost:8000/api/v1/agents
```

### Testar endpoints COM autenticação

```bash
# Obter token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "admin123"}' | jq -r '.access_token')

# Testar endpoints protegidos
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/agents/csv
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/opamp/sync
```

---

## 📊 Monitoramento

### Ver estatísticas de sync

```bash
# Logs em tempo real
docker logs -f opamp-backend | grep "sync"

# Última linha de sync
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

### Métricas do database

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

## 🛠️ Comandos Úteis

### Docker Compose

```bash
# Subir tudo
docker compose up -d

# Ver status
docker compose ps

# Ver logs
docker compose logs -f backend

# Restart serviço
docker compose restart backend

# Parar tudo
docker compose down

# Parar e remover volumes (CUIDADO: perde dados)
docker compose down -v
```

### Database

```bash
# Conectar ao PostgreSQL
docker exec -it opamp-postgres psql -U opamp -d opamp_db

# Listar todas as tabelas
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "\dt"

# Verificar se as tabelas foram criadas
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"

# Contar registros em cada tabela
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM users;"
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agents;"
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agent_health;"
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT COUNT(*) FROM agent_configs;"

# Ver últimos agents sincronizados
docker exec -it opamp-postgres psql -U opamp -d opamp_db -c "SELECT instance_id, is_connected, last_connection_time FROM agents ORDER BY last_connection_time DESC LIMIT 5;"

# Backup
docker exec opamp-postgres pg_dump -U opamp opamp_db > backup.sql

# Restore
cat backup.sql | docker exec -i opamp-postgres psql -U opamp -d opamp_db
```

### Migrations

```bash
# Ver status
docker exec opamp-backend alembic current

# Aplicar todas
docker exec opamp-backend alembic upgrade head

# Voltar uma versão
docker exec opamp-backend alembic downgrade -1
```

---

## 🎯 Próximos Passos

1. ✅ Sistema funcionando
2. 📱 Explorar API via Swagger: http://localhost:8000/docs
3. 🔐 Criar usuários adicionais
4. 📊 Configurar sincronização automática
5. 🚀 Integrar com aplicação frontend (futuro)

---

**Precisa de ajuda?** Consulte o [README.md](README.md) completo ou [ARCHITECTURE.md](ARCHITECTURE.md) para detalhes.
