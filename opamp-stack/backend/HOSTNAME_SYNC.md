# Sincronização por Hostname

## Visão Geral

Por padrão, o sistema usa o `instance_id` fornecido pelo OpAMP server como chave primária para identificar e sincronizar agentes. No entanto, em alguns cenários, pode ser útil usar o `host_name` como chave de identificação, especialmente quando:

- O `instance_id` muda frequentemente (por exemplo, em ambientes containerizados)
- Você deseja manter o histórico de um agente mesmo quando ele é recriado
- O `host_name` é mais estável do que o `instance_id`

Esta funcionalidade permite que o sistema use o `host_name` como chave de identificação, mantendo o `instance_id` atualizado para preservar os relacionamentos entre tabelas.

## Como Funciona

### Modo Padrão (USE_HOSTNAME_AS_SYNC_KEY=false)

```
OpAMP Agent → instance_id → Busca/Cria no DB usando instance_id
```

- O sistema busca o agente pelo `instance_id`
- Se não existir, cria um novo registro
- Se existir, atualiza os dados do agente

### Modo Hostname (USE_HOSTNAME_AS_SYNC_KEY=true)

```
OpAMP Agent → host_name → Busca no DB usando host_name
                        → Atualiza instance_id se mudou
                        → Atualiza registros relacionados
```

- O sistema busca o agente pelo `host_name`
- Se encontrar um agente com o mesmo `host_name` mas `instance_id` diferente:
  - Atualiza o `instance_id` do agente
  - Atualiza o `instance_id` em todas as tabelas relacionadas:
    - `agent_health`
    - `agent_configs`
    - `agent_pipeline_health`
- Se não encontrar, cria um novo registro

## Configuração

### 1. Via Docker Compose (Recomendado)

Edite o arquivo `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - USE_HOSTNAME_AS_SYNC_KEY=true  # Ativa sincronização por hostname
```

Ou defina a variável de ambiente antes de iniciar:

```bash
export USE_HOSTNAME_AS_SYNC_KEY=true
docker compose up -d backend
```

### 2. Via Arquivo .env

Edite o arquivo `backend/.env`:

```env
USE_HOSTNAME_AS_SYNC_KEY=true
```

### 3. Reiniciar o Backend

Após alterar a configuração:

```bash
docker compose restart backend
```

## Casos de Uso

### Cenário 1: Agentes em Containers

**Problema:** Containers são recriados frequentemente e recebem novos `instance_id`

**Solução:** Use `USE_HOSTNAME_AS_SYNC_KEY=true`

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      - USE_HOSTNAME_AS_SYNC_KEY=true
```

**Resultado:**
- O agente mantém seu histórico mesmo após ser recriado
- Configurações anteriores são preservadas
- Health history continua do mesmo agente

### Cenário 2: Migração de Agentes

**Problema:** Você está migrando agentes entre diferentes instâncias mas quer manter o hostname

**Solução:** Ative temporariamente durante a migração

```bash
# Ativar
export USE_HOSTNAME_AS_SYNC_KEY=true
docker compose restart backend

# Aguardar migração completar
# ...

# Desativar (opcional)
export USE_HOSTNAME_AS_SYNC_KEY=false
docker compose restart backend
```

### Cenário 3: Ambientes de Desenvolvimento

**Problema:** Desenvolvedores reiniciam agentes frequentemente

**Solução:** Configure permanentemente no ambiente de dev

```yaml
# docker-compose.dev.yml
services:
  backend:
    environment:
      - USE_HOSTNAME_AS_SYNC_KEY=true
      - LOG_LEVEL=DEBUG
```

## Comportamento Detalhado

### Quando instance_id Muda

1. **Detecção:**
   - Sistema busca agente pelo `host_name`
   - Encontra agente com `instance_id` diferente do OpAMP

2. **Atualização do Agente:**
   ```sql
   UPDATE agents 
   SET instance_id = 'novo_instance_id',
       -- outros campos...
   WHERE host_name = 'meu-servidor';
   ```

3. **Atualização de Relacionamentos:**
   ```sql
   -- Agent Health
   UPDATE agent_health 
   SET instance_id = 'novo_instance_id' 
   WHERE instance_id = 'antigo_instance_id';
   
   -- Agent Configs
   UPDATE agent_configs 
   SET instance_id = 'novo_instance_id' 
   WHERE instance_id = 'antigo_instance_id';
   
   -- Agent Pipeline Health
   UPDATE agent_pipeline_health 
   SET instance_id = 'novo_instance_id' 
   WHERE instance_id = 'antigo_instance_id';
   ```

4. **Resultado:**
   - Todo o histórico é preservado
   - Relacionamentos mantidos
   - Nenhum dado é perdido

### Quando host_name é Nulo

Se o OpAMP não fornecer `host_name`, o sistema automaticamente volta para o modo padrão (por `instance_id`) para aquele agente específico.

```python
# Fallback automático
if settings.USE_HOSTNAME_AS_SYNC_KEY and host_name:
    agent = await self.agent_repo.upsert_by_hostname(instance_id, host_name, agent_dict)
else:
    agent = await self.agent_repo.upsert(instance_id, agent_dict)
```

## Logs

### Modo Debug

Para ver logs detalhados da sincronização:

```yaml
environment:
  - LOG_LEVEL=DEBUG
  - USE_HOSTNAME_AS_SYNC_KEY=true
