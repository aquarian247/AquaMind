#!/bin/bash
# Simplified test runner that uses SQLite and skips TimescaleDB operations
# This script is intended for CI/CD and regular development testing

echo "=== Running AquaMind Tests (SQLite mode) ==="
echo "Note: TimescaleDB tests will be skipped"

# Use our test settings with SQLite
python manage.py test \
  --settings=aquamind.test_settings \
  --testrunner=apps.core.test_runner.TimescaleDBTestRunner \
  --noinput \
  --keepdb
