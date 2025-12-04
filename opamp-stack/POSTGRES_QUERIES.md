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
