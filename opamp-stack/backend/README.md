# OpAMP Backend API

A comprehensive REST API for managing OpAMP (Open Agent Management Protocol) agents and configurations, built with FastAPI, SQLAlchemy, and containerized for easy deployment.

## Features

- **Agent Management**: List, monitor, and track OpAMP agents across environments
- **Configuration Management**: Apply and track configuration changes with version control
- **Bulk Operations**: Execute configuration updates across multiple agents concurrently
- **Background Jobs**: Asynchronous job processing with real-time progress tracking
- **Authentication & Authorization**: JWT-based auth with role-based access control (RBAC)
- **Real-time Updates**: Server-Sent Events (SSE) for live job progress monitoring
- **Monitoring**: Prometheus metrics and optional OpenTelemetry tracing
- **Audit Logging**: Complete audit trail for all configuration changes
- **Database Support**: SQLite (default) and PostgreSQL support
- **Container Ready**: Docker and docker-compose deployment

## Architecture

```
app/
├── main.py                 # FastAPI application entry point
├── settings.py            # Environment configuration
├── api/v1/               # REST API endpoints
│   ├── auth.py           # Authentication endpoints
│   ├── agents.py         # Agent management
│   ├── configs.py        # Configuration management
│   ├── jobs.py           # Job management
│   └── deps.py           # Dependency injection
├── clients/
│   └── opamp.py          # OpAMP server client
├── core/
│   ├── services/         # Business logic services
│   └── utils/            # Utility functions
├── db/
│   ├── models.py         # SQLAlchemy models
│   ├── session.py        # Database session management
│   └── migrations/       # Alembic migrations
├── jobs/
│   ├── runner.py         # Background job processor
│   └── sse.py            # Server-Sent Events
├── security/
│   ├── auth.py           # JWT authentication
│   ├── password.py       # Password hashing (Argon2)
│   └── rbac.py           # Role-based access control
└── telemetry/
    ├── metrics.py        # Prometheus metrics
    └── tracing.py        # OpenTelemetry tracing
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- An OpAMP server running and accessible

### 1. Clone and Setup

```bash
git clone <repository-url>
cd AmpBridge/opamp-stack/backend
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Application
APP_ENV=dev
LOG_LEVEL=INFO

# Database (SQLite by default)
DB_URL=sqlite:///data/app.db
# For PostgreSQL: DB_URL=postgresql://user:password@postgres:5432/opamp

# Admin credentials
ADMIN_USER=admin
ADMIN_PASS=admin123

# JWT configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production-minimum-32-chars
JWT_EXPIRES_MIN=1440

# OpAMP server
OPAMP_BASE_URL=http://opamp-server:4321

# Security
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT_PER_MIN=100

# Optional: OpenTelemetry
OTLP_ENDPOINT=
OTLP_HEADERS=
```

### 3. Run with Docker Compose

```bash
# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f opamp-backend
```

The API will be available at:
- **API**: http://localhost:8080
- **Documentation**: http://localhost:8080/docs
- **Metrics**: http://localhost:8080/metrics

### 4. First Login

```bash
# Get JWT token
curl -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

## Development Setup

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Setup database
alembic upgrade head

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_agents.py -v
```

## API Usage

### Authentication

All protected endpoints require a JWT token in the Authorization header:

```bash
# Login to get token
TOKEN=$(curl -s -X POST "http://localhost:8080/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r .access_token)

# Use token in subsequent requests
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/agents"
```

### Key Endpoints

#### Agents
- `GET /api/v1/agents` - List agents with filtering
- `GET /api/v1/agents/{id}` - Get agent details
- `GET /api/v1/agents/{id}/config` - Get agent configuration

#### Configurations
- `POST /api/v1/agents/{id}/config` - Apply configuration to agent
- `POST /api/v1/configs/bulk` - Bulk configuration update
- `GET /api/v1/configs/{id}/compare/{other_id}` - Compare configurations

#### Jobs
- `GET /api/v1/jobs` - List jobs
- `GET /api/v1/jobs/{id}` - Get job details
- `GET /api/v1/jobs/{id}/stream` - SSE stream for job progress

### Bulk Configuration Update

```bash
curl -X POST "http://localhost:8080/api/v1/configs/bulk" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_ids": ["agent1", "agent2", "agent3"],
    "config_yaml": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317"
  }'
