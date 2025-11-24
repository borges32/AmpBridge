#!/bin/bash

# ============================================================================
# Migrate Docker Images to Podman
# ============================================================================
# This script migrates existing Docker images to Podman
# ============================================================================

set -e

echo "========================================="
echo "Docker to Podman Image Migration"
echo "========================================="
echo ""

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo "❌ Docker daemon is not running"
    exit 1
fi

# Check if Podman is installed
if ! command -v podman &> /dev/null; then
    echo "❌ Podman is not installed"
    echo ""
    echo "Install Podman first:"
    echo "  sudo dnf install -y podman"
    exit 1
fi

echo "✅ Docker and Podman are both available"
echo ""

# Images to migrate
IMAGES=(
    "local/opamp-server:latest"
    "local/opamp-backend:latest"
    "local/opamp-frontend:latest"
)

# Create temporary directory for tar files
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"
echo ""

# Migrate each image
for img in "${IMAGES[@]}"; do
    echo "========================================="
    echo "Migrating: $img"
    echo "========================================="
    
    # Check if image exists in Docker
    if ! docker image inspect "$img" &> /dev/null; then
        echo "⚠️  Image not found in Docker: $img"
        echo "Skipping..."
        echo ""
        continue
    fi
    
    # Check if image already exists in Podman
    if podman image exists "$img" 2>/dev/null; then
        echo "⚠️  Image already exists in Podman: $img"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping..."
            echo ""
            continue
        fi
        podman rmi "$img"
    fi
    
    # Save from Docker
    echo "📦 Saving from Docker..."
    TAR_FILE="$TEMP_DIR/$(echo $img | tr '/:' '_').tar"
    docker save -o "$TAR_FILE" "$img"
    
    # Load into Podman
    echo "📥 Loading into Podman..."
    podman load -i "$TAR_FILE"
    
    # Verify
    if podman image exists "$img"; then
        echo "✅ Successfully migrated: $img"
    else
        echo "❌ Failed to migrate: $img"
    fi
    
    # Clean up tar file
    rm -f "$TAR_FILE"
    echo ""
done

# Clean up temp directory
rmdir "$TEMP_DIR" 2>/dev/null || true

echo "========================================="
echo "Migration Complete!"
echo "========================================="
echo ""

# List migrated images in Podman
echo "Images now in Podman:"
podman images | grep "local/"
echo ""

# Show next steps
echo "Next steps:"
echo ""
echo "1. Verify images:"
echo "   podman images"
echo ""
echo "2. Start the stack with Podman:"
echo "   podman-compose -f podman-compose.yml up -d"
echo ""
echo "3. (Optional) Remove Docker images to save space:"
for img in "${IMAGES[@]}"; do
    echo "   docker rmi $img"
done
echo ""
