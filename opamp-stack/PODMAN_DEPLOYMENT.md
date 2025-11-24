# Guia de Deployment com Podman no Red Hat Enterprise Linux

## Visão Geral

Este guia explica como executar o OpAMP Stack usando **Podman** em sistemas **Red Hat Enterprise Linux (RHEL)** 8/9 ou compatíveis (CentOS Stream, Fedora, Rocky Linux, AlmaLinux).

## Por que Podman?

- ✅ **Rootless por padrão** - Maior segurança
- ✅ **Sem daemon** - Arquitetura fork-exec mais segura
- ✅ **Compatível com Docker** - Mesma sintaxe de comandos
- ✅ **SELinux nativo** - Integração total com RHEL
- ✅ **Suportado oficialmente** pela Red Hat

## Pré-requisitos

### Sistema Operacional
- Red Hat Enterprise Linux 8.x ou 9.x
- CentOS Stream 8/9
- Fedora 35+
- Rocky Linux 8/9
- AlmaLinux 8/9

### Software Necessário
```bash
# Instalar Podman e ferramentas
sudo dnf install -y podman podman-compose python3-pip

# Alternativa: Instalar podman-compose via pip
pip3 install --user podman-compose
```

## Diferenças entre docker-compose.yml e podman-compose.yml

### 1. **Remoção de builds**
```yaml
# docker-compose.yml
build:
  context: ./backend

# podman-compose.yml  
# (removido - usa imagens pré-construídas)
```

### 2. **Volumes com SELinux**
```yaml
# docker-compose.yml
volumes:
  - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro

# podman-compose.yml
volumes:
  - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro,Z
```
- `:Z` - Relabel privado para o container (recomendado)
- `:z` - Relabel compartilhado entre containers

### 3. **User namespaces**
```yaml
# Adicionado em todos os serviços
userns_mode: keep-id
security_opt:
  - label=disable
```

### 4. **Compatibilidade de comandos**
```bash
# Docker
docker-compose up -d

# Podman
podman-compose -f podman-compose.yml up -d
```

## Instalação e Setup

### Passo 1: Instalar Podman

```bash
# RHEL/CentOS/Rocky/AlmaLinux
sudo dnf install -y podman podman-compose

# Verificar instalação
podman --version
podman-compose --version
```

### Passo 2: Configurar ambiente rootless (Recomendado)

```bash
# Configurar subordinate UIDs/GIDs
sudo usermod --add-subuids 100000-165535 $USER
sudo usermod --add-subgids 100000-165535 $USER

# Habilitar linger (manter serviços rodando)
loginctl enable-linger $USER

# Relogar para aplicar mudanças
```

### Passo 3: Executar script de setup

```bash
# Tornar executável
chmod +x setup-podman.sh

# Executar
./setup-podman.sh
```

O script irá:
- ✅ Verificar instalação do Podman
- ✅ Verificar SELinux
- ✅ Configurar user namespaces
- ✅ Criar rede Podman
- ✅ Verificar imagens necessárias
- ✅ Verificar firewall

## Obtendo as Imagens

### Opção 1: Construir com Podman

```bash
# OpAMP Server
cd opamp-server
podman build -t local/opamp-server:latest .

# Backend
cd ../backend
podman build -t local/opamp-backend:latest .

# Frontend
cd ../frontend
podman build -t local/opamp-frontend:latest .
```

### Opção 2: Migrar do Docker

Se você já tem as imagens no Docker:

```bash
# Salvar do Docker e carregar no Podman
docker save local/opamp-server:latest | podman load
docker save local/opamp-backend:latest | podman load
docker save local/opamp-frontend:latest | podman load
```

### Opção 3: Registry Privado

```bash
# Login no registry
podman login registry.example.com

# Pull das imagens
podman pull registry.example.com/opamp-server:latest
podman tag registry.example.com/opamp-server:latest local/opamp-server:latest

podman pull registry.example.com/opamp-backend:latest
podman tag registry.example.com/opamp-backend:latest local/opamp-backend:latest

podman pull registry.example.com/opamp-frontend:latest
podman tag registry.example.com/opamp-frontend:latest local/opamp-frontend:latest
```

## Executando o Stack

### Iniciar todos os serviços

```bash
podman-compose -f podman-compose.yml up -d
```

### Verificar status

```bash
# Status dos containers
podman-compose -f podman-compose.yml ps

# Logs de todos os serviços
podman-compose -f podman-compose.yml logs -f

# Logs de um serviço específico
podman-compose -f podman-compose.yml logs -f backend
```

### Parar o stack

```bash
# Parar containers (mantém volumes)
podman-compose -f podman-compose.yml down

# Parar e remover volumes
podman-compose -f podman-compose.yml down -v
```

### Reiniciar um serviço

```bash
podman-compose -f podman-compose.yml restart backend
```

## Configuração do Firewall

Se o firewalld estiver ativo, abra as portas necessárias:

```bash
# Abrir portas
sudo firewall-cmd --permanent --add-port=3000/tcp   # Frontend
sudo firewall-cmd --permanent --add-port=4320/tcp   # HAProxy
sudo firewall-cmd --permanent --add-port=4321/tcp   # OpAMP Server
sudo firewall-cmd --permanent --add-port=5432/tcp   # PostgreSQL
sudo firewall-cmd --permanent --add-port=8000/tcp   # Backend API

# Recarregar firewall
sudo firewall-cmd --reload

# Verificar portas abertas
sudo firewall-cmd --list-ports
```

