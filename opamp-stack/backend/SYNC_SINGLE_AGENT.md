# Endpoint de Sincronização Individual de Agente

## Visão Geral

Foi implementado um novo endpoint que permite sincronizar imediatamente um agente específico com o servidor OpAMP, sem precisar executar a sincronização completa de todos os agentes.

## Endpoint

```
POST /api/v1/opamp/sync/{instance_id}
```

### Parâmetros

- **instance_id** (path): ID da instância do agente a ser sincronizado

### Autenticação

Requer autenticação via JWT token no header:
```
Authorization: Bearer <token>
```

### Resposta de Sucesso

**Status Code:** `200 OK`

```json
{
  "success": true,
  "message": "Agent 019a7534-f534-70ab-bbbc-115e2d231708 synchronized successfully",
  "instance_id": "019a7534-f534-70ab-bbbc-115e2d231708",
  "updated": true,
  "config_versioned": false
}
```

### Resposta de Erro - Agente Não Encontrado

**Status Code:** `404 Not Found`

```json
{
  "detail": "Agent {instance_id} not found in OpAMP server"
}
```

### Resposta de Erro - Não Autenticado

**Status Code:** `401 Unauthorized`

```json
{
  "detail": "Not authenticated"
}
```

## Funcionamento

O endpoint executa as seguintes etapas:

1. **Busca o agente específico** no OpAMP server (`/agents/full`)
2. **Extrai os dados** do agente encontrado
3. **Sincroniza os dados** no banco de dados:
   - Atualiza/cria o registro do agente
   - Cria registro de health
   - Salva informações de pipeline/component health
   - Verifica se houve mudança na configuração (via hash SHA256)
   - Se a configuração mudou, cria nova versão e marca alerta
4. **Retorna resultado** detalhado da sincronização

## Diferenças com Sincronização Completa

| Aspecto | Sincronização Completa | Sincronização Individual |
|---------|----------------------|-------------------------|
| Endpoint | `/api/v1/opamp/sync` | `/api/v1/opamp/sync/{instance_id}` |
| Agentes processados | Todos os agentes | Um agente específico |
| Performance | Processamento em lotes | Processamento direto |
| Uso | Sincronização periódica | Sincronização sob demanda |
| Source marcado | `SYNC_JOB` | `MANUAL_SYNC` |

## Casos de Uso

### 1. Forçar sincronização após alteração manual

Quando um agente foi alterado manualmente e você deseja atualizar imediatamente seus dados no sistema:

```bash
curl -X POST "http://localhost:8000/api/v1/opamp/sync/019a7534-f534-70ab-bbbc-115e2d231708" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Verificar status específico de um agente

Para verificar e atualizar o status de um agente específico sem aguardar a próxima sincronização automática:

```bash
# Sincronizar
curl -X POST "http://localhost:8000/api/v1/opamp/sync/{instance_id}" \
  -H "Authorization: Bearer $TOKEN"

# Verificar resultado
curl "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Integração com webhooks

O endpoint pode ser integrado com sistemas externos que precisam notificar mudanças em agentes específicos:

```javascript
// Webhook handler example
app.post('/webhook/agent-updated', async (req, res) => {
  const { instance_id } = req.body;
  
  // Trigger sync for specific agent
  await fetch(`http://backend:8000/api/v1/opamp/sync/${instance_id}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  res.json({ success: true });
});
```

## Exemplo Completo

```bash
#!/bin/bash

# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "admin123"}' | \
  jq -r '.access_token')

# 2. Listar agentes
AGENT_ID=$(curl -s "http://localhost:8000/api/v1/agents?page=1&page_size=1" \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.agents[0].instance_id')

echo "Syncing agent: $AGENT_ID"

# 3. Sincronizar agente específico
curl -s -X POST "http://localhost:8000/api/v1/opamp/sync/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## Schema de Resposta

### SingleAgentSyncResponse

```python
class SingleAgentSyncResponse(BaseModel):
    """Response for single agent synchronization."""
    success: bool           # Se a sincronização foi bem-sucedida
    message: str           # Mensagem descritiva do resultado
    instance_id: str       # ID da instância do agente
    updated: bool          # Se o agente foi atualizado
    config_versioned: bool # Se uma nova versão de config foi criada
```

## Implementação Técnica

### Service Layer

O método `sync_single_agent` foi adicionado ao `OpAMPService`:

```python
async def sync_single_agent(self, instance_id: str) -> Dict[str, Any]:
    """
    Synchronize a single agent by instance_id.
    Fetches the agent from OpAMP server and updates the database.
    """
    # 1. Fetch agent data from OpAMP
    agent_data = await self.fetch_single_agent_from_opamp(instance_id)
    
    # 2. Check if agent exists
    if not agent_data:
        return {
            "success": False,
            "message": f"Agent {instance_id} not found in OpAMP server",
            ...
        }
    
    # 3. Sync agent data
    result = await self.sync_agent(agent_data, source="MANUAL_SYNC")
    
    # 4. Return result
    return {
        "success": True,
        "message": f"Agent {instance_id} synchronized successfully",
        ...
    }
```

### Router

O endpoint foi adicionado ao router `opamp.py`:

```python
@router.post("/sync/{instance_id}", response_model=SingleAgentSyncResponse)
async def sync_single_agent(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Manually trigger synchronization for a specific agent.
    """
    opamp_service = OpAMPService(db)
    result = await opamp_service.sync_single_agent(instance_id)
    
    if not result["success"] and "not found" in result["message"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    return result
```

## Logs

O endpoint gera logs específicos para rastreamento:

```
INFO - Fetching agent {instance_id} from OpAMP server...
INFO - Synchronizing agent {instance_id}...
INFO - Agent {instance_id} synchronized successfully
```

## Performance

- **Latência:** ~50-100ms para um agente individual
- **Timeout:** 30 segundos (configurável no httpx client)
- **Recursos:** Processamento direto sem necessidade de batch
- **Concorrência:** Seguro para execução paralela (diferentes instance_ids)

## Notas Importantes

1. **Source Tracking:** Sincronizações manuais são marcadas com `source="MANUAL_SYNC"` no histórico de configurações
2. **Health Records:** A sincronização cria um novo registro de health, mas mantém apenas os últimos 5 registros
3. **Config Versioning:** Apenas cria nova versão se o hash SHA256 da configuração mudou
4. **Pipeline Health:** Deleta e recria todos os registros de pipeline health para garantir estado atual

## Documentação da API

A documentação completa está disponível em:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
