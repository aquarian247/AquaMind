#!/bin/bash
# test_ci_auth.sh - Test Schemathesis authentication flow in CI-like environment
# 
# This script simulates the CI environment to test the Schemathesis authentication
# flow with the hooks-based approach. It validates that the authentication token
# is properly injected by the hooks rather than passed via command-line arguments.

set -e  # Exit on any error

# Cleanup function to ensure server is always killed
cleanup() {
  echo "🧹 Cleaning up..."
  if [ ! -z "$SERVER_PID" ]; then
    echo "Stopping Django server (PID: $SERVER_PID)"
    kill $SERVER_PID 2>/dev/null || true
  fi
  echo "Done."
}

# Register cleanup to run on script exit
trap cleanup EXIT INT TERM

# Set CI settings
DJANGO_SETTINGS="aquamind.settings_ci"

echo "🔄 Applying migrations using CI settings..."
python manage.py migrate --settings=$DJANGO_SETTINGS --noinput

echo "🔑 Getting CI auth token..."
# First run with debug to see any issues
python manage.py get_ci_token --settings=$DJANGO_SETTINGS --debug || true

# Now capture the actual token
TOKEN=$(python manage.py get_ci_token --settings=$DJANGO_SETTINGS)

# Validate token
if [ -z "$TOKEN" ]; then
  echo "❌ Failed to obtain CI auth token"
  exit 1
fi

echo "✅ CI auth token ready (length: ${#TOKEN})"

# Export environment variables for Schemathesis hooks
echo "🔌 Setting up Schemathesis hooks..."
export SCHEMATHESIS_AUTH_TOKEN="$TOKEN"
export SCHEMATHESIS_HOOKS="aquamind.utils.schemathesis_hooks"

echo "🚀 Starting Django server in background..."
python manage.py runserver 0.0.0.0:8000 --settings=$DJANGO_SETTINGS &
SERVER_PID=$!

echo "⏳ Waiting for server to be ready..."
ATTEMPTS=0
until curl -s http://127.0.0.1:8000/ > /dev/null; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ $ATTEMPTS -gt 30 ]; then
    echo "❌ Server did not start in time"
    exit 1
  fi
  echo "  Still waiting... (attempt $ATTEMPTS/30)"
  sleep 2
done
echo "✅ Django server is up and running"

echo "🧪 Running Schemathesis tests..."
echo "Note: No --header parameter is used - auth should be injected by hooks"

# Run Schemathesis with hooks but WITHOUT explicit auth header
schemathesis run \
  --base-url=http://127.0.0.1:8000 \
  --checks all \
  --hypothesis-max-examples=3 \
  --hypothesis-suppress-health-check=filter_too_much,data_too_large \
  --show-errors-tracebacks \
  api/openapi.yaml

STATUS=$?

if [ $STATUS -eq 0 ]; then
  echo "✅ Schemathesis tests passed successfully!"
else
  echo "❌ Schemathesis detected contract test failures"
fi

echo "Test complete with status: $STATUS"
exit $STATUS
