# Logging Configuration Guide

## Overview

O sistema de logging do OpAMP Backend é totalmente configurável através de variáveis de ambiente, permitindo controlar o nível de verbosidade e tipos de logs gerados.

## Variáveis de Ambiente

### LOG_LEVEL

Controla o nível geral de logging da aplicação.

**Valores possíveis:**
- `DEBUG` - Todos os logs incluindo detalhes de debug
- `INFO` - Logs informativos e acima (padrão)
- `WARNING` - Apenas avisos e erros
- `ERROR` - Apenas erros
- `CRITICAL` - Apenas erros críticos

**Exemplo:**
```bash
LOG_LEVEL=WARNING
```

### LOG_SYNC_OPERATIONS

Controla os logs detalhados das operações de sincronização OpAMP.

**Valores possíveis:**
- `true` - Exibe logs detalhados de sincronização (padrão)
- `false` - Suprime logs de sincronização (mantém apenas WARNING e acima)

**Recomendação:**
- **Desenvolvimento/Teste**: `true`
- **Produção**: `false` (reduz volume de logs significativamente)

**Logs afetados quando `false`:**
- "Running OpAMP sync..."
- "Received X agents from OpAMP server"
- "Processing batch X/Y"
- "Cleaned up X old health records"
- "Sync completed: X processed, Y updated, Z configs versioned"

**Exemplo:**
```bash
LOG_SYNC_OPERATIONS=false
```

### LOG_HTTP_REQUESTS

Controla os logs de requisições HTTP feitas pela biblioteca httpx.

**Valores possíveis:**
- `true` - Exibe logs de todas as requisições HTTP
- `false` - Suprime logs HTTP (padrão)

**Exemplo:**
```bash
LOG_HTTP_REQUESTS=true
```

## Configuração no Docker Compose

### Opção 1: Variáveis de Ambiente no Host

Defina as variáveis antes de executar o `docker compose`:

```bash
export LOG_LEVEL=WARNING
export LOG_SYNC_OPERATIONS=false
export LOG_HTTP_REQUESTS=false
docker compose up -d
```

### Opção 2: Arquivo .env

Edite o arquivo `backend/.env`:

```dotenv
LOG_LEVEL=WARNING
LOG_SYNC_OPERATIONS=false
LOG_HTTP_REQUESTS=false
```

Depois execute:
```bash
docker compose up -d --build backend
```

### Opção 3: Inline no docker-compose.yml

Edite diretamente o `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - LOG_LEVEL=WARNING
      - LOG_SYNC_OPERATIONS=false
      - LOG_HTTP_REQUESTS=false
```

## Cenários de Uso

### 🔧 Desenvolvimento

Máxima verbosidade para debug:

```bash
LOG_LEVEL=DEBUG
LOG_SYNC_OPERATIONS=true
LOG_HTTP_REQUESTS=true
```

**Logs esperados:**
```
2025-12-02 23:35:54,457 - app.services.opamp_service - INFO - Fetching agents from OpAMP server...
2025-12-02 23:35:54,474 - httpx - INFO - HTTP Request: GET http://opamp-server:4321/agents/full "HTTP/1.1 200 OK"
2025-12-02 23:35:54,475 - app.services.opamp_service - INFO - Received 1 agents from OpAMP server
2025-12-02 23:35:54,475 - app.services.opamp_service - INFO - Processing batch 1/1 (1 agents)
2025-12-02 23:35:54,503 - app.services.opamp_service - INFO - Cleaned up 1 old health records
```

### 🏭 Produção - Modo Normal

Logs informativos sem excessos:

```bash
LOG_LEVEL=INFO
LOG_SYNC_OPERATIONS=true
LOG_HTTP_REQUESTS=false
```

**Logs esperados:**
```
2025-12-02 23:35:54,506 - app.services.opamp_service - INFO - Sync completed: 1 processed, 1 updated, 0 configs versioned
```

