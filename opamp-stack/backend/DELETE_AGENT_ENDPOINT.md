# Endpoint: DELETE Agent

## Visão Geral

Novo endpoint implementado para excluir permanentemente um agent e todo seu histórico associado do sistema.

## Detalhes do Endpoint

**URL:** `DELETE /api/v1/agents/{instance_id}`

**Autenticação:** Requerida (Bearer Token)

**Parâmetros:**
- `instance_id` (path, required): ID da instância do agent a ser excluído

## Funcionalidade

Este endpoint remove permanentemente:

1. ✅ **Agent** - Informações básicas do agent (tabela `agents`)
2. ✅ **Health History** - Todos os registros de saúde (tabela `agent_health`)
3. ✅ **Config Versions** - Todas as versões de configuração (tabela `agent_configs`)
4. ✅ **Pipeline Health** - Todos os registros de saúde de pipelines/componentes (tabela `agent_pipeline_health`)

### Cascade Delete

A exclusão é realizada através de **CASCADE DELETE** do banco de dados:
- O relacionamento `pipeline_health_records` foi adicionado ao modelo `Agent`
- Configurado com `cascade="all, delete-orphan"` e `passive_deletes=True`
- Foreign keys já tinham `ondelete="CASCADE"` configurado

## Request

```bash
curl -X DELETE "http://localhost:8000/api/v1/agents/{instance_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Exemplo com jq

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/agents/agent-123" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.'
```

## Response

### Sucesso (200 OK)

```json
{
  "success": true,
  "message": "Agent 'agent-123' and all its history have been permanently deleted",
  "instance_id": "agent-123"
}
```

### Agent Não Encontrado (404 Not Found)

```json
{
  "detail": "Agent with instance_id 'agent-123' not found"
}
```

### Não Autenticado (401 Unauthorized)

```json
{
  "detail": "Not authenticated"
}
```

## Implementação

### 1. Modelo (`models.py`)

Adicionado novo relacionamento ao modelo `Agent`:

```python
pipeline_health_records: Mapped[list["AgentPipelineHealth"]] = relationship(
    "AgentPipelineHealth", 
    foreign_keys="[AgentPipelineHealth.instance_id]",
    cascade="all, delete-orphan",
    passive_deletes=True
)
```

### 2. Repository (`agent_repository.py`)

Novo método `delete_with_history`:

```python
async def delete_with_history(self, instance_id: str) -> bool:
    """Delete an agent and all its associated history.
    
    Returns:
        True if agent was found and deleted, False if not found
    """
    agent = await self.get_by_instance_id(instance_id)
    
    if not agent:
        return False
    
    # Delete agent - cascades to all related records
    await self.db.delete(agent)
    await self.db.commit()
    
    return True
```

### 3. Router (`agents.py`)

Novo endpoint DELETE:

```python
@router.delete("/{instance_id}", status_code=status.HTTP_200_OK)
async def delete_agent(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an agent and all its associated history."""
    agent_repo = AgentRepository(db)
    deleted = await agent_repo.delete_with_history(instance_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with instance_id '{instance_id}' not found"
        )
    
    return {
        "success": True,
        "message": f"Agent '{instance_id}' and all its history have been permanently deleted",
        "instance_id": instance_id
    }
```

## Teste

### Script de Teste

Um script de teste foi criado: `test_delete_agent.sh`

```bash
# Uso
./test_delete_agent.sh <instance_id>

# Exemplo
./test_delete_agent.sh agent-123
```

O script:
1. Faz login e obtém token
2. Verifica se o agent existe
3. Obtém estatísticas antes da exclusão
4. Deleta o agent
5. Verifica que o agent foi removido
6. Obtém estatísticas após exclusão

### Teste Manual

```bash
# 1. Obter token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# 2. Listar agents
curl -s -X GET "http://localhost:8000/api/v1/agents?page=1&page_size=10" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.agents[] | .instance_id'

# 3. Deletar um agent específico
curl -X DELETE "http://localhost:8000/api/v1/agents/YOUR_INSTANCE_ID" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.'

# 4. Verificar que foi deletado
curl -s -X GET "http://localhost:8000/api/v1/agents/YOUR_INSTANCE_ID" \
  -H "Authorization: Bearer ${TOKEN}"
```

## Validação em SQL

Para verificar a exclusão completa no banco:

```sql
-- Verificar que o agent foi removido
SELECT COUNT(*) FROM agents WHERE instance_id = 'agent-123';
-- Resultado esperado: 0

-- Verificar que health records foram removidos
SELECT COUNT(*) FROM agent_health WHERE instance_id = 'agent-123';
-- Resultado esperado: 0

-- Verificar que configs foram removidos
SELECT COUNT(*) FROM agent_configs WHERE instance_id = 'agent-123';
-- Resultado esperado: 0

-- Verificar que pipeline health foi removido
SELECT COUNT(*) FROM agent_pipeline_health WHERE instance_id = 'agent-123';
-- Resultado esperado: 0
```

## Considerações de Segurança

⚠️ **IMPORTANTE:** Esta operação é **irreversível**!

- Requer autenticação (token JWT válido)
- Remove permanentemente todos os dados do agent
- Não há confirmação adicional
- Não há funcionalidade de "restore" ou "undo"

### Recomendações

1. **Backup**: Antes de usar em produção, certifique-se de ter backups regulares
2. **Audit Log**: Considere implementar um log de auditoria para rastrear exclusões
3. **Soft Delete**: Para ambientes de produção críticos, considere implementar "soft delete" (marcar como deletado ao invés de remover)
4. **Confirmação UI**: No frontend, implemente confirmação dupla antes de chamar este endpoint

## Documentação OpenAPI

O endpoint aparece automaticamente na documentação Swagger:

```
http://localhost:8000/docs#/Agents/delete_agent_agents__instance_id__delete
```

## Changelog

- **2025-11-24**: Endpoint DELETE implementado
  - Adicionado relacionamento `pipeline_health_records` no modelo `Agent`
  - Criado método `delete_with_history` no `AgentRepository`
  - Implementado endpoint `DELETE /api/v1/agents/{instance_id}`
  - Script de teste criado: `test_delete_agent.sh`
