#!/bin/bash
# Cleanup database script wrapper
# Can be executed from host or inside container

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running inside container
if [ -f "/.dockerenv" ]; then
    IN_CONTAINER=true
    print_info "Running inside container"
else
    IN_CONTAINER=false
    print_info "Running from host - will execute in container"
fi

# Parse arguments
DRY_RUN=""
BACKUP=""
CONFIRM=""
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --backup)
            BACKUP="--backup"
            shift
            ;;
        --confirm)
            CONFIRM="--confirm"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run     Show what would be deleted without deleting"
            echo "  --backup      Show backup command before cleanup"
            echo "  --confirm     Skip confirmation prompt"
            echo "  --verbose     Show detailed SQL operations"
            echo "  -h, --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --dry-run                    # See what would be deleted"
            echo "  $0 --backup --confirm           # Create backup and cleanup"
            echo "  $0                              # Interactive mode"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Execute cleanup
if [ "$IN_CONTAINER" = true ]; then
    # Running inside container
    print_info "Executing cleanup script..."
    python3 "$SCRIPT_DIR/cleanup_database.py" $DRY_RUN $BACKUP $CONFIRM $VERBOSE
else
    # Running from host - execute in container
    CONTAINER_NAME="opamp-backend"
    
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_error "Container '$CONTAINER_NAME' is not running"
        echo "Start it with: docker compose up -d backend"
        exit 1
    fi
    
    print_info "Executing cleanup in container '$CONTAINER_NAME'..."
    docker exec -it "$CONTAINER_NAME" python cleanup_database.py $DRY_RUN $BACKUP $CONFIRM $VERBOSE
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    print_info "Script completed successfully"
else
    print_error "Script failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
