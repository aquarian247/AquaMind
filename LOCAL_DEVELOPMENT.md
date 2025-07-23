# Local Development Setup

This document describes how to set up and run the AquaMind project locally without using Docker or devcontainers.

## Prerequisites

- Python 3.11+
- PostgreSQL v17+ with TimescaleDB extension installed
- Git

## Database Setup

1. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE aquamind_db;
   ```

2. Enable the TimescaleDB extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   ```

3. Configure the database connection in `aquamind/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'aquamind_db',
           'USER': 'postgres',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
           'OPTIONS': {
               'options': '-c search_path=public'
           }
       }
   }
   ```

## Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Migrations

1. Apply Django migrations:
   ```bash
   python manage.py migrate
   ```

2. If you encounter issues with TimescaleDB-specific migrations, you can:
   - Apply non-TimescaleDB migrations first
   - Fake the TimescaleDB migrations: `python manage.py migrate environmental --fake`
   - Run the custom TimescaleDB setup script: `python setup_timescaledb.py`

## Creating a Superuser

```bash
python manage.py createsuperuser
```

## Running the Development Server

```bash
python manage.py runserver
```

## Notes on TimescaleDB

The project uses TimescaleDB for time-series data, particularly for:
- `environmental_environmentalreading` table
- `environmental_weatherdata` table

These tables are configured as hypertables with time-based partitioning for efficient time-series data storage and querying.

## Switching Between Local and Container Development

This project supports both local development and development using devcontainers:

- For local development, follow the instructions in this document
- For container-based development, use the `.devcontainer` configuration and `docker-compose.yml`

## Troubleshooting

If you encounter issues with TimescaleDB migrations or hypertable setup, you can use the custom `setup_timescaledb.py` script to properly configure the hypertables.
