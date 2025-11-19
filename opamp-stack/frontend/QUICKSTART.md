# OpAMP Frontend - Quick Start Guide

Get the OpAMP Dashboard running in 5 minutes! 🚀

## Prerequisites

- Node.js 18+ installed ([Download](https://nodejs.org/))
- Backend API running (see backend README)
- Or use Docker Compose (easiest!)

## Option 1: Docker Compose (Recommended) 🐳

**Start everything (backend + frontend):**

```bash
cd opamp-stack
docker compose up -d
```

**Access the dashboard:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- OpAMP Server: http://localhost:4321

**Default credentials:**
- Username: `admin`
- Password: `admin`

That's it! 🎉

## Option 2: Local Development 💻

### Step 1: Install Dependencies

```bash
cd opamp-stack/frontend
npm install
```

### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if your backend is not on `localhost:8000`:

```env
VITE_API_URL=http://your-backend:8000
```

### Step 3: Start Dev Server

```bash
npm run dev
```

Open http://localhost:3000

### Step 4: Login

Default credentials:
- Username: `admin`
- Password: `admin`

## First Steps in the Dashboard

### 1. View Agents
After login, you'll see the Agents page with:
- **Stats cards**: Total, connected, healthy agents
- **Agent table**: All your registered agents
- **Filters**: Search and filter by OS, status, health

### 2. Configure an Agent
Click the **Config** button on any agent to:
- View agent details
- Edit YAML configuration
- Save and apply changes

### 3. View Config History
Click **View History** to:
- See all previous versions
- Compare changes
- Restore previous versions

## Common Tasks

### Add Test Data

If you don't have agents yet, use the backend to create test agents:

```bash
cd opamp-stack/backend
# Follow backend README to register agents
```

### Download Agent Config

From the Agents table:
1. Click the **download icon** (↓) on any agent
2. YAML file downloads automatically

### Edit Agent Config

1. Click **Config** button on an agent
2. Edit YAML in the Monaco editor
3. Click **Save Configuration**
4. Confirm the modal
5. Config is sent to the agent!

### Restore Previous Config

1. Go to agent config page
2. Click **View History**
3. Click **View** on any version to preview
4. Click **Restore** to apply that version
5. Confirm restoration

## Troubleshooting

### ❌ "Cannot connect to backend"

**Check:**
```bash
# Is backend running?
curl http://localhost:8000/health

# Check logs
docker compose logs backend
```

**Fix:** Start backend or update `VITE_API_URL` in `.env`

### ❌ "Login failed"

**Check:**
- Backend is running
- Credentials are correct (default: admin/admin)
- Check browser console for errors

**Fix:**
```bash
# Reset backend database
docker compose down -v
docker compose up -d
```

### ❌ Blank page after login

**Check browser console** (F12) for errors

**Common causes:**
- API URL misconfigured
- CORS issues (use proxy or fix backend CORS)
- Missing dependencies

**Fix:**
```bash
# Reinstall dependencies
rm -rf node_modules
npm install
npm run dev
```

### ❌ Monaco Editor not loading

**Check:**
- Internet connection (CDN required)
- Browser console for errors

**Fix:** Monaco loads from CDN, ensure network access

## Development Tips

### Hot Reload

Vite provides instant HMR. Edit any file and see changes immediately!

### View Network Calls

1. Open DevTools (F12)
2. Go to Network tab
3. See all API calls to backend

### React Query DevTools

TanStack Query DevTools are included (dev only):
- See cached queries
- Inspect query states
- Manually trigger refetch

Look for floating icon in bottom-right corner.

### TypeScript Errors

```bash
# Check types
npm run build

# Or use IDE (VS Code recommended)
# TypeScript errors show inline
```

## Useful Commands

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

## Docker Commands

```bash
# Build frontend image
docker compose build frontend

# Start only frontend
docker compose up -d frontend

# View logs
docker compose logs -f frontend

# Restart frontend
docker compose restart frontend

# Stop everything
docker compose down

# Stop and remove volumes
docker compose down -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |
| `VITE_APP_TITLE` | `OpAMP Dashboard` | Browser tab title |

## Browser Support

Tested on:
- ✅ Chrome 120+
- ✅ Firefox 120+
- ✅ Edge 120+
- ✅ Safari 16+

## Performance Tips

### Slow Loading?
- Check backend response times
- Enable gzip in nginx (already configured)
- Use production build (not dev server)

### High Memory Usage?
- Monaco Editor can use ~100MB
- Close unused tabs
- Restart browser

## Next Steps

1. **Explore Features**: Try all buttons and filters
2. **Register Agents**: Follow backend guide to connect real agents
3. **Customize Theme**: Edit `src/App.tsx` theme config
4. **Add Features**: See ARCHITECTURE.md for extensibility guide

## Getting Help

**Issues?**
1. Check browser console (F12)
2. Check backend logs: `docker compose logs backend`
3. Check frontend logs: `docker compose logs frontend`
4. Read full README.md
5. Read ARCHITECTURE.md

## Production Deployment Checklist

Before deploying to production:

- [ ] Change default admin password
- [ ] Set `VITE_API_URL` to production backend
- [ ] Enable HTTPS (use reverse proxy like nginx/caddy)
- [ ] Configure CORS properly on backend
- [ ] Set up monitoring (e.g., Sentry for errors)
- [ ] Run `npm run build` to create optimized bundle
- [ ] Test all features in production environment
- [ ] Set up backup strategy for configs

## Quick Reference

**Pages:**
- `/login` - Authentication
- `/agents` - Agent list with stats
- `/agents/:id/config` - Config editor
- `/agents/:id/config/history` - Version history

**Key Files:**
- `src/App.tsx` - Routing & theme
- `src/services/agentService.ts` - API calls
- `src/types/index.ts` - TypeScript types
- `.env` - Environment config

**Ports:**
- `3000` - Frontend (dev)
- `80` - Frontend (Docker)
- `8000` - Backend API
- `4321` - OpAMP Server
- `5432` - PostgreSQL

Happy coding! 🎉
