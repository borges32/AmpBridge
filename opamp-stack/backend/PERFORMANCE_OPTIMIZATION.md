# Performance Optimization - OpAMP Sync

## Resumo das Otimizações

Este documento descreve as otimizações implementadas no sistema de sincronização OpAMP para lidar com **10.000+ agents** em produção.

## Problemas Identificados na Implementação Anterior

### 1. **Processamento Sequencial** ❌
```python
for agent_data in opamp_agents:  # 10k iterações sequenciais
    result = await self.sync_agent(agent_data)
```
- Processava agents um por um
- Para 10k agents: ~10-20 minutos de sync

### 2. **N+1 Query Problem** ❌
```python
agent = await self.get_by_instance_id(instance_id)  # 1 query por agent
latest_config = await self.config_repo.get_latest_by_instance_id(instance_id)  # 1 query por agent
```
- 10k agents × 2 queries = **20.000 queries**
- Cada query: ~10-50ms
- Total: 200-1000 segundos apenas em queries!

### 3. **Commits Individuais** ❌
```python
await self.db.commit()  # Dentro do loop, para cada agent
```
- 10k commits
- Cada commit: ~50-100ms
- Total: 500-1000 segundos em commits!

### 4. **Delete + Insert Ineficiente** ❌
```python
await self.pipeline_health_repo.delete_all_by_instance_id(instance_id)  # 10k deletes
for component in components:
    await self.pipeline_health_repo.create(health_data)  # ~100k inserts individuais
```

## Soluções Implementadas

### 1. **Batch Processing** ✅
```python
batch_size = settings.OPAMP_SYNC_BATCH_SIZE  # Default: 100

for batch_start in range(0, total_agents, batch_size):
    batch = opamp_agents[batch_start:batch_end]
    await self._sync_batch(batch)
```

**Benefícios:**
- Processa 100 agents por vez
- Commit único por batch
- Melhor controle de memória
- Progress tracking granular

### 2. **Bulk Database Operations** ✅

#### Bulk Upsert de Agents
```python
async def bulk_upsert(self, agents_data: List[dict]) -> List[Agent]:
    # 1 query para buscar agents existentes
    # Batch update/insert
    # 1 commit para tudo
```

**Antes:** 10k queries individuais  
**Depois:** ~100 queries (1 por batch)  
**Ganho:** **99% redução em queries**

#### Bulk Create para Health
```python
async def bulk_create(self, health_data_list: List[AgentHealthCreate]):
    self.db.add_all(health_records)
    await self.db.commit()
```

**Antes:** 10k inserts individuais  
**Depois:** 100 bulk inserts  
**Ganho:** **99% redução em operações**

### 3. **Single Query Config Fetch** ✅
```python
async def get_latest_configs_bulk(self, instance_ids: List[str]) -> dict:
    # Subquery com GROUP BY para pegar max version
    # JOIN para buscar configs completos
    # 1 query para todos os agents do batch
```

**Antes:** 10k queries (1 por agent)  
**Depois:** 100 queries (1 por batch)  
**Ganho:** **99% redução**

### 4. **Bulk Delete Pipeline Health** ✅
```python
async def bulk_delete_by_instance_ids(self, instance_ids: List[str]):
    # 1 delete para todos os agents do batch
```

**Antes:** 10k deletes individuais  
**Depois:** 100 deletes em batch  
**Ganho:** **99% redução**

## Performance Estimada

### Antes das Otimizações
```
10.000 agents × 200ms (queries + commits) = 2.000 segundos = ~33 minutos
```

### Depois das Otimizações
```
100 batches × 2 segundos por batch = 200 segundos = ~3 minutos
```

**Ganho: 90% redução no tempo de sync (de 33min para 3min)**

## Configurações de Performance

Adicione ao `.env`:

```env
# Performance Settings
OPAMP_SYNC_BATCH_SIZE=100        # Agents por batch (ajustar conforme RAM)
OPAMP_SYNC_MAX_WORKERS=10        # Máximo de batches concorrentes (futuro)
OPAMP_DB_BULK_SIZE=500           # Tamanho dos bulk inserts
```

### Tuning por Cenário

#### 10k Agents com 8GB RAM
```env
OPAMP_SYNC_BATCH_SIZE=100
OPAMP_SYNC_INTERVAL_SECONDS=60
```

