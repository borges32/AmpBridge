# Production Deployment Guide

This document describes best practices and steps for deploying the OpAMP Backend in production.

---

## 🔒 Security Checklist

### 1. Change Secret Key

```bash
# Generate new secret key
openssl rand -hex 32

# Edit backend/.env
SECRET_KEY=<your-generated-key-here>
```

### 2. Database Passwords

```bash
# Generate strong password
openssl rand -base64 32

# Update docker-compose.yml
POSTGRES_PASSWORD=<strong-password>

# Update backend/.env
DATABASE_URL=postgresql+asyncpg://opamp:<strong-password>@postgres:5432/opamp_db
```

### 3. Configure CORS

Edit `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-domain.com",
        "https://admin.your-domain.com"
    ],  # Specify allowed domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 4. Disable Debug Mode

In `backend/.env`:

```env
DEBUG=false
```

### 5. Configure Token Expiration

In `backend/.env` (adjust as needed):

```env
ACCESS_TOKEN_EXPIRE_MINUTES=30  # Or shorter for better security
```

---

## 🌐 Domain and HTTPS Configuration

### Option 1: Nginx Reverse Proxy

#### 1.1. Install Nginx and Certbot

```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx
```

#### 1.2. Configure Nginx

Create file `/etc/nginx/sites-available/opamp-backend`:

```nginx
# HTTP - Redirect to HTTPS
server {
    listen 80;
    server_name api.your-domain.com;
    
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
    server_name api.your-domain.com;
    
    # SSL certificates (certbot will configure)
    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;
    
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
        
        # WebSocket support (if needed in the future)
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

#### 1.3. Enable configuration

```bash
sudo ln -s /etc/nginx/sites-available/opamp-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 1.4. Obtain SSL certificate

```bash
sudo certbot --nginx -d api.your-domain.com
```

### Option 2: Traefik (Docker-based)

Add to `docker-compose.yml`:

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
      - "--certificatesresolvers.letsencrypt.acme.email=your-email@example.com"
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
    # ... existing configuration ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`api.your-domain.com`)"
      - "traefik.http.routers.backend.entrypoints=websecure"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
      # Redirect HTTP to HTTPS
      - "traefik.http.middlewares.redirect-to-https.redirectscheme.scheme=https"
      - "traefik.http.routers.backend-http.rule=Host(`api.your-domain.com`)"
      - "traefik.http.routers.backend-http.entrypoints=web"
      - "traefik.http.routers.backend-http.middlewares=redirect-to-https"
```

---

## 📦 Data Persistence

### PostgreSQL Backup

#### 1. Manual Backup

```bash
# Full backup
docker exec opamp-postgres pg_dump -U opamp opamp_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker exec opamp-postgres pg_dump -U opamp opamp_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### 2. Automated Backup (Cron)

Create script `/opt/opamp/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/opamp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Make backup
docker exec opamp-postgres pg_dump -U opamp opamp_db | gzip > $BACKUP_DIR/opamp_backup_$DATE.sql.gz

# Remove old backups
find $BACKUP_DIR -name "opamp_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Log
echo "Backup completed: opamp_backup_$DATE.sql.gz"
```

Add to crontab:

```bash
chmod +x /opt/opamp/backup.sh

# Edit crontab
crontab -e

# Add line (daily backup at 2:00 AM)
0 2 * * * /opt/opamp/backup.sh >> /var/log/opamp-backup.log 2>&1
```

#### 3. Restore

```bash
# Decompress and restore
gunzip -c backup_20251117_020000.sql.gz | docker exec -i opamp-postgres psql -U opamp -d opamp_db
```

### Persistent Volumes

Ensure volumes are configured in `docker-compose.yml`:

```yaml
services:
  postgres:
    volumes:
      - ./data/postgres:/var/lib/postgresql/data  # Persistent data
```

---

## 🔍 Monitoring

### 1. Health Checks

Configure health check monitoring:

```bash
#!/bin/bash
# /opt/opamp/healthcheck.sh

API_URL="https://api.your-domain.com/health"
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

response=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ "$response" != "200" ]; then
    # Send alert
    curl -X POST $SLACK_WEBHOOK -H 'Content-Type: application/json' \
      -d "{\"text\":\"⚠️ OpAMP Backend health check failed! HTTP $response\"}"
fi
```

Add to cron (check every 5 minutes):

```bash
*/5 * * * * /opt/opamp/healthcheck.sh
```

### 2. Centralized Logs

#### Option: Loki + Promtail + Grafana

Add to `docker-compose.yml`:

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

### 3. Metrics (Prometheus)

Add metrics endpoint to the backend:

```python
# backend/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(...)

# Add instrumentation
Instrumentator().instrument(app).expose(app)
```

Add Prometheus to `docker-compose.yml`:

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

## 🚀 Automated Deployment

### GitHub Actions (CI/CD)

Create `.github/workflows/deploy.yml`:

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
            
            # Check health
            sleep 10
            curl -f http://localhost:8000/health || exit 1
```

---

## ⚡ Performance

### 1. Database Connection Pooling

Already configured in SQLAlchemy. Adjust if needed in `backend/app/core/database.py`:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,           # Number of permanent connections
    max_overflow=20,        # Additional temporary connections
    pool_pre_ping=True,     # Check connections before using
    pool_recycle=3600,      # Recycle connections every hour
)
```

### 2. Gunicorn Workers (Production)

Create `backend/gunicorn_conf.py`:

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

Update `Dockerfile`:

```dockerfile
# ... rest of Dockerfile ...

# Install gunicorn
RUN pip install --no-cache-dir gunicorn

# CMD
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
```

### 3. Redis Cache (Optional)

To improve query performance:

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

## 📊 Server Resources

### Minimum Recommended

- **CPU**: 2 vCPUs
- **RAM**: 4 GB
- **Disk**: 20 GB SSD
- **Network**: 100 Mbps

### Recommended for Production

- **CPU**: 4 vCPUs
- **RAM**: 8 GB
- **Disk**: 50 GB SSD
- **Network**: 1 Gbps

### Docker Limits

Configure limits in `docker-compose.yml`:

```yaml
services:
  backend:
    # ... other configurations ...
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

# Block direct access to internal services
# (only via reverse proxy)
# DO NOT open 8000, 5432, 4321 publicly
```

---

## 📝 Final Checklist

- [ ] Secret key changed
- [ ] Strong passwords configured
- [ ] CORS properly configured
- [ ] Debug mode disabled
- [ ] HTTPS configured (Nginx/Traefik)
- [ ] Automated backups
- [ ] Monitoring configured
- [ ] Centralized logs
- [ ] Firewall configured
- [ ] Resource limits defined
- [ ] Production health checks
- [ ] CI/CD configured (optional)

---

## 🆘 Rollback

In case of problems:

```bash
# Stop new deployment
docker compose down backend

# Revert to previous image
docker tag local/opamp-backend:latest local/opamp-backend:rollback
docker pull local/opamp-backend:previous  # If you have a registry

# Restore database backup
gunzip -c backup_previous.sql.gz | docker exec -i opamp-postgres psql -U opamp -d opamp_db

# Start previous version
docker compose up -d backend
```

---

## 📞 Production Support

- Logs: `docker logs -f opamp-backend`
- Database: `docker exec -it opamp-postgres psql -U opamp -d opamp_db`
- Health: `curl https://api.your-domain.com/health`

---

**Good luck with the deployment! 🚀**
