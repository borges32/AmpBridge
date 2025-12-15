# Como Executar Queries no PostgreSQL (Container)

## Métodos de Acesso ao PostgreSQL

### 1. Usando Docker Exec (Recomendado)

#### Acesso Interativo ao psql

```bash
# Entrar no container e acessar o psql
docker exec -it opamp-postgres psql -U opamp -d opamp
```

#### Executar Query Direta (Sem Entrar no Container)

```bash
# Executar uma query específica
docker exec -it opamp-postgres psql -U opamp -d opamp -c "SELECT * FROM agents;"
```

### 2. Usando Docker Compose

```bash
# Acesso interativo
docker compose exec postgres psql -U opamp -d opamp

# Query direta
docker compose exec postgres psql -U opamp -d opamp -c "SELECT COUNT(*) FROM agents;"
```

---

## Queries Úteis

### Verificar Agentes

```sql
-- Listar todos os agentes
SELECT instance_id, host_name, os_type, is_connected, healthy 
FROM agents;

-- Contar agentes conectados
SELECT COUNT(*) as total_conectados 
FROM agents 
WHERE is_connected = true;

-- Ver agentes com alerta de config
SELECT instance_id, host_name, alert_config, status_sync 
FROM agents 
WHERE alert_config = true;
```

### Verificar Configurações

```sql
-- Listar versões de config de um agente específico
SELECT version, source, created_at, updated_by_user_id 
FROM agent_configs 
WHERE instance_id = '019a7534-f534-70ab-bbbc-115e2d231708'
ORDER BY version DESC;

-- Contar total de versões por agente
SELECT instance_id, COUNT(*) as total_versoes 
FROM agent_configs 
GROUP BY instance_id;

-- Ver última config de cada agente
SELECT DISTINCT ON (instance_id) 
    instance_id, version, source, created_at 
FROM agent_configs 
ORDER BY instance_id, version DESC;
```

### Verificar Health

```sql
-- Últimos registros de health
SELECT instance_id, healthy, status, created_at 
FROM agent_health 
ORDER BY created_at DESC 
LIMIT 10;

-- Health por agente (último registro)
SELECT DISTINCT ON (instance_id) 
    instance_id, healthy, status, created_at 
FROM agent_health 
ORDER BY instance_id, created_at DESC;
```

### Verificar Pipeline Health

```sql
-- Ver health dos componentes de um agente
SELECT component_type, component_name, parent_pipeline, healthy, status 
FROM agent_pipeline_health 
WHERE instance_id = '019a7534-f534-70ab-bbbc-115e2d231708';

-- Componentes não saudáveis
SELECT instance_id, component_name, component_type, status, last_error 
FROM agent_pipeline_health 
WHERE healthy = false;
```

### Usuários

```sql
-- Listar usuários
SELECT id, name, email, login, is_active 
FROM users;

-- Ver usuário específico
SELECT * FROM users WHERE login = 'admin';
```

---

## Comandos psql Úteis

Quando estiver dentro do psql interativo:

```sql
-- Listar todas as tabelas
\dt

-- Descrever estrutura de uma tabela
\d agents
\d agent_configs
\d agent_health

-- Listar databases
\l

-- Sair do psql
\q
```

---

## Exemplos Práticos

### Verificar Estado Geral do Sistema

```bash
docker exec -it opamp-postgres psql -U opamp -d opamp << EOF
SELECT 
    'Total Agents' as metric, COUNT(*)::text as value FROM agents
UNION ALL
SELECT 
    'Connected Agents', COUNT(*)::text FROM agents WHERE is_connected = true
UNION ALL
SELECT 
    'Healthy Agents', COUNT(*)::text FROM agents WHERE healthy = true
UNION ALL
SELECT 
    'Config Versions', COUNT(*)::text FROM agent_configs
UNION ALL
SELECT 
    'Health Records', COUNT(*)::text FROM agent_health;
EOF
```

### Limpar Dados Antigos (Cuidado!)

```bash
# Limpar registros de health com mais de 30 dias
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "DELETE FROM agent_health WHERE created_at < NOW() - INTERVAL '30 days';"

# Ver quantos registros seriam deletados (antes de deletar)
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "SELECT COUNT(*) FROM agent_health WHERE created_at < NOW() - INTERVAL '30 days';"
```

### Limpar Toda a Base (Manter Apenas Usuários)

⚠️ **ATENÇÃO: Esta operação é IRREVERSÍVEL! Faça backup antes!**

