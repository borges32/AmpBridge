# Database Cleanup Script

Script Python para limpar as tabelas do banco de dados mantendo apenas os usuários.

## Arquivos

- `cleanup_database.py` - Script Python principal
- `cleanup.sh` - Script shell wrapper para facilitar execução

## Funcionalidades

✅ Remove todos os dados de agentes (agents, agent_health, agent_configs, agent_pipeline_health)  
✅ **Preserva todos os usuários** (tabela users)  
✅ Reseta as sequences dos IDs  
✅ Mostra estatísticas antes e depois  
✅ Modo dry-run para preview  
✅ Confirmação de segurança  
✅ Suporte a backup  
✅ Output colorido e detalhado  

## Uso

### 1. Modo Interativo (Recomendado)

```bash
# Do host (recomendado)
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack/backend
./cleanup.sh

# Ou diretamente no container
docker exec -it opamp-backend python cleanup_database.py
```

O script irá:
1. Mostrar estatísticas atuais
2. Pedir confirmação (digite 'YES' para confirmar)
3. Executar a limpeza
4. Mostrar estatísticas finais

### 2. Dry Run (Ver o que seria deletado)

```bash
./cleanup.sh --dry-run

# Ou no container
docker exec -it opamp-backend python cleanup_database.py --dry-run
```

### 3. Com Backup Automático

```bash
# Criar backup antes da limpeza
./cleanup.sh --backup --confirm

# O script mostrará o comando para criar o backup:
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 4. Modo Automático (Sem Confirmação)

```bash
# Use com CUIDADO - não pede confirmação
./cleanup.sh --confirm

# Ou no container
docker exec -it opamp-backend python cleanup_database.py --confirm
```

### 5. Modo Verbose (Detalhado)

```bash
./cleanup.sh --verbose

# Mostra todas as queries SQL executadas
```

## Opções Disponíveis

| Opção | Descrição |
|-------|-----------|
| `--dry-run` | Mostra o que seria deletado sem deletar |
| `--backup` | Mostra comando de backup antes da limpeza |
| `--confirm` | Pula confirmação (automático) |
| `--verbose` | Mostra operações SQL detalhadas |
| `-h, --help` | Mostra ajuda |

## Exemplos de Uso

### Exemplo 1: Preview Seguro

```bash
# Ver exatamente o que será deletado
./cleanup.sh --dry-run
```

Output exemplo:
```
==================================================
DATABASE CLEANUP UTILITY
==================================================

Before Cleanup Statistics:
==================================================
  Agents:                        152
  Agent Health:                3,421
  Agent Configs:                 456
  Agent Pipeline Health:       1,234
  Users (PRESERVED):               3
==================================================

🔍 DRY RUN MODE - No data will be deleted
```

### Exemplo 2: Limpeza com Backup

```bash
# 1. Criar backup primeiro
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Executar limpeza
./cleanup.sh --confirm
```

### Exemplo 3: Limpeza em Pipeline/CI

```bash
# Em scripts automatizados
./cleanup.sh --confirm --verbose > cleanup.log 2>&1
```

### Exemplo 4: Limpeza Rápida para Desenvolvimento

```bash
# Sem backup, sem confirmação (apenas dev!)
./cleanup.sh --confirm
```

## Saída do Script

### Antes da Limpeza
```
==================================================
DATABASE CLEANUP UTILITY
==================================================

Before Cleanup Statistics:
==================================================
  Agents:                        152
  Agent Health:                3,421
  Agent Configs:                 456
  Agent Pipeline Health:       1,234
  Users (PRESERVED):               3
==================================================
```

### Durante a Limpeza
```
🗑️  Starting cleanup...

  Deleting agent_pipeline_health records...
    ✓ Deleted 1,234 records
  Deleting agent_health records...
    ✓ Deleted 3,421 records
  Deleting agent_configs records...
    ✓ Deleted 456 records
  Deleting agents records...
    ✓ Deleted 152 records

  Resetting ID sequences...
    ✓ Sequences reset

  ✓ Changes committed to database
```

### Depois da Limpeza
```
After Cleanup Statistics:
==================================================
  Agents:                          0
  Agent Health:                    0
  Agent Configs:                   0
  Agent Pipeline Health:           0
  Users (PRESERVED):               3
==================================================

==================================================
CLEANUP SUMMARY
==================================================
  Total records deleted: 5,263
  Users preserved:       3
==================================================

✅ Cleanup completed successfully!
```

## Execução Direta no Container

### Via Docker Exec
```bash
# Interativo
docker exec -it opamp-backend python cleanup_database.py

