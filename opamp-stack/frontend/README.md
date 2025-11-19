# OpAMP Frontend Dashboard

Modern, responsive web dashboard for managing OpenTelemetry agents via OpAMP (Open Agent Management Protocol). Built with React, TypeScript, and Ant Design.

## 🚀 Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (fast HMR, optimized production builds)
- **UI Library**: Ant Design 5 (enterprise-grade components)
- **Styling**: Tailwind CSS (utility-first CSS)
- **Routing**: React Router v6 (SPA routing with protected routes)
- **State Management**: TanStack Query (server state management & caching)
- **HTTP Client**: Axios (with interceptors for auth)
- **Code Editor**: Monaco Editor (VS Code editor for YAML configs)
- **Date/Time**: Day.js (lightweight date library)

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable components
│   │   ├── Header.tsx       # App header with navigation
│   │   ├── MainLayout.tsx   # Main layout wrapper
│   │   ├── ProtectedRoute.tsx  # Route guard for authentication
│   │   └── StatsCards.tsx   # Dashboard statistics cards
│   ├── contexts/            # React contexts
│   │   └── AuthContext.tsx  # Authentication context & provider
│   ├── pages/               # Page components (routes)
│   │   ├── LoginPage.tsx    # User authentication page
│   │   ├── AgentsPage.tsx   # Agent list with filters & stats
│   │   ├── AgentHealthPage.tsx   # Detailed agent health monitoring
│   │   ├── ConfigEditorPage.tsx   # Config editor with Monaco
│   │   └── ConfigHistoryPage.tsx  # Config version history
│   ├── services/            # API service layer
│   │   ├── api.ts           # Axios client with interceptors
│   │   ├── authService.ts   # Authentication API calls
│   │   └── agentService.ts  # Agent management API calls
│   ├── types/               # TypeScript type definitions
│   │   └── index.ts         # All application types
│   ├── styles/              # Global styles
│   │   └── index.css        # Tailwind + custom CSS
│   ├── App.tsx              # Root component with routing
│   ├── main.tsx             # Application entry point
│   └── vite-env.d.ts        # Vite environment types
├── public/                  # Static assets
├── Dockerfile               # Multi-stage Docker build
├── nginx.conf               # Nginx config for production
├── package.json             # Dependencies & scripts
├── vite.config.ts           # Vite configuration
├── tsconfig.json            # TypeScript configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── .env.example             # Environment variables template
```

## 🎯 Features & Pages

### 1. Login Page (`/login`)
- **Authentication**: OAuth2 password flow with backend
- **Form Validation**: Real-time validation with helpful error messages
- **Auto-redirect**: Redirects to agents page if already authenticated
- **Credentials Storage**: Secure token storage in localStorage
- **Error Handling**: Clear feedback on authentication failures

### 2. Agents Page (`/agents`)
- **Stats Dashboard**: Real-time metrics (total, connected, healthy agents, OS distribution)
- **Agent Table**: Paginated table with sortable columns
  - Instance ID, Hostname, OS, Connection Status, Health, Last Seen
- **Advanced Filters**:
  - Search by hostname or instance ID
  - Filter by OS type
  - Filter by connection status (connected/disconnected)
  - Filter by health status (healthy/unhealthy)
- **Actions**:
  - Download config (YAML file)
  - View health details (modal)
  - Navigate to config editor
- **Auto-refresh**: Stats refresh every 30 seconds

### 3. Agent Health Page (`/agents/:instanceId/health`)
- **Agent Overview**: Complete agent information and current status
- **Current Health Status**: Real-time health snapshot with:
  - Health status (Healthy/Unhealthy)
  - Up status indicator
  - Last error messages
  - Status timestamps
- **Pipeline & Component Health**: Detailed OpenTelemetry Collector component monitoring
  - Individual component health (exporters, processors, receivers, extensions)
  - Component type filtering
  - Parent pipeline relationships
  - Component-specific error tracking
  - Real-time health status per component
- **Health History**: Historical health records with:
  - Timeline of health changes
  - Trend analysis
  - Filterable and sortable data
- **Auto-refresh**: All data refreshes every 30 seconds
- **Navigation**: Easy access from agents table

### 4. Config Editor Page (`/agents/:instanceId/config`)
- **Agent Information**: Full agent details in organized cards
- **Monaco Editor**: VS Code-quality YAML editor with:
  - Syntax highlighting
  - Line numbers
  - Minimap
  - Word wrap
  - Auto-formatting
- **Real-time Editing**: Track unsaved changes
- **Save Confirmation**: Modal confirmation before applying changes
- **Download Config**: Export current config as YAML file
- **Version History**: Quick access to previous versions
- **Attributes Display**: View agent identifying & non-identifying attributes

### 4. Config Editor Page (`/agents/:instanceId/config`)
- **Agent Information**: Full agent details in organized cards
- **Monaco Editor**: VS Code-quality YAML editor with:
  - Syntax highlighting
  - Line numbers
  - Minimap
  - Word wrap
  - Auto-formatting
- **Real-time Editing**: Track unsaved changes
- **Save Confirmation**: Modal confirmation before applying changes
- **Download Config**: Export current config as YAML file
- **Version History**: Quick access to previous versions
- **Attributes Display**: View agent identifying & non-identifying attributes

### 5. Config History Page (`/agents/:instanceId/config/history`)
- **Version List**: All config versions in sortable table
- **Version Details**: View any version in read-only Monaco editor
- **Restore Functionality**: Restore previous versions with confirmation
- **Version Metadata**:
  - Version number
  - Config hash
  - Source (MANUAL_UPDATE, SYNC_JOB, RESTORE)
  - Created by (user)
  - Created timestamp
- **Current Version Indicator**: Highlight active version

## 🔒 Security Features

- **Protected Routes**: Authentication required for all non-login pages
- **Token Management**: Automatic token injection in API requests
- **Auto-logout**: Redirects to login on 401 Unauthorized
- **CORS Handling**: Proxy configuration for API calls
- **Secure Headers**: Security headers in Nginx config

## 🛠️ Development Setup

### Prerequisites
- Node.js 18+ and npm
- Backend API running (default: http://localhost:8000)

### Installation

```bash
# Navigate to frontend directory
cd opamp-stack/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env if needed (set VITE_API_URL)
# VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Development Scripts

