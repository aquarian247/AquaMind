#!/bin/bash
# scripts/regenerate_api.sh
#
# Regenerates the OpenAPI specification from Django models/serializers
# and optionally triggers frontend TypeScript client generation.
#
# Usage:
#   ./scripts/regenerate_api.sh [--frontend] [--validate] [--watch]
#
# Options:
#   --frontend    Also regenerate the frontend TypeScript client
#   --validate    Validate the generated OpenAPI spec
#   --watch       Watch for changes and regenerate (requires entr)
#
# This script is designed to be used by Factory workspace file watchers
# to automatically regenerate API specs when Django models/serializers change.

set -e  # Exit immediately if a command exits with a non-zero status

# Configuration
BACKEND_DIR="."
FRONTEND_DIR="../AquaMind-Frontend"
OPENAPI_OUTPUT="api/openapi.yaml"
FRONTEND_SCRIPT="npm run generate:api"

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

# Parse arguments
REGENERATE_FRONTEND=false
VALIDATE_SPEC=false
WATCH_MODE=false

for arg in "$@"; do
  case $arg in
    --frontend)
      REGENERATE_FRONTEND=true
      shift
      ;;
    --validate)
      VALIDATE_SPEC=true
      shift
      ;;
    --watch)
      WATCH_MODE=true
      shift
      ;;
    *)
      # Unknown option
      echo -e "${RED}Unknown option: $arg${RESET}"
      exit 1
      ;;
  esac
done

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to regenerate the OpenAPI spec
regenerate_spec() {
  echo -e "\n${BOLD}Regenerating OpenAPI specification...${RESET}"
  
  # Check if we're in the right directory
  if [ ! -f "manage.py" ]; then
    echo -e "${RED}Error: manage.py not found. Please run this script from the Django project root.${RESET}"
    exit 1
  fi
  
  # Generate the OpenAPI spec
  python manage.py spectacular --file "$OPENAPI_OUTPUT"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ OpenAPI spec generated successfully at $OPENAPI_OUTPUT${RESET}"
  else
    echo -e "${RED}✗ Failed to generate OpenAPI spec${RESET}"
    exit 1
  fi
  
  # Validate if requested
  if [ "$VALIDATE_SPEC" = true ]; then
    echo -e "\n${BOLD}Validating OpenAPI specification...${RESET}"
    python manage.py spectacular --file "$OPENAPI_OUTPUT" --validate
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}✓ OpenAPI spec validation passed${RESET}"
    else
      echo -e "${RED}✗ OpenAPI spec validation failed${RESET}"
      exit 1
    fi
  fi
}

# Function to regenerate the frontend TypeScript client
regenerate_frontend() {
  if [ "$REGENERATE_FRONTEND" = true ]; then
    echo -e "\n${BOLD}Regenerating frontend TypeScript client...${RESET}"
    
    # Check if frontend directory exists
    if [ ! -d "$FRONTEND_DIR" ]; then
      echo -e "${YELLOW}⚠ Frontend directory not found at $FRONTEND_DIR${RESET}"
      echo -e "${YELLOW}⚠ Skipping frontend client generation${RESET}"
      return
    fi
    
    # Copy OpenAPI spec to frontend if needed
    FRONTEND_OPENAPI_DIR="$FRONTEND_DIR/api"
    if [ ! -d "$FRONTEND_OPENAPI_DIR" ]; then
      mkdir -p "$FRONTEND_OPENAPI_DIR"
    fi
    
    cp "$OPENAPI_OUTPUT" "$FRONTEND_OPENAPI_DIR/"
    
    # Change to frontend directory and run generation script
    pushd "$FRONTEND_DIR" > /dev/null
    
    if [ -f "package.json" ]; then
      echo -e "${YELLOW}Running: $FRONTEND_SCRIPT${RESET}"
      eval "$FRONTEND_SCRIPT"
      
      if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend TypeScript client generated successfully${RESET}"
      else
        echo -e "${RED}✗ Failed to generate frontend TypeScript client${RESET}"
        popd > /dev/null
        exit 1
      fi
    else
      echo -e "${RED}✗ package.json not found in frontend directory${RESET}"
      popd > /dev/null
      exit 1
    fi
    
    popd > /dev/null
  fi
}

# Main execution
if [ "$WATCH_MODE" = true ]; then
  # Check if entr is installed
  if ! command_exists entr; then
    echo -e "${RED}Error: 'entr' is required for watch mode but not installed.${RESET}"
    echo -e "${YELLOW}Install with: apt-get install entr (Debian/Ubuntu) or brew install entr (macOS)${RESET}"
    exit 1
  fi
  
  echo -e "${BOLD}Watching for changes in apps/ directory...${RESET}"
  echo -e "${YELLOW}Press Ctrl+C to stop watching${RESET}\n"
  
  # Use find to get all Python files in the apps directory and pass to entr
  # When any file changes, regenerate the spec and frontend client
  find apps -name "*.py" | entr -c bash -c "$(declare -f regenerate_spec); $(declare -f regenerate_frontend); regenerate_spec; regenerate_frontend"
else
  # Single run mode
  regenerate_spec
  regenerate_frontend
  
  echo -e "\n${GREEN}${BOLD}✓ API regeneration complete!${RESET}"
fi
