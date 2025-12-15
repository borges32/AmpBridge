#!/bin/bash
# Quick fix script for duplicate hostname issue

set -e

echo "========================================================"
echo "HOSTNAME SYNC DUPLICATE FIX - Quick Guide"
echo "========================================================"
echo ""

# Check if inside container
if [ -f "/.dockerenv" ]; then
    IN_CONTAINER=true
    echo "✓ Running inside container"
else
    IN_CONTAINER=false
    echo "⚠ Running from host"
fi

echo ""
echo "Steps to fix:"
echo ""
echo "1. Preview duplicates (dry-run):"
if [ "$IN_CONTAINER" = true ]; then
    echo "   python fix_duplicate_hostnames.py --dry-run"
else
    echo "   docker exec -it opamp-backend python fix_duplicate_hostnames.py --dry-run"
fi

echo ""
echo "2. Fix specific hostname (e.g., DESKTOP-C49UQO6):"
if [ "$IN_CONTAINER" = true ]; then
    echo "   python fix_duplicate_hostnames.py --hostname DESKTOP-C49UQO6"
else
    echo "   docker exec -it opamp-backend python fix_duplicate_hostnames.py --hostname DESKTOP-C49UQO6"
fi

echo ""
echo "3. Fix ALL duplicates:"
if [ "$IN_CONTAINER" = true ]; then
    echo "   python fix_duplicate_hostnames.py"
else
    echo "   docker exec -it opamp-backend python fix_duplicate_hostnames.py"
fi

echo ""
echo "4. Restart backend to apply code fix:"
echo "   docker compose restart backend"

echo ""
echo "5. Verify no duplicates remain:"
echo "   docker exec -i opamp-postgres psql -U opamp opamp -c \\"
echo "     \"SELECT host_name, COUNT(*) FROM agents WHERE host_name IS NOT NULL GROUP BY host_name HAVING COUNT(*) > 1;\""

echo ""
echo "========================================================"
echo ""

# Interactive mode
read -p "Do you want to run the dry-run preview now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ "$IN_CONTAINER" = true ]; then
        python fix_duplicate_hostnames.py --dry-run
    else
        docker exec -it opamp-backend python fix_duplicate_hostnames.py --dry-run
    fi
fi