```

**Exemplo de log:**

```
DEBUG - Using host_name 'web-server-01' as sync key for instance_id '019a7534-f534-70ab-bbbc-115e2d231708'
INFO - Updated instance_id from '019a1234-...' to '019a7534-...' for host 'web-server-01'
INFO - Updated 45 related health records
INFO - Updated 12 related config records
INFO - Updated 8 related pipeline health records
```

## Considerações Importantes

### ⚠️ Cuidados

1. **Hostname Duplicados:**
   - Certifique-se de que os hostnames são únicos
   - Caso contrário, múltiplos agentes serão mesclados em um único registro

2. **Mudança de Hostname:**
   - Se o hostname mudar, um novo agente será criado
   - O histórico anterior ficará associado ao hostname antigo

3. **Performance:**
   - A atualização de relacionamentos é performática mas adiciona overhead
   - Recomendado apenas quando necessário

4. **Integridade de Dados:**
   - A funcionalidade mantém a integridade referencial
   - Mas pode causar confusão se não documentado adequadamente

### ✅ Boas Práticas

1. **Documente a Configuração:**
   ```yaml
   # Usando hostname sync para ambiente containerizado
   # onde instance_id muda a cada deploy
   - USE_HOSTNAME_AS_SYNC_KEY=true
   ```

2. **Monitore Mudanças de instance_id:**
   ```sql
   SELECT 
     instance_id, 
     host_name, 
     updated_at 
   FROM agents 
   WHERE updated_at > NOW() - INTERVAL '1 hour'
   ORDER BY updated_at DESC;
   ```

3. **Teste Antes de Produção:**
   - Ative em ambiente de desenvolvimento primeiro
   - Verifique comportamento com seus agentes
   - Confirme que histórico é preservado

## Verificação

### Confirmar Configuração Ativa

```bash
# Ver logs do backend
docker logs opamp-backend | grep "USE_HOSTNAME_AS_SYNC_KEY"

# Ou verificar variável de ambiente
docker exec opamp-backend env | grep USE_HOSTNAME_AS_SYNC_KEY
```

### Testar Funcionamento

1. **Antes de ativar:**
   ```bash
   # Anotar instance_id atual
   docker exec -it opamp-postgres psql -U opamp -d opamp -c \
     "SELECT instance_id, host_name FROM agents WHERE host_name = 'seu-host';"
   ```

2. **Ativar configuração:**
   ```bash
   export USE_HOSTNAME_AS_SYNC_KEY=true
   docker compose restart backend
   ```

3. **Simular mudança de instance_id:**
   - Reinicie o agente OpAMP
   - Aguarde próxima sincronização (60s)

4. **Verificar atualização:**
   ```bash
   # Ver novo instance_id
   docker exec -it opamp-postgres psql -U opamp -d opamp -c \
     "SELECT instance_id, host_name, updated_at FROM agents WHERE host_name = 'seu-host';"
   
   # Verificar que histórico foi preservado
   docker exec -it opamp-postgres psql -U opamp -d opamp -c \
     "SELECT COUNT(*) FROM agent_configs WHERE instance_id = 'novo_instance_id';"
   ```

## Troubleshooting

### Agentes Duplicados

**Problema:** Vários registros para o mesmo host

**Causa:** Hostname inconsistente ou nulo

**Solução:**
```sql
-- Verificar agentes duplicados
SELECT host_name, COUNT(*) 
FROM agents 
GROUP BY host_name 
HAVING COUNT(*) > 1;

-- Limpar duplicatas (CUIDADO!)
-- Backup primeiro!
DELETE FROM agents 
WHERE id NOT IN (
  SELECT MAX(id) 
  FROM agents 
  GROUP BY host_name
);
```

### História Perdida

**Problema:** Histórico não foi transferido

**Causa:** Funcionalidade foi ativada após mudança de instance_id

**Solução:** A funcionalidade só previne perda futura. Para recuperar histórico antigo:
```sql
-- Transferir manualmente (exemplo)
UPDATE agent_configs 
SET instance_id = 'novo_id' 
WHERE instance_id = 'id_antigo';
```

### Performance Lenta

**Problema:** Sincronização está lenta

**Causa:** Muitos registros relacionados para atualizar

**Solução:**
```sql
-- Ver quantos registros serão atualizados
SELECT 
  'health' as table_name, 
  COUNT(*) as records 
FROM agent_health 
WHERE instance_id = 'old_id'
UNION ALL
SELECT 'configs', COUNT(*) FROM agent_configs WHERE instance_id = 'old_id'
UNION ALL  
SELECT 'pipeline', COUNT(*) FROM agent_pipeline_health WHERE instance_id = 'old_id';
```

Se tiver muitos registros, considere:
- Fazer cleanup de dados antigos antes
- Aumentar recursos do backend
- Desativar a funcionalidade temporariamente

## Migração

### De Modo Padrão para Hostname

```bash
# 1. Fazer backup
docker exec opamp-postgres pg_dump -U opamp opamp > backup.sql

# 2. Ativar configuração
echo "USE_HOSTNAME_AS_SYNC_KEY=true" >> backend/.env

# 3. Reiniciar
docker compose restart backend

# 4. Monitorar logs
docker logs -f opamp-backend

# 5. Verificar funcionamento
# (aguardar alguns ciclos de sync)
```

### De Hostname para Modo Padrão

```bash
# 1. Desativar configuração
sed -i 's/USE_HOSTNAME_AS_SYNC_KEY=true/USE_HOSTNAME_AS_SYNC_KEY=false/' backend/.env

# 2. Reiniciar
docker compose restart backend

# Nota: Dados existentes não serão afetados
# Apenas novas sincronizações usarão instance_id
```

## Referências

- Código: `app/repositories/agent_repository.py` - método `upsert_by_hostname()`
- Configuração: `app/core/config.py` - parâmetro `USE_HOSTNAME_AS_SYNC_KEY`
- Service: `app/services/opamp_service.py` - método `sync_agent()`
