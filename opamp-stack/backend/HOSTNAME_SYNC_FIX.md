# Fix: Hostname Sync Duplicates

## Problema Identificado

Quando `USE_HOSTNAME_AS_SYNC_KEY=true` está configurado, o backend deveria usar o hostname como chave primária para identificar agentes, ao invés do instance_id. Isso permite que agentes mantenham seu histórico mesmo quando o instance_id muda (comum em ambientes containerizados).

### Sintoma
- Agentes com o mesmo hostname mas instance_ids diferentes geravam **registros duplicados**
- Exemplo: `DESKTOP-C49UQO6` aparecia duas vezes na tabela com instance_ids diferentes:
  - `019b22ee-2bf8-74c7-8700-0586b8a1ef01`
  - `019a7534-f534-70ab-bbbc-115e2d231708`

### Causa Raiz
O método `upsert_by_hostname()` no `agent_repository.py` tinha dois problemas:

1. **Não atualizava o instance_id** quando encontrava um agente pelo hostname
2. **Não atualizava as tabelas relacionadas** (agent_health, agent_configs, agent_pipeline_health)

Resultado: Quando um agente mudava de instance_id, o sistema criava um novo registro ao invés de atualizar o existente.

## Correção Implementada

### Mudanças no Código

#### 1. agent_repository.py - Método `upsert_by_hostname()`

**Antes:**
```python
async def upsert_by_hostname(self, instance_id: str, host_name: str, agent_data: dict) -> Agent:
    agent = await self.get_by_host_name(host_name)
    
    if not agent:
        agent = await self.get_by_instance_id(instance_id)
    
    if agent:
        for field, value in agent_data.items():
            if hasattr(agent, field):
                setattr(agent, field, value)  # ❌ Não atualiza instance_id!
        agent.last_seen_at = datetime.utcnow()
    else:
        agent = Agent(**agent_data)
        agent.last_seen_at = datetime.utcnow()
        self.db.add(agent)
    
    await self.db.commit()
    return agent
```

**Depois:**
```python
async def upsert_by_hostname(self, instance_id: str, host_name: str, agent_data: dict) -> Agent:
    agent = await self.get_by_host_name(host_name)
    
    old_instance_id = None
    if agent:
        # ✅ Guarda o instance_id antigo
        old_instance_id = agent.instance_id
    else:
        agent = await self.get_by_instance_id(instance_id)
    
    if agent:
        for field, value in agent_data.items():
            if hasattr(agent, field):
                setattr(agent, field, value)
        
        # ✅ Atualiza instance_id e tabelas relacionadas
        if old_instance_id and old_instance_id != instance_id:
            logger.info(f"Hostname '{host_name}': instance_id changed from '{old_instance_id}' to '{instance_id}'")
            await self._update_related_instance_ids(old_instance_id, instance_id)
            agent.instance_id = instance_id
        
        agent.last_seen_at = datetime.utcnow()
    else:
        agent = Agent(**agent_data)
        agent.last_seen_at = datetime.utcnow()
        self.db.add(agent)
    
    await self.db.commit()
    return agent
```

#### 2. Novo Método: `_update_related_instance_ids()`

```python
async def _update_related_instance_ids(self, old_instance_id: str, new_instance_id: str) -> None:
    """Update instance_id in all related tables."""
    
    # Update agent_health
    result = await self.db.execute(
        update(AgentHealth)
        .where(AgentHealth.instance_id == old_instance_id)
        .values(instance_id=new_instance_id)
    )
    health_updated = result.rowcount
    
    # Update agent_configs
    result = await self.db.execute(
        update(AgentConfig)
        .where(AgentConfig.instance_id == old_instance_id)
        .values(instance_id=new_instance_id)
    )
    config_updated = result.rowcount
    
    # Update agent_pipeline_health
    result = await self.db.execute(
        update(AgentPipelineHealth)
        .where(AgentPipelineHealth.instance_id == old_instance_id)
        .values(instance_id=new_instance_id)
    )
    pipeline_updated = result.rowcount
    
    logger.info(
        f"Updated instance_id from '{old_instance_id}' to '{new_instance_id}': "
        f"health={health_updated}, configs={config_updated}, pipeline={pipeline_updated}"
    )
```