```bash
# Start dev server with HMR
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint TypeScript/React code
npm run lint
```

## 🐳 Docker Deployment

### Build Docker Image

```bash
# From frontend directory
docker build -t opamp-frontend:latest .
```

### Run Container Standalone

```bash
docker run -d \
  --name opamp-frontend \
  -p 3000:80 \
  -e VITE_API_URL=http://backend:8000 \
  opamp-frontend:latest
```

### Docker Compose Integration

Add to your `docker-compose.yml`:

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: opamp-frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - opamp-network
    restart: unless-stopped
```

Run with:

```bash
docker compose up -d frontend
```

## 🔌 API Integration

### Backend Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/token` | POST | User login (OAuth2) |
| `/api/auth/me` | GET | Get current user info |
| `/api/agents` | GET | List agents (with filters) |
| `/api/agents/stats` | GET | Get agent statistics |
| `/api/agents/:id` | GET | Get agent details |
| `/api/agents/:id/config` | GET | Get current config |
| `/api/agents/:id/config` | POST | Save new config |
| `/api/agents/:id/config/download` | GET | Download config YAML |
| `/api/agents/:id/config/history` | GET | Get config versions |
| `/api/agents/:id/config/restore` | POST | Restore config version |
| `/api/agents/:id/health` | GET | Get agent health |

### API Client Features

- **Automatic Token Injection**: Bearer token added to all requests
- **Error Handling**: Centralized error handling with user-friendly messages
- **Auto-logout**: Clears session on 401 responses
- **Request/Response Interceptors**: Axios interceptors for consistent behavior
- **Timeout Configuration**: 30-second timeout for all requests

## 🎨 Customization

### Theme Configuration

Edit `src/App.tsx` to customize Ant Design theme:

```typescript
<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#1890ff',  // Primary color
      borderRadius: 6,          // Border radius
      // Add more theme tokens
    },
  }}
>
```

### Tailwind Customization

Edit `tailwind.config.js` to extend Tailwind:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        // Custom colors
      },
    },
  },
}
```

## 📊 Performance Optimizations

- **Code Splitting**: Automatic route-based code splitting
- **Tree Shaking**: Vite removes unused code
- **Asset Optimization**: Images and fonts optimized
- **Gzip Compression**: Nginx gzip for smaller payloads
- **Browser Caching**: Cache static assets for 1 year
- **React Query Caching**: Smart server state caching (5 min stale time)

## 🧪 Type Safety

Full TypeScript coverage with:
- **Strict Mode**: All strict checks enabled
- **Type Definitions**: Complete types for all API responses
- **Interface Definitions**: Clear interfaces for props
- **No `any` Types**: Explicit typing throughout (warnings on `any`)

## 🌐 Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_APP_TITLE` | `OpAMP Dashboard` | Application title |

## 🚨 Troubleshooting

### Common Issues

**Issue**: API calls fail with CORS errors
- **Solution**: Ensure backend has CORS enabled or use Nginx proxy

**Issue**: Login doesn't work
- **Solution**: Check backend is running and `VITE_API_URL` is correct

**Issue**: Blank page after build
- **Solution**: Check browser console for errors, ensure all dependencies installed

**Issue**: Monaco Editor not loading
- **Solution**: Check network tab, may need CDN access

## 🔄 Deployment Workflow

```bash
# 1. Build frontend
cd frontend
npm run build

# 2. Build Docker image
docker build -t opamp-frontend:1.0.0 .

# 3. Tag for registry (optional)
docker tag opamp-frontend:1.0.0 your-registry/opamp-frontend:1.0.0

# 4. Push to registry (optional)
docker push your-registry/opamp-frontend:1.0.0

# 5. Deploy with compose
cd ..
docker compose up -d frontend
```

## 📚 Additional Resources

- [React Documentation](https://react.dev/)
- [Ant Design Components](https://ant.design/components/overview/)
- [TanStack Query Guide](https://tanstack.com/query/latest)
- [Monaco Editor API](https://microsoft.github.io/monaco-editor/)
- [Vite Guide](https://vitejs.dev/guide/)

## 🤝 Contributing

When contributing:
1. Follow existing code style (ESLint rules)
2. Add TypeScript types for new features
3. Test all new components
4. Update this README for new features

## 📄 License

Same license as the parent AmpBridge project.
