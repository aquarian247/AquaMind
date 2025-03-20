# Docker Development Environment

## Overview

AquaMind uses a containerized development environment to ensure consistent development experience across different machines. The environment consists of:

1. **Development Container**: A Python 3.11 container with Node.js for frontend development
2. **TimescaleDB Container**: A PostgreSQL database with TimescaleDB extension for time-series data

## Environment Setup

### Development Container

The development container is configured in `.devcontainer/devcontainer.json` with:

- Python 3.11 as the base image
- Node.js 20 for frontend development
- Network connection to the TimescaleDB container
- Automatic installation of dependencies upon container creation
- Visual Studio Code extensions for Python and JavaScript development

```json
{
  "name": "AquaMind Dev Container",
  "image": "mcr.microsoft.com/devcontainers/python:3.11",
  "features": {
    "ghcr.io/devcontainers/features/node:1": {
      "version": "20"
    }
  },
  "runArgs": ["--network=aquamind-net"],
  "postCreateCommand": "pip install -r requirements.txt && npm install",
  "containerEnv": {
    "DATABASE_URL": "postgresql://postgres:aquapass12345@timescale-db:5432/aquamind_db"
  },
  "settings": {
    "terminal.integrated.shell.linux": "/bin/bash"
  },
  "extensions": [
    "ms-python.python",
    "ms-vscode.vscode-typescript-tslint-plugin",
    "dbaeumer.vscode-eslint"
  ]
}
```

### Database Container

The TimescaleDB container runs PostgreSQL with the TimescaleDB extension. It's connected to the same Docker network (`aquamind-net`) as the development container.

Database connection settings are configured in `aquamind/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aquamind_db',
        'USER': 'postgres',
        'PASSWORD': 'aquapass12345',
        'HOST': 'timescale-db',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        }
    }
}
```

## Starting the Environment

The development environment is set up to run in the Windsurf IDE, which automatically creates the containers according to the configuration.

To start development:

1. Open the project in Windsurf IDE
2. The IDE will automatically build and start the development container
3. The TimescaleDB container will be available at `timescale-db:5432`
4. Django will connect to the database using the settings in `settings.py`

## Potential Improvements

For future development:

1. Create a `docker-compose.yml` file to formalize the multi-container setup
2. Refactor database settings to use environment variables instead of hardcoded values
3. Add separate configurations for development, testing, and production environments