```

### Real-time Job Progress

```bash
# Stream job progress via SSE
curl -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/jobs/{job_id}/stream"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `dev` | Application environment |
| `DB_URL` | `sqlite:///data/app.db` | Database connection URL |
| `ADMIN_USER` | `admin` | Bootstrap admin username |
| `ADMIN_PASS` | `admin123` | Bootstrap admin password |
| `JWT_SECRET` | `(required)` | JWT signing secret |
| `JWT_EXPIRES_MIN` | `1440` | JWT expiration in minutes |
| `OPAMP_BASE_URL` | `http://opamp-server:4321` | OpAMP server URL |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `RATE_LIMIT_PER_MIN` | `100` | Rate limit per IP per minute |
| `MAX_CONCURRENT_JOBS` | `50` | Max concurrent job executions |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OTLP_ENDPOINT` | `(optional)` | OpenTelemetry OTLP endpoint |

### Database Support

#### SQLite (Default)
- Perfect for development and small deployments
- Automatic WAL mode for better concurrency
- Data stored in `/data/app.db`

#### PostgreSQL
Set `DB_URL=postgresql://user:password@host:port/database`

### OpAMP Server Integration

The API expects your OpAMP server to expose these endpoints:
- `GET /api/agents` - List agents
- `GET /api/agents/{id}` - Get agent details
- `POST /api/agents/{id}/config` - Apply configuration

## Monitoring

### Prometheus Metrics

Available at `http://localhost:8080/metrics`:

- `opamp_agents_total` - Total number of agents by environment and status
- `opamp_config_apply_total` - Configuration applications by status
- `opamp_job_total` - Jobs by type and status
- `opamp_job_duration_seconds` - Job execution duration
- `http_requests_total` - HTTP request count by endpoint and status
- `auth_attempts_total` - Authentication attempts by status

### OpenTelemetry Tracing

Optional distributed tracing support:

```bash
# Enable tracing
OTLP_ENDPOINT=http://jaeger:4317
OTLP_HEADERS=authorization=Bearer token123
```

### Health Checks

- `GET /healthz` - Basic health check
- `GET /readyz` - Readiness check (includes database connectivity)

## Security

### Authentication
- JWT tokens with configurable expiration
- Argon2id password hashing
- Rate limiting on sensitive endpoints

### Authorization (RBAC)
- **Admin**: Full access to all operations
- **Viewer**: Read-only access to agents, configs, and jobs

### Audit Logging
All configuration changes are logged with:
- Timestamp and actor
- Target agent/configuration
- Change details in JSON format
- IP address tracking

## Production Deployment

### Docker Compose (Recommended)

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  opamp-backend:
    image: opamp-backend:latest
    restart: always
    environment:
      - APP_ENV=prod
      - DB_URL=postgresql://opamp:secure_password@postgres:5432/opamp
      - JWT_SECRET=very-secure-random-key-at-least-32-characters
      - ADMIN_PASS=secure_admin_password
    volumes:
      - ./data:/app/data
    ports:
      - "8080:8080"
```

### Production Checklist

- [ ] Change default admin password
- [ ] Use strong JWT secret (32+ characters)
- [ ] Configure PostgreSQL for production
- [ ] Set up SSL/TLS termination (nginx/traefik)
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerting
- [ ] Regular database backups
- [ ] Resource limits and scaling

### Scaling Considerations

- **Database**: Use PostgreSQL with connection pooling
- **Jobs**: Scale horizontally by running multiple backend instances
- **Monitoring**: Consider Prometheus federation for metrics
- **Load Balancing**: Use nginx or cloud load balancer

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database URL and connectivity
   docker compose logs opamp-backend
   ```

2. **OpAMP Server Unreachable**
   ```bash
   # Test OpAMP server connectivity
   curl http://opamp-server:4321/api/agents
   ```

3. **Job Stuck in Pending**
   ```bash
   # Check job runner status and logs
   docker compose exec opamp-backend python -c "from app.jobs.runner import job_runner; print(job_runner.active_jobs)"
   ```

4. **Permission Denied**
   - Ensure user has correct role in database
   - Check JWT token validity and claims

### Debugging

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
```

Access application logs:
```bash
docker compose logs -f opamp-backend
```

Database console:
```bash
# SQLite
docker compose exec opamp-backend sqlite3 /app/data/app.db

# PostgreSQL
docker compose exec postgres psql -U opamp -d opamp
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Commit changes: `git commit -m "Add amazing feature"`
6. Push to branch: `git push origin feature/amazing-feature`
7. Create Pull Request

### Code Standards

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions and classes
- Add tests for new features
- Update documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Include logs and configuration (sanitized)

---

**Security Note**: Always change default passwords and use strong secrets in production deployments.