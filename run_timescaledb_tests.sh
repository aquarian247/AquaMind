#!/bin/bash
# Script to manually run TimescaleDB-specific tests
# This is only for manual testing and should not be used in CI/CD pipelines

# Set environment variable to enable TimescaleDB tests
export USE_TIMESCALEDB_TESTING="true"

echo "=== Running TimescaleDB manual tests ==="
echo "WARNING: This requires a properly configured PostgreSQL with TimescaleDB"
echo "         and will modify the test database schema."

# Use our TimescaleDB-specific test settings
python manage.py test apps.environmental.tests.test_timescaledb_features \
  --settings=aquamind.timescaledb_test_settings \
  --noinput \
  --keepdb