## Troubleshooting

### Problema: "permission denied" em volumes

**Solução:** Verificar contexto SELinux

```bash
# Verificar contexto
ls -Z haproxy.cfg

# Reconfigurar contexto se necessário
chcon -Rt svirt_sandbox_file_t haproxy.cfg
```

### Problema: Containers não conseguem se comunicar

**Solução:** Verificar rede Podman

```bash
# Listar redes
podman network ls

# Inspecionar rede
podman network inspect opamp-network

# Recriar rede se necessário
podman network rm opamp-network
podman network create opamp-network
```

### Problema: "image not found"

**Solução:** Verificar imagens disponíveis

```bash
# Listar imagens
podman images

# Verificar se a imagem existe
podman image exists local/opamp-backend:latest
echo $?  # 0 = existe, 1 = não existe
```

### Problema: Healthcheck falha

**Solução:** Verificar logs e aumentar timeout

```bash
# Ver logs
podman logs opamp-backend

# Entrar no container para debug
podman exec -it opamp-backend /bin/bash

# Testar healthcheck manualmente
podman exec opamp-backend curl -f http://localhost:8000/health
```

### Problema: SELinux bloqueando acesso

**Solução:** Adicionar flags corretas nos volumes

```yaml
volumes:
  - ./data:/app/data:Z    # Privado
  - ./config:/app/config:z # Compartilhado
```

## Comandos Úteis

### Gerenciamento de Containers

```bash
# Listar todos os containers
podman ps -a

# Parar container
podman stop opamp-backend

# Remover container
podman rm opamp-backend

# Logs em tempo real
podman logs -f opamp-backend

# Executar comando no container
podman exec -it opamp-backend /bin/bash

# Inspecionar container
podman inspect opamp-backend
```

### Gerenciamento de Volumes

```bash
# Listar volumes
podman volume ls

# Inspecionar volume
podman volume inspect postgres_data

# Remover volume não utilizado
podman volume prune

# Backup de volume
podman run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

### Gerenciamento de Imagens

```bash
# Listar imagens
podman images

# Remover imagem
podman rmi local/opamp-backend:latest

# Remover imagens não utilizadas
podman image prune

# Inspecionar imagem
podman inspect local/opamp-backend:latest
```

### Gerenciamento de Redes

```bash
# Listar redes
podman network ls

# Criar rede
podman network create opamp-network

# Remover rede
podman network rm opamp-network

# Inspecionar rede
podman network inspect opamp-network
```

## Systemd Integration (Opcional)

Para executar como serviço systemd:

### 1. Gerar arquivo de serviço

```bash
cd /home/alexandre/Documentos/github/AmpBridge/opamp-stack
podman generate systemd --new --name opamp-backend > ~/.config/systemd/user/opamp-backend.service
```

### 2. Habilitar e iniciar

```bash
systemctl --user enable opamp-backend.service
systemctl --user start opamp-backend.service
systemctl --user status opamp-backend.service
```

### 3. Logs

```bash
journalctl --user -u opamp-backend.service -f
```

## Monitoramento

### Estatísticas de recursos

```bash
# CPU e memória de todos os containers
podman stats

# Específico
podman stats opamp-backend

# Uma vez só (não contínuo)
podman stats --no-stream
```

### Healthchecks

```bash
# Verificar health de todos os containers
podman ps --filter health=healthy
podman ps --filter health=unhealthy

# Inspecionar healthcheck
podman inspect --format='{{.State.Health.Status}}' opamp-backend
```

## URLs de Acesso

Após iniciar o stack:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Backend Docs**: http://localhost:8000/docs
- **OpAMP Server UI**: http://localhost:4321
- **HAProxy**: http://localhost:4320
- **PostgreSQL**: localhost:5432

## Segurança

### Rootless vs Rootful

**Rootless (Recomendado)**:
```bash
# Como usuário normal
podman-compose -f podman-compose.yml up -d
```

**Rootful** (se necessário):
```bash
# Como root
sudo podman-compose -f podman-compose.yml up -d
```

### SELinux

Mantenha SELinux em modo **Enforcing** para máxima segurança:

```bash
# Verificar status
getenforce

# Nunca desabilite SELinux em produção!
# Use as flags :Z e :z nos volumes para compatibilidade
```

## Backup e Restore

### Backup do PostgreSQL

```bash
# Backup do banco
podman exec opamp-postgres pg_dump -U opamp opamp_db > backup.sql

# Backup com podman volume
podman run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

### Restore do PostgreSQL

```bash
# Restore do banco
cat backup.sql | podman exec -i opamp-postgres psql -U opamp opamp_db

# Restore do volume
podman run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

## Performance Tips

1. **Use volumes nomeados** ao invés de bind mounts quando possível
2. **Configure limits** de CPU e memória se necessário:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```
3. **Use overlayfs** para melhor performance (padrão no Podman)
4. **Ajuste healthcheck intervals** conforme necessidade

## Referências

- [Documentação Oficial Podman](https://docs.podman.io/)
- [Podman Compose](https://github.com/containers/podman-compose)
- [RHEL Container Tools](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/building_running_and_managing_containers/)
- [Migração Docker → Podman](https://podman.io/getting-started/migration)