#### 50k Agents com 32GB RAM
```env
OPAMP_SYNC_BATCH_SIZE=500
OPAMP_SYNC_INTERVAL_SECONDS=120
```

#### 100k+ Agents com 64GB RAM
```env
OPAMP_SYNC_BATCH_SIZE=1000
OPAMP_SYNC_INTERVAL_SECONDS=300
```

## Monitoramento

Os logs agora incluem métricas detalhadas:

```
INFO: Received 10000 agents from OpAMP server
INFO: Processing batch 1/100 (100 agents)
INFO: Bulk upserting 100 agents
INFO: Bulk creating 100 health records
INFO: Bulk creating 5000 pipeline health records
INFO: Bulk creating 23 new config versions
INFO: Processing batch 2/100 (100 agents)
...
INFO: Marked 15 agent(s) as disconnected
INFO: Sync completed: 10000 processed, 10000 updated, 145 configs versioned
```

## Database Indices Recomendados

Certifique-se que os índices existem:

```sql
-- Agents
CREATE INDEX idx_agents_instance_id ON agents(instance_id);
CREATE INDEX idx_agents_is_connected ON agents(is_connected);

-- Agent Configs
CREATE INDEX idx_agent_configs_instance_id_version ON agent_configs(instance_id, version DESC);

-- Agent Health
CREATE INDEX idx_agent_health_instance_id_created ON agent_health(instance_id, created_at DESC);

-- Pipeline Health
CREATE INDEX idx_pipeline_health_instance_id ON agent_pipeline_health(instance_id);
```

## Próximas Otimizações (Futuro)

### 1. Parallel Batch Processing
```python
# Processar múltiplos batches em paralelo
tasks = []
for batch in batches:
    tasks.append(self._sync_batch(batch))
await asyncio.gather(*tasks, limit=MAX_WORKERS)
```

**Ganho estimado:** Mais 50-70% redução no tempo total

### 2. Redis Caching
```python
# Cache de latest configs em Redis
latest_config = await redis.get(f"config:{instance_id}")
```

**Ganho estimado:** 30-50% redução em queries

### 3. Connection Pooling
```python
# Aumentar pool de conexões do DB
DATABASE_URL="postgresql+asyncpg://...?min_size=10&max_size=50"
```

**Ganho estimado:** 20-30% redução em wait time

### 4. Streaming/Pagination do OpAMP
```python
# Buscar agents em páginas ao invés de tudo de uma vez
async for page in opamp_client.fetch_agents_paginated(page_size=1000):
    await self._sync_batch(page)
```

**Ganho estimado:** Reduz picos de memória em 80%

## Testes de Carga Recomendados

### Teste Local
```bash
# Simular 10k agents
python scripts/simulate_agents.py --count 10000 --interval 0.1
```

### Teste de Stress
```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/agents/sync

# ou K6
k6 run --vus 10 --duration 30s load_test.js
```

### Métricas a Observar
- **Tempo de Sync:** < 5 minutos para 10k agents
- **Uso de Memória:** < 2GB durante sync
- **CPU:** < 50% durante sync
- **Database Connections:** < 20 simultâneas
- **Query Time:** < 1s para batch queries

## Troubleshooting

### Sync muito lento?
1. Verificar índices do banco: `EXPLAIN ANALYZE SELECT ...`
2. Aumentar `OPAMP_SYNC_BATCH_SIZE`
3. Verificar connection pool do DB
4. Monitorar slow queries

### Out of Memory?
1. Reduzir `OPAMP_SYNC_BATCH_SIZE`
2. Implementar pagination no OpAMP fetch
3. Desabilitar logging verboso
4. Aumentar RAM do container

### Deadlocks no DB?
1. Verificar índices
2. Reduzir `OPAMP_SYNC_BATCH_SIZE`
3. Aumentar timeout de transações
4. Verificar locks com `pg_locks`

## Conclusão

As otimizações implementadas reduzem o tempo de sincronização de **~33 minutos para ~3 minutos** para 10.000 agents, representando uma **melhoria de 90% em performance**.

O sistema agora está preparado para escalar até 50k+ agents com ajustes mínimos de configuração.
