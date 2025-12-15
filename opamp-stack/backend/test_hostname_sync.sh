#!/bin/bash

# Script para testar sincronização por hostname
# Demonstra como a funcionalidade mantém o histórico quando instance_id muda

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Teste de Sincronização por Hostname${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verificar se PostgreSQL está rodando
if ! docker ps | grep -q opamp-postgres; then
    echo -e "${RED}❌ Container PostgreSQL não está rodando${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/7] Verificando configuração atual...${NC}"
CURRENT_CONFIG=$(docker exec opamp-backend env | grep USE_HOSTNAME_AS_SYNC_KEY || echo "USE_HOSTNAME_AS_SYNC_KEY=false")
echo "  Configuração: $CURRENT_CONFIG"
echo ""

# Escolher um agente para teste
echo -e "${YELLOW}[2/7] Buscando agente de teste...${NC}"
TEST_AGENT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT instance_id, host_name FROM agents WHERE host_name IS NOT NULL LIMIT 1;")

if [ -z "$TEST_AGENT" ]; then
    echo -e "${RED}❌ Nenhum agente encontrado com host_name${NC}"
    echo -e "${YELLOW}Aguarde a sincronização criar agentes...${NC}"
    exit 1
fi

INSTANCE_ID=$(echo "$TEST_AGENT" | awk '{print $1}' | tr -d ' \r\n')
HOST_NAME=$(echo "$TEST_AGENT" | awk '{print $3}' | tr -d ' \r\n')

echo -e "${GREEN}  Agente selecionado:${NC}"
echo "    Instance ID: $INSTANCE_ID"
echo "    Hostname: $HOST_NAME"
echo ""

echo -e "${YELLOW}[3/7] Coletando estado inicial...${NC}"

# Contar registros relacionados
HEALTH_COUNT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT COUNT(*) FROM agent_health WHERE instance_id = '$INSTANCE_ID';" | tr -d ' \r\n')
CONFIG_COUNT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT COUNT(*) FROM agent_configs WHERE instance_id = '$INSTANCE_ID';" | tr -d ' \r\n')
PIPELINE_COUNT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT COUNT(*) FROM agent_pipeline_health WHERE instance_id = '$INSTANCE_ID';" | tr -d ' \r\n')

echo "  Registros de Health: $HEALTH_COUNT"
echo "  Registros de Config: $CONFIG_COUNT"
echo "  Registros de Pipeline: $PIPELINE_COUNT"
echo ""

echo -e "${YELLOW}[4/7] Ativando sincronização por hostname...${NC}"

# Verificar se já está ativo
if echo "$CURRENT_CONFIG" | grep -q "true"; then
    echo -e "${GREEN}  ✓ Já está ativo${NC}"
else
    echo "  Atualizando docker-compose.yml..."
    
    # Criar backup
    cp docker-compose.yml docker-compose.yml.backup
    
    # Atualizar configuração
    sed -i 's/USE_HOSTNAME_AS_SYNC_KEY:-false/USE_HOSTNAME_AS_SYNC_KEY:-true/' docker-compose.yml
    
    # Reiniciar backend
    echo "  Reiniciando backend..."
    docker compose restart backend > /dev/null 2>&1
    
    # Aguardar backend ficar pronto
    echo -e "${YELLOW}  Aguardando backend inicializar...${NC}"
    sleep 10
    
    # Verificar se subiu
    for i in {1..30}; do
        if docker exec opamp-backend curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}  ✓ Backend pronto${NC}"
            break
        fi
        sleep 1
    done
fi
echo ""

echo -e "${YELLOW}[5/7] Simulando mudança de instance_id...${NC}"
echo "  Criando novo instance_id simulado..."

NEW_INSTANCE_ID="sim-$(date +%s)-test-hostname-sync"

# Atualizar manualmente para simular mudança
docker exec -it opamp-postgres psql -U opamp -d opamp -c \
  "UPDATE agents SET instance_id = '$NEW_INSTANCE_ID' WHERE host_name = '$HOST_NAME';" > /dev/null

echo -e "${GREEN}  ✓ Instance ID alterado para: $NEW_INSTANCE_ID${NC}"
echo ""

echo -e "${YELLOW}[6/7] Verificando preservação de dados...${NC}"

# Verificar se registros relacionados também foram atualizados
NEW_HEALTH_COUNT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT COUNT(*) FROM agent_health WHERE instance_id = '$NEW_INSTANCE_ID';" | tr -d ' \r\n')
NEW_CONFIG_COUNT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT COUNT(*) FROM agent_configs WHERE instance_id = '$NEW_INSTANCE_ID';" | tr -d ' \r\n')
NEW_PIPELINE_COUNT=$(docker exec -it opamp-postgres psql -U opamp -d opamp -t -c \
  "SELECT COUNT(*) FROM agent_pipeline_health WHERE instance_id = '$NEW_INSTANCE_ID';" | tr -d ' \r\n')

echo "  Registros com novo instance_id:"
echo "    Health: $NEW_HEALTH_COUNT (antes: $HEALTH_COUNT)"
echo "    Config: $NEW_CONFIG_COUNT (antes: $CONFIG_COUNT)"
echo "    Pipeline: $NEW_PIPELINE_COUNT (antes: $PIPELINE_COUNT)"

# Verificar se dados foram preservados
if [ "$NEW_HEALTH_COUNT" -eq "$HEALTH_COUNT" ] && \
   [ "$NEW_CONFIG_COUNT" -eq "$CONFIG_COUNT" ] && \
   [ "$NEW_PIPELINE_COUNT" -eq "$PIPELINE_COUNT" ]; then
    echo -e "${GREEN}  ✓ Todos os registros foram preservados!${NC}"
else
    echo -e "${RED}  ✗ Alguns registros podem ter sido perdidos${NC}"
fi
echo ""

echo -e "${YELLOW}[7/7] Aguardando próxima sincronização...${NC}"
echo "  O backend irá sincronizar com OpAMP em ~60 segundos"
echo "  Durante a sincronização, se o instance_id original retornar:"
echo "    - O sistema detectará pela hostname '$HOST_NAME'"
echo "    - Atualizará o instance_id de volta"
echo "    - Manterá todo o histórico intacto"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Teste concluído!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Para monitorar a próxima sincronização:${NC}"
echo "  docker logs -f opamp-backend | grep -i sync"
echo ""

echo -e "${YELLOW}Para verificar o agente:${NC}"
echo "  docker exec -it opamp-postgres psql -U opamp -d opamp -c \\"
echo "    \"SELECT instance_id, host_name, updated_at FROM agents WHERE host_name = '$HOST_NAME';\""
echo ""

echo -e "${YELLOW}Para restaurar configuração:${NC}"
echo "  mv docker-compose.yml.backup docker-compose.yml"
echo "  docker compose restart backend"
echo ""
