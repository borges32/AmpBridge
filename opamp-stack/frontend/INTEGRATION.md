# Frontend ↔ Backend Integration Guide

## 🔗 API Contract

This document describes how the frontend integrates with the OpAMP backend API.

## Base Configuration

### Environment Variables

**Frontend `.env`:**
```env
VITE_API_URL=http://localhost:8000
```

**Production `.env`:**
```env
VITE_API_URL=https://api.yourdomain.com
```

### Axios Client Configuration

Location: `src/services/api.ts`

```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// All requests go to: ${API_BASE_URL}/api/...
```

## Authentication Flow

### 1. Login
**Frontend Request:**
```http
POST /api/auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin
```

**Backend Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Frontend Action:**
```typescript
localStorage.setItem('access_token', response.access_token);
// Navigate to /agents
```

### 2. Get Current User
**Frontend Request:**
```http
GET /api/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Backend Response:**
```json
{
  "username": "admin",
  "email": "admin@example.com"
}
```

### 3. Token Handling

**Request Interceptor:**
```typescript
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

**Response Interceptor:**
```typescript
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## Agent Management APIs

### Get Agents (Paginated & Filtered)

**Frontend Request:**
```http
GET /api/agents?page=1&size=10&os_type=Linux&connected=true&search=web
Authorization: Bearer <token>
```

**Query Parameters:**
- `page`: integer (default: 1)
- `size`: integer (default: 10)
- `os_type`: string (optional)
- `connected`: boolean (optional)
- `healthy`: boolean (optional)
- `search`: string (optional) - searches hostname and instance_id

**Backend Response:**
```json
{
  "items": [
    {
      "id": 1,
      "instance_id": "01234567-89ab-cdef-0123-456789abcdef",
      "hostname": "web-server-01",
      "os_type": "Linux",
      "os_version": "5.15.0-58-generic",
      "connected": true,
      "last_seen": "2024-01-15T14:30:22.123456",
      "created_at": "2024-01-10T10:00:00",
      "updated_at": "2024-01-15T14:30:22"
    }
  ],
  "total": 142,
  "page": 1,
  "size": 10,
  "pages": 15
}
```

**Frontend Usage:**
```typescript
const { data } = useQuery({
  queryKey: ['agents', filters],
  queryFn: () => agentService.getAgents(filters)
});

// data.items = Agent[]
// data.total = total count
```

### Get Agent Statistics

**Frontend Request:**
```http
GET /api/agents/stats
Authorization: Bearer <token>
```

**Backend Response:**
```json
{
  "total_agents": 142,
  "connected_agents": 128,
  "disconnected_agents": 14,
  "healthy_agents": 135,
  "unhealthy_agents": 7,
  "os_distribution": {
    "Linux": 95,
    "Windows": 42,
    "Darwin": 5
  }
}
```

**Frontend Usage:**
```typescript
const { data: stats } = useQuery({
  queryKey: ['agentStats'],
  queryFn: () => agentService.getAgentStats(),
  refetchInterval: 30000 // Refresh every 30s
});
```

### Get Agent Details

**Frontend Request:**
```http
GET /api/agents/01234567-89ab-cdef-0123-456789abcdef
Authorization: Bearer <token>
```

**Backend Response:**
```json
{
  "id": 1,
  "instance_id": "01234567-89ab-cdef-0123-456789abcdef",
  "hostname": "web-server-01",
  "os_type": "Linux",
  "os_version": "5.15.0-58-generic",
  "connected": true,
  "last_seen": "2024-01-15T14:30:22",
  "created_at": "2024-01-10T10:00:00",
  "updated_at": "2024-01-15T14:30:22",
  "health": {
    "id": 1,
    "agent_id": 1,
    "healthy": true,
    "last_error": null,
    "up": true,
    "created_at": "2024-01-15T14:30:22",
    "updated_at": "2024-01-15T14:30:22"
  },
  "current_config": {
    "id": 5,
    "agent_id": 1,
    "version": 5,
    "config_yaml": "receivers:\n  otlp:\n    ...",
    "config_hash": "sha256:abcdef123456...",
    "source": "MANUAL_UPDATE",
    "created_by": "admin",
    "created_at": "2024-01-15T14:00:00"
  },
  "agent_description": {
    "identifying_attributes": [
      {"key": "service.name", "value": "my-service"},
      {"key": "service.version", "value": "1.0.0"}
    ],
    "non_identifying_attributes": [
      {"key": "host.arch", "value": "amd64"}
    ]
  }
}
```

## Configuration Management

### Get Current Config

**Frontend Request:**
```http
GET /api/agents/01234567-89ab-cdef-0123-456789abcdef/config
Authorization: Bearer <token>
```

**Backend Response:**
```json
{
  "config_yaml": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317\n..."
}
```

**Frontend Usage:**
```typescript
const { data: configYaml } = useQuery({
  queryKey: ['agentConfig', instanceId],
  queryFn: () => agentService.getCurrentConfig(instanceId)
});