```bash
# 1. FAZER BACKUP PRIMEIRO (OBRIGATÓRIO)
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup_before_cleanup_$(date +%Y%m%d_%H%M%S).sql

# 2. Ver o que será deletado (PREVIEW)
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
SELECT 'agents' as table_name, COUNT(*) as records FROM agents
UNION ALL
SELECT 'agent_health', COUNT(*) FROM agent_health
UNION ALL
SELECT 'agent_configs', COUNT(*) FROM agent_configs
UNION ALL
SELECT 'agent_pipeline_health', COUNT(*) FROM agent_pipeline_health
UNION ALL
SELECT 'users (SERÁ MANTIDO)', COUNT(*) FROM users;
EOF

# 3. LIMPAR TUDO EXCETO USERS (CUIDADO!)
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
-- Desabilitar constraints temporariamente
SET session_replication_role = 'replica';

-- Limpar tabelas relacionadas aos agentes
TRUNCATE TABLE agent_pipeline_health CASCADE;
TRUNCATE TABLE agent_health CASCADE;
TRUNCATE TABLE agent_configs CASCADE;
TRUNCATE TABLE agents CASCADE;

-- Reabilitar constraints
SET session_replication_role = 'origin';

-- Verificar resultado
SELECT 'agents' as table_name, COUNT(*) as remaining_records FROM agents
UNION ALL
SELECT 'agent_health', COUNT(*) FROM agent_health
UNION ALL
SELECT 'agent_configs', COUNT(*) FROM agent_configs
UNION ALL
SELECT 'agent_pipeline_health', COUNT(*) FROM agent_pipeline_health
UNION ALL
SELECT 'users (PRESERVADO)', COUNT(*) FROM users;
EOF

# 4. Reiniciar sequências (IDs começam do 1 novamente)
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
ALTER SEQUENCE agents_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_health_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_configs_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_pipeline_health_id_seq RESTART WITH 1;
EOF
```

### Limpar Base Completa (Incluindo Usuários)

⚠️ **EXTREMO CUIDADO: Apaga TUDO, inclusive usuários!**

```bash
# 1. BACKUP OBRIGATÓRIO
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup_full_cleanup_$(date +%Y%m%d_%H%M%S).sql

# 2. LIMPAR TUDO
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
-- Desabilitar constraints
SET session_replication_role = 'replica';

-- Limpar TODAS as tabelas
TRUNCATE TABLE agent_pipeline_health CASCADE;
TRUNCATE TABLE agent_health CASCADE;
TRUNCATE TABLE agent_configs CASCADE;
TRUNCATE TABLE agents CASCADE;
TRUNCATE TABLE users CASCADE;

-- Reabilitar constraints
SET session_replication_role = 'origin';

-- Resetar sequências
ALTER SEQUENCE agents_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_health_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_configs_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_pipeline_health_id_seq RESTART WITH 1;
ALTER SEQUENCE users_id_seq RESTART WITH 1;

-- Verificar que está tudo vazio
SELECT 'agents' as table_name, COUNT(*) as records FROM agents
UNION ALL SELECT 'agent_health', COUNT(*) FROM agent_health
UNION ALL SELECT 'agent_configs', COUNT(*) FROM agent_configs
UNION ALL SELECT 'agent_pipeline_health', COUNT(*) FROM agent_pipeline_health
UNION ALL SELECT 'users', COUNT(*) FROM users;
EOF

# 3. Recriar usuário admin (se necessário)
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "INSERT INTO users (name, email, login, hashed_password, is_active, created_at, updated_at) 
   VALUES ('Admin', 'admin@example.com', 'admin', 
   '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyMGzBfKwxiW', 
   true, NOW(), NOW());"
```

### Script Completo de Limpeza (Recomendado)

Salve como `cleanup_database.sh`:

```bash
#!/bin/bash

# Script para limpar base de dados mantendo usuários
# Uso: ./cleanup_database.sh

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Limpeza de Base de Dados${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

# Verificar se PostgreSQL está rodando
if ! docker ps | grep -q opamp-postgres; then
    echo -e "${RED}❌ Container PostgreSQL não está rodando${NC}"
    exit 1
fi

# Mostrar estatísticas atuais
echo -e "${YELLOW}Estatísticas atuais:${NC}"
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
SELECT 'agents' as table_name, COUNT(*) as records FROM agents
UNION ALL SELECT 'agent_health', COUNT(*) FROM agent_health
UNION ALL SELECT 'agent_configs', COUNT(*) FROM agent_configs
UNION ALL SELECT 'agent_pipeline_health', COUNT(*) FROM agent_pipeline_health
UNION ALL SELECT 'users', COUNT(*) FROM users
ORDER BY table_name;
EOF
echo ""

# Confirmar ação
echo -e "${RED}⚠️  ATENÇÃO: Esta operação irá DELETAR todos os dados de agentes!${NC}"
echo -e "${YELLOW}Os usuários serão MANTIDOS.${NC}"
echo ""
read -p "Deseja continuar? (digite 'SIM' para confirmar): " confirm

if [ "$confirm" != "SIM" ]; then
    echo -e "${GREEN}Operação cancelada.${NC}"
    exit 0
fi

# Fazer backup
echo ""
echo -e "${YELLOW}[1/3] Criando backup...${NC}"
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
docker exec -t opamp-postgres pg_dump -U opamp opamp > "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup criado: $BACKUP_FILE${NC}"

# Limpar base
echo ""
echo -e "${YELLOW}[2/3] Limpando base de dados...${NC}"
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
SET session_replication_role = 'replica';
TRUNCATE TABLE agent_pipeline_health CASCADE;
TRUNCATE TABLE agent_health CASCADE;
TRUNCATE TABLE agent_configs CASCADE;
TRUNCATE TABLE agents CASCADE;
SET session_replication_role = 'origin';

ALTER SEQUENCE agents_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_health_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_configs_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_pipeline_health_id_seq RESTART WITH 1;
EOF
echo -e "${GREEN}✓ Base limpa com sucesso${NC}"

# Verificar resultado
echo ""
echo -e "${YELLOW}[3/3] Verificando resultado...${NC}"
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
SELECT 'agents' as table_name, COUNT(*) as records FROM agents
UNION ALL SELECT 'agent_health', COUNT(*) FROM agent_health
UNION ALL SELECT 'agent_configs', COUNT(*) FROM agent_configs
UNION ALL SELECT 'agent_pipeline_health', COUNT(*) FROM agent_pipeline_health
UNION ALL SELECT 'users (PRESERVADO)', COUNT(*) FROM users
ORDER BY table_name;
EOF

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Limpeza concluída com sucesso!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Backup salvo em: $BACKUP_FILE${NC}"
echo -e "${YELLOW}Para restaurar: docker exec -i opamp-postgres psql -U opamp opamp < $BACKUP_FILE${NC}"
echo ""
```

