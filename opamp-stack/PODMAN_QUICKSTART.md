# 🚀 Quick Start - Podman Deployment

## Para Red Hat Enterprise Linux / CentOS Stream / Fedora / Rocky / AlmaLinux

### 📋 Pré-requisitos

```bash
# Instalar Podman
sudo dnf install -y podman podman-compose python3-pip
```

### 🔧 Setup Rápido

```bash
# 1. Executar script de setup
./setup-podman.sh

# 2. Migrar imagens do Docker (se já tiver)
./migrate-docker-to-podman.sh

# OU construir com Podman
podman build -t local/opamp-server:latest opamp-server/
podman build -t local/opamp-backend:latest backend/
podman build -t local/opamp-frontend:latest frontend/
```

### ▶️ Iniciar Stack

```bash
# Iniciar todos os serviços
podman-compose -f podman-compose.yml up -d

# Ver logs
podman-compose -f podman-compose.yml logs -f

# Ver status
podman-compose -f podman-compose.yml ps
```

### 🌐 Acessar Aplicação

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs
- **OpAMP Server**: http://localhost:4321

### 🛑 Parar Stack

```bash
# Parar (mantém volumes)
podman-compose -f podman-compose.yml down

# Parar e remover volumes
podman-compose -f podman-compose.yml down -v
```

### 🔥 Firewall (se necessário)

```bash
sudo firewall-cmd --permanent --add-port={3000,4320,4321,5432,8000}/tcp
sudo firewall-cmd --reload
```

### 📚 Documentação Completa

Ver **PODMAN_DEPLOYMENT.md** para:
- Troubleshooting detalhado
- Integração com systemd
- Backup e restore
- Performance tuning
- Comandos úteis

### 🔑 Principais Diferenças do Docker

1. **Volumes com SELinux**: Usar `:Z` ou `:z`
   ```yaml
   volumes:
     - ./data:/app/data:Z
   ```

2. **User namespaces**: Configurado automaticamente
   ```yaml
   userns_mode: keep-id
   ```

3. **Rootless**: Executa sem root por padrão (mais seguro)

4. **Comandos**: `podman-compose` ao invés de `docker-compose`

### ✅ Verificar Instalação

```bash
# Versões
podman --version
podman-compose --version

# Imagens disponíveis
podman images

# Containers rodando
podman ps

# Redes
podman network ls
```

### 🆘 Ajuda Rápida

```bash
# Ver logs de um serviço
podman logs -f opamp-backend

# Reiniciar um serviço
podman restart opamp-backend

# Entrar no container
podman exec -it opamp-backend /bin/bash

# Ver recursos (CPU/RAM)
podman stats
```

### 📞 Suporte

Para problemas comuns, consulte a seção **Troubleshooting** em `PODMAN_DEPLOYMENT.md`
