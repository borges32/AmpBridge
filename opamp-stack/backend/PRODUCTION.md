# Guia de Deploy em Produção

Este documento descreve as melhores práticas e passos para deploy do OpAMP Backend em produção.

---

## 🔒 Checklist de Segurança

### 1. Alterar Secret Key

```bash
# Gerar nova secret key
openssl rand -hex 32

# Editar backend/.env
SECRET_KEY=<sua-chave-gerada-aqui>
```

### 2. Senhas do Database

```bash
# Gerar senha forte
openssl rand -base64 32

# Atualizar docker-compose.yml
POSTGRES_PASSWORD=<senha-forte>

# Atualizar backend/.env
DATABASE_URL=postgresql+asyncpg://opamp:<senha-forte>@postgres:5432/opamp_db
```

### 3. Configurar CORS

Edite `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seu-dominio.com",
        "https://admin.seu-dominio.com"
    ],  # Especificar domínios permitidos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 4. Desabilitar Debug Mode

Em `backend/.env`:

```env
DEBUG=false
```

### 5. Configurar Token Expiration

Em `backend/.env` (ajustar conforme necessidade):

```env
ACCESS_TOKEN_EXPIRE_MINUTES=30  # Ou mais curto para maior segurança
```

---

## 🌐 Configuração de Domínio e HTTPS

### Opção 1: Nginx Reverse Proxy

#### 1.1. Instalar Nginx e Certbot

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

#### 1.2. Configurar Nginx

Criar arquivo `/etc/nginx/sites-available/opamp-backend`:

```nginx
# HTTP - Redirecionar para HTTPS
server {
    listen 80;
    server_name api.seu-dominio.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name api.seu-dominio.com;
    
    # SSL certificates (certbot irá configurar)
    ssl_certificate /etc/letsencrypt/live/api.seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.seu-dominio.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logs
    access_log /var/log/nginx/opamp-backend-access.log;
    error_log /var/log/nginx/opamp-backend-error.log;
    
    # Proxy settings
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # WebSocket support (se necessário no futuro)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 1.3. Ativar configuração

```bash
sudo ln -s /etc/nginx/sites-available/opamp-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 1.4. Obter certificado SSL

```bash
sudo certbot --nginx -d api.seu-dominio.com
```

### Opção 2: Traefik (Docker-based)

Adicionar ao `docker-compose.yml`:

```yaml
services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=seu-email@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
    networks:
      - opamp-network

  backend:
    # ... configuração existente ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.seu-dominio.com`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
      # Redirect HTTP to HTTPS
      - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
      - "traefik.http.routers.backend-http.rule=Host(`api.seu-dominio.com`)"
      - "traefik.http.routers.backend-http.entrypoints=web"
      - "traefik.http.routers.backend-http.middlewares=redirect-to-https"
```

---

## 📦 Persistência de Dados

### Backup do PostgreSQL

#### 1. Backup Manual

```bash
# Backup completo
docker exec opamp-postgres pg_dump -U opamp opamp_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup comprimido
docker exec opamp-postgres pg_dump -U opamp opamp_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### 2. Backup Automatizado (Cron)

Criar script `/opt/opamp/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/opamp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Criar diretório se não existe
mkdir -p $BACKUP_DIR

# Fazer backup
docker exec opamp-postgres pg_dump -U opamp opamp_db | gzip > $BACKUP_DIR/opamp_backup_$DATE.sql.gz

# Remover backups antigos
find $BACKUP_DIR -name "opamp_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Log
echo "Backup completed: opamp_backup_$DATE.sql.gz"
```

Adicionar ao crontab:

```bash
chmod +x /opt/opamp/backup.sh

# Editar crontab
crontab -e

# Adicionar linha (backup diário às 2:00 AM)
0 2 * * * /opt/opamp/backup.sh >> /var/log/opamp-backup.log 2>&1
```

#### 3. Restore

```bash
# Descompactar e restaurar
gunzip -c backup_20251117_020000.sql.gz | docker exec -i opamp-postgres psql -U opamp -d opamp_db
```

### Volumes Persistentes

Garantir que volumes estejam configurados no `docker-compose.yml`:

```yaml
services:
  postgres:
    volumes:
      - ./data/postgres:/var/lib/postgresql/data  # Dados persistentes
```

---

## 🔍 Monitoramento

### 1. Health Checks

Configurar monitoramento de health checks:

```bash
#!/bin/bash
# /opt/opamp/healthcheck.sh

API_URL="https://api.seu-dominio.com/health"
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ "$response" != "200" ]; then
    # Enviar alerta
    curl -X POST $SLACK_WEBHOOK -H 'Content-Type: application/json' \
      -d "{\"text\":\"⚠️ OpAMP Backend health check failed! HTTP $response\"}"
fi
```

Adicionar ao cron (verificar a cada 5 minutos):

```bash
*/5 * * * * /opt/opamp/healthcheck.sh
```

### 2. Logs Centralizados

#### Opção: Loki + Promtail + Grafana

Adicionar ao `docker-compose.yml`:

```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - opamp-network

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - opamp-network

  grafana:
    image: grafana/grafana:10.0.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - opamp-network

volumes:
  grafana-data:
```

### 3. Métricas (Prometheus)

Adicionar endpoint de métricas no backend:

```python
# backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

# Adicionar instrumentação
Instrumentator().instrument(app).expose(app)
```

Adicionar Prometheus ao `docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - "9090:9090"
    networks:
      - opamp-network

volumes:
  prometheus-data:
```

---

## 🚀 Deploy Automatizado

### GitHub Actions (CI/CD)

Criar `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main
    paths:
      - 'opamp-stack/backend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/opamp/opamp-stack
            git pull origin main
            docker compose down backend
            docker compose build --no-cache backend
            docker compose up -d backend
            docker exec opamp-backend alembic upgrade head
            
            # Verificar health
            sleep 10
            curl -f http://localhost:8000/health || exit 1
```

---

## ⚡ Performance

### 1. Database Connection Pooling

Já configurado no SQLAlchemy. Ajustar se necessário em `backend/app/core/database.py`:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,           # Número de conexões permanentes
    max_overflow=20,        # Conexões adicionais temporárias
    pool_pre_ping=True,     # Verificar conexões antes de usar
    pool_recycle=3600,      # Reciclar conexões a cada hora
)
```

### 2. Gunicorn Workers (Produção)

Criar `backend/gunicorn_conf.py`:

```python
import multiprocessing

