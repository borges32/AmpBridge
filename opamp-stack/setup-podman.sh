#!/bin/bash

# ============================================================================
# Podman Setup Script for Red Hat Enterprise Linux
# ============================================================================
# This script prepares the environment for running OpAMP Stack with Podman
# on Red Hat Enterprise Linux (RHEL) 8/9 or compatible systems.
# ============================================================================

set -e

echo "========================================="
echo "OpAMP Stack - Podman Setup for RHEL"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  Warning: Running as root. Consider using rootless mode for better security."
   echo ""
fi

# ============================================================================
# Step 1: Check Podman installation
# ============================================================================
echo "Step 1: Checking Podman installation..."

if ! command -v podman &> /dev/null; then
    echo "❌ Podman is not installed!"
    echo ""
    echo "To install Podman on RHEL, run:"
    echo "  sudo dnf install -y podman podman-compose"
    echo ""
    exit 1
fi

PODMAN_VERSION=$(podman --version)
echo "✅ Podman is installed: $PODMAN_VERSION"
echo ""

# ============================================================================
# Step 2: Check podman-compose installation
# ============================================================================
echo "Step 2: Checking podman-compose installation..."

if ! command -v podman-compose &> /dev/null; then
    echo "⚠️  podman-compose is not installed!"
    echo ""
    echo "Installing podman-compose via pip..."
    
    # Check if pip3 is available
    if command -v pip3 &> /dev/null; then
        pip3 install --user podman-compose
        echo "✅ podman-compose installed"
    else
        echo "❌ pip3 is not available. Install it first:"
        echo "  sudo dnf install -y python3-pip"
        exit 1
    fi
else
    COMPOSE_VERSION=$(podman-compose --version 2>/dev/null || echo "unknown")
    echo "✅ podman-compose is installed: $COMPOSE_VERSION"
fi
echo ""

# ============================================================================
# Step 3: Check SELinux status
# ============================================================================
echo "Step 3: Checking SELinux status..."

if command -v getenforce &> /dev/null; then
    SELINUX_STATUS=$(getenforce)
    echo "SELinux status: $SELINUX_STATUS"
    
    if [ "$SELINUX_STATUS" = "Enforcing" ]; then
        echo "✅ SELinux is enforcing (volumes use :Z flag for compatibility)"
    fi
else
    echo "⚠️  SELinux tools not found (sestatus)"
fi
echo ""

# ============================================================================
# Step 4: Configure user namespaces (if not root)
# ============================================================================
if [ "$EUID" -ne 0 ]; then
    echo "Step 4: Configuring rootless Podman..."
    
    # Check if subuid/subgid are configured
    if ! grep -q "^$(whoami):" /etc/subuid 2>/dev/null; then
        echo "⚠️  User subordinate UIDs not configured"
        echo "Run as root:"
        echo "  sudo usermod --add-subuids 100000-165535 $(whoami)"
        echo "  sudo usermod --add-subgids 100000-165535 $(whoami)"
    else
        echo "✅ User namespaces configured"
    fi
    
    # Enable linger for user (keeps user services running)
    if command -v loginctl &> /dev/null; then
        loginctl enable-linger $(whoami) 2>/dev/null || true
        echo "✅ User linger enabled"
    fi
else
    echo "Step 4: Running as root - skipping rootless configuration"
fi
echo ""

# ============================================================================
# Step 5: Create Podman network
# ============================================================================
echo "Step 5: Setting up Podman network..."

if podman network exists opamp-network 2>/dev/null; then
    echo "✅ Network 'opamp-network' already exists"
else
    podman network create opamp-network
    echo "✅ Network 'opamp-network' created"
fi
echo ""

# ============================================================================
# Step 6: Check if images exist
# ============================================================================
echo "Step 6: Checking for required images..."

IMAGES_NEEDED=(
    "postgres:16-alpine"
    "local/opamp-server:latest"
    "local/opamp-backend:latest"
    "haproxy:2.9"
    "local/opamp-frontend:latest"
)

MISSING_IMAGES=()

for img in "${IMAGES_NEEDED[@]}"; do
    if podman image exists "$img"; then
        echo "✅ Image exists: $img"
    else
        echo "⚠️  Missing image: $img"
        MISSING_IMAGES+=("$img")
    fi
done
echo ""

if [ ${#MISSING_IMAGES[@]} -gt 0 ]; then
    echo "⚠️  Missing images detected!"
    echo ""
    echo "For official images (postgres, haproxy), they will be pulled automatically."
    echo ""
    echo "For local images, you need to:"
    echo "  1. Build them with Docker/Podman first, OR"
    echo "  2. Load them from tar files, OR"
    echo "  3. Pull from a registry"
    echo ""
    echo "Example - Build with Podman:"
    echo "  cd opamp-server && podman build -t local/opamp-server:latest ."
    echo "  cd ../backend && podman build -t local/opamp-backend:latest ."
    echo "  cd ../frontend && podman build -t local/opamp-frontend:latest ."
    echo ""
    echo "Example - Save/Load from Docker:"
    echo "  docker save local/opamp-server:latest | podman load"
    echo ""
fi

# ============================================================================
# Step 7: Configure firewall (if firewalld is running)
# ============================================================================
echo "Step 7: Checking firewall configuration..."

if systemctl is-active --quiet firewalld; then
    echo "Firewalld is active"
    echo ""
    echo "Ports used by OpAMP Stack:"
    echo "  - 3000  (Frontend)"
    echo "  - 4320  (HAProxy)"
    echo "  - 4321  (OpAMP Server UI)"
    echo "  - 5432  (PostgreSQL)"
    echo "  - 8000  (Backend API)"
    echo ""
    echo "To open these ports, run:"
    echo "  sudo firewall-cmd --permanent --add-port=3000/tcp"
    echo "  sudo firewall-cmd --permanent --add-port=4320/tcp"
    echo "  sudo firewall-cmd --permanent --add-port=4321/tcp"
    echo "  sudo firewall-cmd --permanent --add-port=5432/tcp"
    echo "  sudo firewall-cmd --permanent --add-port=8000/tcp"
    echo "  sudo firewall-cmd --reload"
else
    echo "✅ Firewalld is not active"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Ensure all required images are available (see above)"
echo ""
echo "2. Start the stack:"
echo "   podman-compose -f podman-compose.yml up -d"
echo ""
echo "3. Check status:"
echo "   podman-compose -f podman-compose.yml ps"
echo ""
echo "4. View logs:"
echo "   podman-compose -f podman-compose.yml logs -f"
echo ""
echo "5. Stop the stack:"
echo "   podman-compose -f podman-compose.yml down"
echo ""
echo "Access URLs:"
echo "  - Frontend:    http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - OpAMP UI:    http://localhost:4321"
echo "  - HAProxy:     http://localhost:4320"
echo ""
echo "========================================="