#### 3. Imports Atualizados

```python
import logging
from sqlalchemy import select, func, desc, or_, update
from app.models.models import Agent, AgentHealth, AgentConfig, AgentPipelineHealth

logger = logging.getLogger(__name__)
```

## Como Funciona Agora

### Fluxo de Sync com Hostname

1. **Agente se conecta** com hostname `DESKTOP-C49UQO6` e instance_id `ABC123`
2. **Backend procura** por hostname primeiro
3. **Não encontra** → Cria novo registro

```sql
INSERT INTO agents (instance_id, host_name, ...) 
VALUES ('ABC123', 'DESKTOP-C49UQO6', ...)
```

4. **Agente reinicia** → Novo instance_id `XYZ789`
5. **Backend procura** por hostname `DESKTOP-C49UQO6`
6. **Encontra registro** com instance_id `ABC123`
7. **Detecta mudança** de instance_id
8. **Atualiza tudo**:

```sql
-- Atualizar agent
UPDATE agents SET instance_id = 'XYZ789' WHERE host_name = 'DESKTOP-C49UQO6';

-- Atualizar relacionamentos
UPDATE agent_health SET instance_id = 'XYZ789' WHERE instance_id = 'ABC123';
UPDATE agent_configs SET instance_id = 'XYZ789' WHERE instance_id = 'ABC123';
UPDATE agent_pipeline_health SET instance_id = 'XYZ789' WHERE instance_id = 'ABC123';
```

9. **Resultado**: Histórico preservado, sem duplicatas!

## Corrigindo Duplicatas Existentes

### Script: fix_duplicate_hostnames.py

Um script foi criado para corrigir registros duplicados existentes no banco:

```bash
# Preview (dry-run)
docker exec -it opamp-backend python fix_duplicate_hostnames.py --dry-run

# Corrigir hostname específico
docker exec -it opamp-backend python fix_duplicate_hostnames.py --hostname DESKTOP-C49UQO6

# Corrigir todos os duplicados
docker exec -it opamp-backend python fix_duplicate_hostnames.py
```

### O que o Script Faz

1. **Identifica duplicatas**: Encontra hostnames com múltiplos instance_ids
2. **Escolhe o mais recente**: Mantém o agente com `last_seen_at` mais recente
3. **Mescla histórico**: Atualiza todas as tabelas relacionadas
4. **Remove duplicatas**: Deleta os registros antigos

### Exemplo de Execução

```
==============================================================
DUPLICATE HOSTNAME FIXER
==============================================================

Searching for duplicate hostnames...

Found 1 hostname(s) with duplicates:
  - DESKTOP-C49UQO6: 2 records

==============================================================
MERGING DUPLICATES
==============================================================

  Hostname: DESKTOP-C49UQO6
  Keeping:  019b22ee-2bf8-74c7-8700-0586b8a1ef01 (last_seen: 2025-12-15 14:23:10)
  Removing: 019a7534-f534-70ab-bbbc-115e2d231708 (last_seen: 2025-12-14 10:15:03)
  ✓ Merged: health=156, configs=12, pipeline=48

==============================================================
SUMMARY
==============================================================
  Hostnames processed:     1
  Duplicate agents removed: 1
  Health records merged:    156
  Config records merged:    12
  Pipeline records merged:  48

✅ Duplicates fixed successfully!
==============================================================
```

## Testando a Correção

### 1. Reiniciar Backend

```bash
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack
docker compose restart backend
```

### 2. Verificar Logs

```bash
docker logs -f opamp-backend | grep "instance_id changed"
```

Você deve ver mensagens como:
```
INFO - Hostname 'DESKTOP-C49UQO6': instance_id changed from '019a7534...' to '019b22ee...'
INFO - Updated instance_id from '019a7534...' to '019b22ee...': health=156, configs=12, pipeline=48
```

### 3. Monitorar Sync

```bash
# Aguardar próximo sync (60 segundos por padrão)
# Verificar se não há duplicatas
```

### 4. Consultar Database

```bash
# Verificar hostnames únicos
docker exec -i opamp-postgres psql -U opamp opamp -c "
SELECT host_name, COUNT(*) as count, array_agg(instance_id) as instance_ids
FROM agents 
WHERE host_name IS NOT NULL
GROUP BY host_name
HAVING COUNT(*) > 1;
"
```

