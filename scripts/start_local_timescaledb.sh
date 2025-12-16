#!/bin/bash
# =============================================================================
# Start Local TimescaleDB Development Environment
# =============================================================================
# 
# This script starts TimescaleDB and Redis in Docker for local development.
# It does NOT start the Django server - run that separately with:
#   python manage.py runserver
#
# Usage:
#   ./scripts/start_local_timescaledb.sh        # Start services
#   ./scripts/start_local_timescaledb.sh stop   # Stop services
#   ./scripts/start_local_timescaledb.sh reset  # Reset and restart
#
# After starting, run Django with:
#   source scripts/activate_local_timescaledb_env.sh
#   python manage.py migrate
#   python manage.py runserver
#
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AquaMind Local TimescaleDB Environment ===${NC}"

case "${1:-start}" in
    stop)
        echo -e "${YELLOW}Stopping TimescaleDB and Redis containers...${NC}"
        docker compose stop timescale-db redis
        echo -e "${GREEN}✓ Services stopped${NC}"
        ;;
    
    reset)
        echo -e "${YELLOW}Resetting database (destroying all data)...${NC}"
        docker compose down -v timescale-db redis
        docker compose up -d timescale-db redis
        echo -e "${YELLOW}Waiting for TimescaleDB to be ready...${NC}"
        sleep 5
        echo -e "${GREEN}✓ Services reset and started${NC}"
        echo ""
        echo -e "${YELLOW}Run 'python manage.py migrate' to recreate schema${NC}"
        ;;
    
    start|*)
        # Check if containers are already running
        if docker compose ps timescale-db | grep -q "running"; then
            echo -e "${YELLOW}TimescaleDB already running${NC}"
        else
            echo -e "${YELLOW}Starting TimescaleDB and Redis containers...${NC}"
            docker compose up -d timescale-db redis
            
            # Wait for PostgreSQL to be ready
            echo -e "${YELLOW}Waiting for TimescaleDB to accept connections...${NC}"
            for i in {1..30}; do
                if docker compose exec -T timescale-db pg_isready -U postgres > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ TimescaleDB is ready${NC}"
                    break
                fi
                sleep 1
                echo -n "."
            done
            echo ""
        fi
        
        # Verify TimescaleDB extension
        echo -e "${YELLOW}Verifying TimescaleDB extension...${NC}"
        TSDB_VERSION=$(docker compose exec -T timescale-db psql -U postgres -d aquamind_db -t -c "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';" 2>/dev/null || echo "NOT INSTALLED")
        
        if [[ "$TSDB_VERSION" == *"NOT INSTALLED"* ]]; then
            echo -e "${YELLOW}Installing TimescaleDB extension...${NC}"
            docker compose exec -T timescale-db psql -U postgres -d aquamind_db -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
            TSDB_VERSION=$(docker compose exec -T timescale-db psql -U postgres -d aquamind_db -t -c "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';")
        fi
        
        echo -e "${GREEN}✓ TimescaleDB version: ${TSDB_VERSION}${NC}"
        
        # Print connection info
        echo ""
        echo -e "${GREEN}=== Connection Info ===${NC}"
        echo "Host:     localhost"
        echo "Port:     5432"
        echo "Database: aquamind_db"
        echo "User:     postgres"
        echo "Password: adminpass1234"
        echo ""
        echo -e "${GREEN}=== Next Steps ===${NC}"
        echo "1. Source environment variables:"
        echo "   source scripts/activate_local_timescaledb_env.sh"
        echo ""
        echo "2. Run migrations (includes TimescaleDB hypertable setup):"
        echo "   python manage.py migrate"
        echo ""
        echo "3. Start Django development server:"
        echo "   python manage.py runserver"
        echo ""
        echo -e "${YELLOW}Note: TimescaleDB hypertables will be created during migration.${NC}"
        ;;
esac

