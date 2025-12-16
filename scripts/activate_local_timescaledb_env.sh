#!/bin/bash
# =============================================================================
# Activate Local TimescaleDB Environment Variables
# =============================================================================
#
# Source this file to configure Django to use the Docker TimescaleDB:
#   source scripts/activate_local_timescaledb_env.sh
#
# This sets environment variables for connecting to:
# - TimescaleDB on localhost:5432 (Docker container)
# - Redis on localhost:6379 (Docker container)
#
# =============================================================================

# Database Configuration (Docker TimescaleDB)
export DB_HOST=localhost
export DB_NAME=aquamind_db
export DB_USER=postgres
export DB_PASSWORD=adminpass1234
export DB_PORT=5432
export DATABASE_HOST=localhost
export DATABASE_URL="postgresql://postgres:adminpass1234@localhost:5432/aquamind_db"

# Enable TimescaleDB operations
export TIMESCALE_ENABLED=true
export USE_TIMESCALEDB=true

# Celery/Redis Configuration (Docker Redis)
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
export REDIS_URL=redis://localhost:6379/1

# Django Settings
export DJANGO_SETTINGS_MODULE=aquamind.settings
export DJANGO_DEBUG=true

echo "✓ Environment configured for local TimescaleDB (Docker)"
echo ""
echo "Database: postgresql://postgres:***@localhost:5432/aquamind_db"
echo "Redis:    redis://localhost:6379"
echo ""
echo "Run 'python manage.py migrate' if tables need to be created."