### 🏭 Produção - Modo Silencioso

Apenas erros e avisos:

```bash
LOG_LEVEL=WARNING
LOG_SYNC_OPERATIONS=false
LOG_HTTP_REQUESTS=false
```

**Logs esperados:**
- Apenas logs de erro ou warning
- Sincronizações silenciosas (sem logs a cada 60s)
- Requisições HTTP silenciosas

### 🐛 Debug de Problemas

Máxima verbosidade temporária:

```bash
LOG_LEVEL=DEBUG
LOG_SYNC_OPERATIONS=true
LOG_HTTP_REQUESTS=true
```

Depois de resolver, volte para produção:

```bash
LOG_LEVEL=INFO
LOG_SYNC_OPERATIONS=false
LOG_HTTP_REQUESTS=false
```

## Impacto no Volume de Logs

### Com LOG_SYNC_OPERATIONS=true (padrão)

A cada 60 segundos (intervalo de sync), são gerados ~5-10 linhas de log por agent.

**Para 100 agents:**
- ~500-1000 linhas/minuto
- ~30.000-60.000 linhas/hora
- ~720.000-1.440.000 linhas/dia

### Com LOG_SYNC_OPERATIONS=false (recomendado produção)

Apenas logs de erro ou eventos importantes.

**Redução estimada:** ~90% do volume de logs

## Visualização de Logs

### Ver logs em tempo real:
```bash
docker compose logs -f backend
```

### Ver apenas erros:
```bash
docker compose logs backend | grep ERROR
```

### Ver últimas 100 linhas:
```bash
docker compose logs backend --tail 100
```

### Ver logs das últimas 5 minutos:
```bash
docker compose logs backend --since 5m
```

## Troubleshooting

### Logs não mudaram após alterar variáveis

1. Rebuild do container:
   ```bash
   docker compose up -d --build backend
   ```

2. Verificar variáveis aplicadas:
   ```bash
   docker compose exec backend env | grep LOG
   ```

### Muitos logs em produção

Configure:
```bash
LOG_LEVEL=WARNING
LOG_SYNC_OPERATIONS=false
```

### Não aparecem logs de debug

Verifique:
```bash
LOG_LEVEL=DEBUG
```

## Boas Práticas

1. ✅ **Desenvolvimento**: Use `LOG_LEVEL=DEBUG` e `LOG_SYNC_OPERATIONS=true`
2. ✅ **Staging**: Use `LOG_LEVEL=INFO` e `LOG_SYNC_OPERATIONS=true`
3. ✅ **Produção**: Use `LOG_LEVEL=WARNING` e `LOG_SYNC_OPERATIONS=false`
4. ✅ **Monitoramento**: Configure sistema de agregação de logs (ELK, Splunk, etc)
5. ✅ **Rotação**: Configure rotação de logs no Docker/host
6. ❌ **Não use** `DEBUG` em produção (performance e segurança)
7. ❌ **Não use** `LOG_HTTP_REQUESTS=true` em produção (dados sensíveis)

## Exemplo de Configuração Completa

**backend/.env para Produção:**
```dotenv
# Database
DATABASE_URL=postgresql+asyncpg://opamp:opamp_password@postgres:5432/opamp_db

# OpAMP Server
OPAMP_SERVER_URL=http://opamp-server:4321
OPAMP_SYNC_INTERVAL_SECONDS=60

# Performance Settings
OPAMP_SYNC_BATCH_SIZE=100
OPAMP_SYNC_MAX_WORKERS=10
OPAMP_DB_BULK_SIZE=500

# JWT Security
SECRET_KEY=your-production-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
API_V1_PREFIX=/api/v1
PROJECT_NAME=OpAMP Backend API
DEBUG=false

# Logging - Produção Silenciosa
LOG_LEVEL=WARNING
LOG_SYNC_OPERATIONS=false
LOG_HTTP_REQUESTS=false
```