# Com opções
docker exec -it opamp-backend python cleanup_database.py --dry-run
docker exec -it opamp-backend python cleanup_database.py --confirm --verbose
```

### Via Docker Compose Exec
```bash
docker compose exec backend python cleanup_database.py
```

## Tabelas Afetadas

### ❌ Deletadas (com CASCADE)
- `agent_pipeline_health` - Toda a saúde dos pipelines
- `agent_health` - Todo o histórico de saúde dos agentes
- `agent_configs` - Todas as configurações dos agentes
- `agents` - Todos os agentes

### ✅ Preservadas
- `users` - **Todos os usuários são mantidos**

### 🔄 Sequences Resetadas
- `agents_id_seq` → 1
- `agent_health_id_seq` → 1
- `agent_configs_id_seq` → 1
- `agent_pipeline_health_id_seq` → 1

## Segurança

### ⚠️ Avisos Importantes

1. **Operação Irreversível**: Dados deletados não podem ser recuperados
2. **Sempre faça backup em produção**: Use `pg_dump` antes da limpeza
3. **Teste em desenvolvimento primeiro**: Use `--dry-run` para verificar
4. **Confirmação obrigatória**: A menos que use `--confirm`

### 🔒 Proteções Implementadas

- Confirmação manual (digite 'YES')
- Foreign key checks desabilitadas temporariamente
- Transaction com commit/rollback
- Dry-run mode para preview
- Estatísticas antes/depois
- Preservação garantida da tabela users

## Backup e Restore

### Criar Backup Completo
```bash
# Backup completo
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup_full_$(date +%Y%m%d_%H%M%S).sql

# Backup comprimido
docker exec -t opamp-postgres pg_dump -U opamp opamp | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restaurar Backup
```bash
# Restaurar de arquivo SQL
docker exec -i opamp-postgres psql -U opamp opamp < backup_full_20241211_123456.sql

# Restaurar de arquivo comprimido
gunzip -c backup_20241211_123456.sql.gz | docker exec -i opamp-postgres psql -U opamp opamp
```

## Troubleshooting

### Erro: "Container is not running"
```bash
# Verificar status
docker ps -a | grep opamp-backend

# Iniciar container
docker compose up -d backend
```

### Erro: "Permission denied"
```bash
# Tornar script executável
chmod +x cleanup.sh
```

### Erro: "Module not found"
```bash
# Verificar se está no diretório correto
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack/backend

# Ou executar com path absoluto no container
docker exec -it opamp-backend python /app/cleanup_database.py
```

### Script não encontra o banco
```bash
# Verificar se postgres está rodando
docker ps | grep opamp-postgres

# Verificar variável DATABASE_URL
docker exec opamp-backend env | grep DATABASE_URL
```

## Integração com Scripts

### Script Bash
```bash
#!/bin/bash
set -e

echo "Creating backup..."
docker exec -t opamp-postgres pg_dump -U opamp opamp > backup.sql

echo "Cleaning database..."
./cleanup.sh --confirm

echo "Done!"
```

### Script Python
```python
import subprocess
import sys

def cleanup_database(dry_run=False):
    cmd = ["./cleanup.sh"]
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("--confirm")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    print(result.stdout)

# Uso
cleanup_database(dry_run=True)  # Preview
cleanup_database(dry_run=False) # Executar
```

## Agendamento (Cron)

### Limpeza Automática Semanal
```bash
# Editar crontab
crontab -e

# Adicionar linha (toda segunda às 02:00)
0 2 * * 1 cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack/backend && ./cleanup.sh --backup --confirm >> /var/log/db-cleanup.log 2>&1
```

## Performance

- **Tabelas pequenas** (< 1000 registros): ~1-2 segundos
- **Tabelas médias** (1000-10000 registros): ~2-5 segundos
- **Tabelas grandes** (> 10000 registros): ~5-30 segundos

O script usa `DELETE` com foreign keys desabilitadas temporariamente para máxima performance.

## Logs

### Redirecionar para arquivo
```bash
./cleanup.sh --confirm > cleanup_$(date +%Y%m%d_%H%M%S).log 2>&1
```

### Ver apenas erros
```bash
./cleanup.sh --confirm 2> errors.log
```

### Log detalhado
```bash
./cleanup.sh --verbose --confirm | tee cleanup.log
```

## Casos de Uso

### 1. Resetar Ambiente de Desenvolvimento
```bash
./cleanup.sh --confirm
```

### 2. Limpeza Pré-Teste
```bash
# Preview
./cleanup.sh --dry-run

# Executar
./cleanup.sh --confirm
```

### 3. Manutenção de Produção
```bash
# Backup completo
docker exec -t opamp-postgres pg_dump -U opamp opamp | gzip > backup_prod_$(date +%Y%m%d).sql.gz

# Limpeza com confirmação
./cleanup.sh --backup

# Digite 'YES' quando solicitado
```

### 4. CI/CD Pipeline
```bash
# Em .gitlab-ci.yml ou GitHub Actions
- name: Cleanup test database
  run: |
    cd opamp-stack/backend
    ./cleanup.sh --confirm
```

## Suporte

Para problemas ou dúvidas, verifique:
1. Logs do container: `docker logs opamp-backend`
2. Status do banco: `docker exec opamp-postgres pg_isready`
3. Conexão: `docker exec opamp-backend python -c "from app.core.config import settings; print(settings.DATABASE_URL)"`
