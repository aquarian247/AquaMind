#!/bin/bash
# scripts/regenerate_openapi.sh
# Regenerates the OpenAPI specification and stages it for commit if changed

set -e  # Exit immediately if a command exits with a non-zero status

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define paths
SPEC_FILE="api/openapi.yaml"
SETTINGS="aquamind.settings_ci"

echo -e "${YELLOW}Regenerating OpenAPI specification...${NC}"

# Check if we're in the project root (where manage.py is)
if [ ! -f "manage.py" ]; then
    echo -e "${RED}Error: This script must be run from the project root directory (where manage.py is located)${NC}"
    exit 1
fi

# Run the Django management command to generate the spec
python manage.py spectacular --file "$SPEC_FILE" --settings="$SETTINGS"

# Check if the spec has changed
if git diff --quiet -- "$SPEC_FILE"; then
    echo -e "${GREEN}OpenAPI spec is up to date.${NC}"
    exit 0
else
    echo -e "${YELLOW}OpenAPI spec has changed. Staging for commit...${NC}"
    git add "$SPEC_FILE"
    echo -e "${GREEN}OpenAPI spec regenerated and staged for commit.${NC}"
    echo -e "${YELLOW}Hint: If this was run manually, remember to commit the changes.${NC}"
    exit 0
fi