// Display in Monaco Editor
<Editor value={configYaml} language="yaml" />
```

### Save Config

**Frontend Request:**
```http
POST /api/agents/01234567-89ab-cdef-0123-456789abcdef/config
Authorization: Bearer <token>
Content-Type: application/json

{
  "config_yaml": "receivers:\n  otlp:\n    protocols:\n      grpc:\n        endpoint: 0.0.0.0:4317\n..."
}
```

**Backend Response:**
```json
{
  "message": "Config saved successfully"
}
```

**Backend Actions:**
1. Validates YAML
2. Calculates hash
3. Creates new version in database
4. Sends config to agent via OpAMP
5. Returns success

**Frontend Usage:**
```typescript
const mutation = useMutation({
  mutationFn: (yaml: string) => 
    agentService.saveConfig(instanceId, { config_yaml: yaml }),
  onSuccess: () => {
    message.success('Configuration saved!');
    queryClient.invalidateQueries(['agentConfig']);
  }
});
```

### Download Config

**Frontend Request:**
```http
GET /api/agents/01234567-89ab-cdef-0123-456789abcdef/config/download
Authorization: Bearer <token>
```

**Backend Response:**
```
Content-Type: application/x-yaml
Content-Disposition: attachment; filename="web-server-01_config.yaml"

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
...
```

**Frontend Usage:**
```typescript
const blob = await agentService.downloadConfig(instanceId);
const url = window.URL.createObjectURL(blob);
const link = document.createElement('a');
link.href = url;
link.download = `${hostname}_config.yaml`;
link.click();
```

### Get Config History

**Frontend Request:**
```http
GET /api/agents/01234567-89ab-cdef-0123-456789abcdef/config/history
Authorization: Bearer <token>
```

**Backend Response:**
```json
[
  {
    "id": 5,
    "agent_id": 1,
    "version": 5,
    "config_hash": "sha256:abcdef123456...",
    "config_yaml": "receivers:\n  otlp:\n...",
    "source": "MANUAL_UPDATE",
    "created_by": "admin",
    "created_at": "2024-01-15T14:00:00"
  },
  {
    "id": 4,
    "agent_id": 1,
    "version": 4,
    "config_hash": "sha256:fedcba654321...",
    "config_yaml": "receivers:\n  otlp:\n...",
    "source": "SYNC_JOB",
    "created_by": null,
    "created_at": "2024-01-15T10:00:00"
  }
]
```

**Sorted:** Newest first (descending created_at)

### Restore Config Version

**Frontend Request:**
```http
POST /api/agents/01234567-89ab-cdef-0123-456789abcdef/config/restore
Authorization: Bearer <token>
Content-Type: application/json

{
  "version": 3
}
```

**Backend Response:**
```json
{
  "message": "Config restored successfully",
  "new_version": 6
}
```

**Backend Actions:**
1. Finds version 3 config
2. Creates new version (e.g., v6) with v3 content
3. Sets source to "RESTORE"
4. Sends config to agent
5. Returns new version number

## Health Monitoring

### Get Agent Health History

**Frontend Request:**
```http
GET /api/v1/agents/01234567-89ab-cdef-0123-456789abcdef/health?limit=100
Authorization: Bearer <token>
```

**Backend Response:**
```json
[
  {
    "id": 123,
    "instance_id": "01234567-89ab-cdef-0123-456789abcdef",
    "healthy": true,
    "status": "StatusOK",
    "status_time_unix_nano": 1705324222000000000,
    "last_error": null,
    "component_health_summary": null,
    "up": true,
    "created_at": "2024-01-15T14:30:22"
  },
  // ... more records
]
```

**Frontend Usage:**
```typescript
const { data: healthRecords } = useQuery({
  queryKey: ['agentHealth', instanceId],
  queryFn: () => agentService.getAgentHealth(instanceId, 100),
  refetchInterval: 30000,
});
```

### Get Pipeline/Component Health

**NEW - Monitor individual OpenTelemetry Collector components**

**Frontend Request:**
```http
GET /api/v1/agents/01234567-89ab-cdef-0123-456789abcdef/pipelines/health
Authorization: Bearer <token>
```

**Backend Response:**
```json
[
  {
    "id": 1,
    "instance_id": "01234567-89ab-cdef-0123-456789abcdef",
    "component_type": "exporter",
    "component_name": "otlp/http",
    "parent_pipeline": "traces",
    "healthy": true,
    "status": "StatusOK",
    "status_time_unix_nano": 1705324222000000000,
    "last_error": null,
    "created_at": "2024-01-15T14:30:22"
  },
  {
    "id": 2,
    "instance_id": "01234567-89ab-cdef-0123-456789abcdef",
    "component_type": "processor",
    "component_name": "batch/default",
    "parent_pipeline": "traces",
    "healthy": true,
    "status": "StatusOK",
    "status_time_unix_nano": null,
    "last_error": null,
    "created_at": "2024-01-15T14:30:22"
  }
  // ... more components
]
```

**Optional Filter by Component:**
```http
GET /api/v1/agents/{instanceId}/pipelines/health?component_name=otlp/http
```

**Frontend Usage:**
```typescript
const { data: pipelineHealth } = useQuery({
  queryKey: ['agentPipelineHealth', instanceId],
  queryFn: () => agentService.getAgentPipelineHealth(instanceId),
  refetchInterval: 30000,
});
```

**Component Types:**
- `pipeline` - Complete pipeline
- `exporter` - Data exporters (OTLP, Prometheus, etc.)
- `processor` - Data processors (batch, attributes, etc.)
- `receiver` - Data receivers (OTLP, Prometheus, etc.)
- `extension` - Extensions (health_check, pprof, etc.)

**Frontend Display:**
```typescript
// Table showing component health
<Table
  dataSource={pipelineHealth}
  columns={[
    { title: 'Component Type', dataIndex: 'component_type' },
    { title: 'Component Name', dataIndex: 'component_name' },
    { title: 'Parent Pipeline', dataIndex: 'parent_pipeline' },
    { title: 'Health', render: (_, record) => 
      record.healthy ? '✅ Healthy' : '❌ Unhealthy' 
    },
    { title: 'Last Error', dataIndex: 'last_error' },
  ]}