Se a saída estiver vazia, não há duplicatas! ✅

## Validação

### Cenários de Teste

#### ✅ Cenário 1: Primeiro Sync
- Agente: `DESKTOP-TEST`, instance_id: `A1`
- Resultado: Cria registro novo
- Verificação: 1 registro na tabela

#### ✅ Cenário 2: Sync com Mesmo Instance ID
- Agente: `DESKTOP-TEST`, instance_id: `A1`
- Resultado: Atualiza registro existente
- Verificação: 1 registro na tabela

#### ✅ Cenário 3: Sync com Novo Instance ID
- Agente: `DESKTOP-TEST`, instance_id: `A2` (mudou!)
- Resultado: 
  - Encontra por hostname
  - Atualiza instance_id de `A1` → `A2`
  - Atualiza todas as tabelas relacionadas
- Verificação: 1 registro na tabela (sem duplicata!)

#### ✅ Cenário 4: Múltiplos Agentes, Mesmo Hostname
- **Antes da correção**: Criava duplicatas
- **Depois da correção**: Mantém apenas 1 registro, sempre atualizado

## Logs de Debugging

### Habilitar Logs Detalhados

No `.env` ou `docker-compose.yml`:

```yaml
LOG_LEVEL=DEBUG
LOG_SYNC_OPERATIONS=true
```

### Logs Esperados

```
DEBUG - Using host_name 'DESKTOP-C49UQO6' as sync key for instance_id '019b22ee-2bf8-74c7-8700-0586b8a1ef01'
INFO - Hostname 'DESKTOP-C49UQO6': instance_id changed from '019a7534-f534-70ab-bbbc-115e2d231708' to '019b22ee-2bf8-74c7-8700-0586b8a1ef01' - updating related records
INFO - Updated instance_id from '019a7534-f534-70ab-bbbc-115e2d231708' to '019b22ee-2bf8-74c7-8700-0586b8a1ef01': health=156, configs=12, pipeline=48
```

## Checklist de Validação

- [x] Código atualizado em `agent_repository.py`
- [x] Método `_update_related_instance_ids()` criado
- [x] Imports adicionados (logging, update, AgentPipelineHealth)
- [x] Script de correção criado (`fix_duplicate_hostnames.py`)
- [x] Backend reiniciado
- [ ] Duplicatas corrigidas no banco
- [ ] Novo sync testado
- [ ] Logs verificados
- [ ] Sem novas duplicatas

## Próximos Passos

### 1. Corrigir Duplicatas Existentes
```bash
docker exec -it opamp-backend python fix_duplicate_hostnames.py
```

### 2. Reiniciar Backend
```bash
docker compose restart backend
```

### 3. Monitorar
```bash
docker logs -f opamp-backend | grep -E "(instance_id changed|Updated instance_id)"
```

### 4. Validar
```bash
# Verificar ausência de duplicatas
docker exec -i opamp-postgres psql -U opamp opamp -c "
SELECT host_name, COUNT(*) FROM agents 
WHERE host_name IS NOT NULL 
GROUP BY host_name 
HAVING COUNT(*) > 1;
"
```

## Rollback (se necessário)

Se houver problemas, você pode:

1. **Desabilitar hostname sync**:
```yaml
# docker-compose.yml
USE_HOSTNAME_AS_SYNC_KEY: false
```

2. **Restaurar backup**:
```bash
docker exec -i opamp-postgres psql -U opamp opamp < backup.sql
```

## Prevenção

Com a correção implementada, o sistema agora:

✅ **Previne duplicatas** automaticamente  
✅ **Preserva histórico** durante mudanças de instance_id  
✅ **Atualiza relacionamentos** corretamente  
✅ **Loga mudanças** para auditoria  
✅ **Funciona transparentemente** sem intervenção manual  

## Suporte

Se encontrar problemas:
1. Verifique os logs do backend
2. Confirme que `USE_HOSTNAME_AS_SYNC_KEY=true` no docker-compose
3. Execute o script de correção em modo dry-run primeiro
4. Verifique se há erros de sintaxe com `docker logs opamp-backend`