### Comandos Rápidos de Limpeza

```bash
# Limpar apenas health antigo (> 7 dias)
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "DELETE FROM agent_health WHERE created_at < NOW() - INTERVAL '7 days';"

# Limpar apenas pipeline health antigo (> 1 dia)
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "DELETE FROM agent_pipeline_health WHERE created_at < NOW() - INTERVAL '1 day';"

# Deletar agentes desconectados há mais de 30 dias
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "DELETE FROM agents WHERE is_connected = false AND updated_at < NOW() - INTERVAL '30 days';"

# Deletar versões antigas de config (manter apenas últimas 10 por agente)
docker exec -it opamp-postgres psql -U opamp -d opamp << 'EOF'
DELETE FROM agent_configs
WHERE id NOT IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY instance_id ORDER BY version DESC) as rn
    FROM agent_configs
  ) sub
  WHERE rn <= 10
);
EOF
```

### Backup de Dados

```bash
# Fazer dump completo do database
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup_$(date +%Y%m%d_%H%M%S).sql

# Fazer dump de uma tabela específica
docker exec -t opamp-postgres pg_dump -U opamp opamp -t agents > agents_backup.sql
```

### Restaurar Backup

```bash
# Restaurar dump completo
docker exec -i opamp-postgres psql -U opamp opamp < backup.sql

# Restaurar tabela específica
docker exec -i opamp-postgres psql -U opamp opamp < agents_backup.sql
```

---

## Informações de Conexão

- **Host**: localhost (ou opamp-postgres dentro da rede Docker)
- **Porta**: 5432
- **Database**: opamp
- **Usuário**: opamp
- **Senha**: opamp123 (padrão - veja `.env` para confirmar)

### Conectar de Fora do Container (via localhost)

```bash
# Usando psql instalado localmente
psql -h localhost -p 5432 -U opamp -d opamp

# Você será solicitado a informar a senha: opamp123
```

### String de Conexão

```
postgresql://opamp:opamp123@localhost:5432/opamp
```

---

## Troubleshooting

### Container PostgreSQL não está rodando

```bash
# Verificar status
docker ps | grep postgres

# Iniciar se estiver parado
docker compose up -d postgres
```

### Erro de permissão

```bash
# Verificar se está usando o usuário correto
docker exec -it opamp-postgres psql -U opamp -d opamp
```

### Database não existe

```bash
# Listar databases disponíveis
docker exec -it opamp-postgres psql -U opamp -l
```

---

## Queries de Análise

### Performance de Sincronização

```sql
-- Ver quantas configs foram criadas por fonte
SELECT source, COUNT(*) as total 
FROM agent_configs 
GROUP BY source 
ORDER BY total DESC;

-- Agentes com mais versões de config
SELECT instance_id, COUNT(*) as versoes 
FROM agent_configs 
GROUP BY instance_id 
ORDER BY versoes DESC 
LIMIT 10;
```

### Histórico de Atividade

```sql
-- Últimas atualizações de config
SELECT ac.instance_id, a.host_name, ac.version, ac.source, ac.created_at, u.login as updated_by
FROM agent_configs ac
LEFT JOIN agents a ON ac.instance_id = a.instance_id
LEFT JOIN users u ON ac.updated_by_user_id = u.id
ORDER BY ac.created_at DESC
LIMIT 20;

-- Timeline de conexão dos agentes
SELECT instance_id, host_name, 
       CASE WHEN is_connected THEN 'Online' ELSE 'Offline' END as status,
       last_seen_at
FROM agents
ORDER BY last_seen_at DESC;
```