/>
```

## Error Handling

### Backend Error Format

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Examples:**

```json
// 400 Bad Request
{"detail": "Invalid YAML syntax"}

// 401 Unauthorized
{"detail": "Could not validate credentials"}

// 404 Not Found
{"detail": "Agent not found"}

// 422 Validation Error
{"detail": "Field 'config_yaml' is required"}

// 500 Internal Server Error
{"detail": "Database connection failed"}
```

### Frontend Error Handling

```typescript
try {
  await agentService.saveConfig(instanceId, config);
} catch (error: any) {
  // error.detail = backend error message
  message.error(error.detail || 'An error occurred');
}
```

## CORS Configuration

### Backend CORS Setup

Backend must allow frontend origin:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Production CORS

```python
allow_origins=[
    "https://dashboard.yourdomain.com",
    "https://yourdomain.com"
]
```

## Nginx Proxy (Production)

### Frontend nginx.conf

```nginx
location /api/ {
    proxy_pass http://backend:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Authorization $http_authorization;
}
```

This allows frontend to call `/api/agents` which proxies to `backend:8000/api/agents`.

## Testing API Integration

### Using Browser DevTools

1. Open DevTools (F12)
2. Go to Network tab
3. Perform action (e.g., login)
4. Check request/response:
   - Request headers (Authorization?)
   - Request payload
   - Response status (200, 401, etc.)
   - Response body

### Using curl

```bash
# Login
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Get agents
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer <token>"

# Save config
curl -X POST http://localhost:8000/api/agents/<id>/config \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"config_yaml": "receivers:\n  otlp:\n    ..."}'
```

## Common Integration Issues

### Issue 1: CORS Error
**Symptom:** "CORS policy: No 'Access-Control-Allow-Origin' header"

**Fix:**
- Check backend CORS configuration
- Ensure frontend origin is in `allow_origins`
- Or use nginx proxy (recommended)

### Issue 2: 401 Unauthorized
**Symptom:** All API calls return 401

**Check:**
- Token is stored in localStorage
- Token is in Authorization header
- Token hasn't expired

**Fix:**
```typescript
// Check token
console.log(localStorage.getItem('access_token'));

// Clear and re-login
localStorage.removeItem('access_token');
// Go to /login
```

### Issue 3: Network Error
**Symptom:** "Network Error" in console

**Check:**
- Backend is running: `curl http://localhost:8000/health`
- `VITE_API_URL` is correct in `.env`
- Firewall/network allows connection

### Issue 4: Type Mismatch
**Symptom:** TypeScript errors about response types

**Fix:** Update types in `src/types/index.ts` to match backend

## API Versioning

Currently: **v1** (implicit)

Future API versioning:
```
/api/v1/agents
/api/v2/agents
```

Frontend can switch versions via env var:
```env
VITE_API_VERSION=v1
```

## Rate Limiting

Backend may implement rate limiting. Frontend should handle 429 responses:

```typescript
if (error.response?.status === 429) {
  message.warning('Too many requests. Please wait...');
  // Retry after delay
}
```

## WebSocket Support (Future)

For real-time updates:

```typescript
// Future implementation
const ws = new WebSocket('ws://backend:8000/ws/agents');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  queryClient.invalidateQueries(['agents']);
};
```

---

## Integration Checklist

Before deployment:

- [ ] Backend CORS configured correctly
- [ ] `VITE_API_URL` points to production backend
- [ ] Authentication flow tested
- [ ] All API endpoints return expected data
- [ ] Error handling works for all error codes
- [ ] Network tab shows correct request/response
- [ ] Tokens expire and refresh correctly
- [ ] HTTPS enabled in production
- [ ] Nginx proxy configured (if using)
- [ ] Health checks working

---

This integration guide ensures smooth communication between frontend and backend! 🚀
