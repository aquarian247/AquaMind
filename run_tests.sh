#!/bin/bash
# Script to run tests without TimescaleDB and avoid manual interaction

# Set environment variable to skip TimescaleDB related tests
export USE_TIMESCALEDB_TESTING="false"

echo "=== Running tests with TimescaleDB tests skipped ==="

# Use --settings to specify our test_settings.py file which uses SQLite instead of PostgreSQL
# Use --noinput to avoid manual confirmation
# Use our custom test runner which handles test database creation properly
python manage.py test "$@" --settings=aquamind.test_settings --noinput --testrunner=apps.core.test_runner.TimescaleDBTestRunner