# Bind
bind = "0.0.0.0:8000"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "opamp-backend"
```

Atualizar `Dockerfile`:

```dockerfile
# ... resto do Dockerfile ...

# Instalar gunicorn
RUN pip install --no-cache-dir gunicorn

# CMD
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
```

### 3. Redis Cache (Opcional)

Para melhorar performance de queries:

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes
    networks:
      - opamp-network
```

---

## 📊 Recursos do Servidor

### Mínimo Recomendado

- **CPU**: 2 vCPUs
- **RAM**: 4 GB
- **Disco**: 20 GB SSD
- **Rede**: 100 Mbps

### Recomendado para Produção

- **CPU**: 4 vCPUs
- **RAM**: 8 GB
- **Disco**: 50 GB SSD
- **Rede**: 1 Gbps

### Limites Docker

Configurar limites em `docker-compose.yml`:

```yaml
services:
  backend:
    # ... outras configurações ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## 🔥 Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp       # SSH
sudo ufw allow 80/tcp       # HTTP
sudo ufw allow 443/tcp      # HTTPS
sudo ufw enable

# Bloquear acesso direto a serviços internos
# (apenas via reverse proxy)
# NÃO abrir 8000, 5432, 4321 publicamente
```

---

## 📝 Checklist Final

- [ ] Secret key alterada
- [ ] Senhas fortes configuradas
- [ ] CORS configurado corretamente
- [ ] Debug mode desabilitado
- [ ] HTTPS configurado (Nginx/Traefik)
- [ ] Backups automatizados
- [ ] Monitoramento configurado
- [ ] Logs centralizados
- [ ] Firewall configurado
- [ ] Limites de recursos definidos
- [ ] Health checks em produção
- [ ] CI/CD configurado (opcional)

---

## 🆘 Rollback

Em caso de problemas:

```bash
# Parar novo deploy
docker compose down backend

# Voltar para imagem anterior
docker tag local/opamp-backend:latest local/opamp-backend:rollback
docker pull local/opamp-backend:previous  # Se tiver registry

# Restaurar backup de database
gunzip -c backup_anterior.sql.gz | docker exec -i opamp-postgres psql -U opamp -d opamp_db

# Subir versão anterior
docker compose up -d backend
```

---

## 📞 Suporte em Produção

- Logs: `docker logs -f opamp-backend`
- Database: `docker exec -it opamp-postgres psql -U opamp -d opamp_db`
- Health: `curl https://api.seu-dominio.com/health`

---

**Boa sorte com o deploy! 🚀**
