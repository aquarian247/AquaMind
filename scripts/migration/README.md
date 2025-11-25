# FishTalk to AquaMind Migration Scripts

## Overview

This directory contains scripts for migrating data from the legacy FishTalk system to AquaMind. The migration framework implements a chronological replay approach that preserves audit trails and data integrity.

## Prerequisites

- Python 3.11+
- PostgreSQL database
- Microsoft ODBC Driver 18 for SQL Server (for production migration)
- Access to FishTalk database

## Quick Setup (Development)

> **Important:** All migration work uses the dedicated PostgreSQL database `aquamind_db_migr_dev` (the `migr_dev` Django alias). Keep the primary `aquamind_db` instance untouched for day-to-day development. Connection details for the FishTalk Docker container and the migration database are documented in `docs/database/migration/ENV_SETUP.md`.

### 1. Set up Migration Database

```bash
# Run Django migrations on the migration database
python manage.py migrate --database=migr_dev
```

### 2. Initialize Master Data

```bash
# Populate geographies, species, users, etc.
python scripts/migration/setup_master_data.py
```

### 3. Test Migration Framework

```bash
# Run with mock data (default)
python scripts/migration/fishtalk_event_engine.py
```

### 4. Orchestrate Phases (dry-run)

```bash
python scripts/migration/migrate.py --dry-run
```

## Production Setup

### 1. Install ODBC Driver

Follow Microsoft's installation guide for your platform:
https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos

### 2. Configure Connection

Update `migration_config.json` with FishTalk database credentials:

```json
{
  "fishtalk": {
    "driver": "{ODBC Driver 18 for SQL Server}",
    "server": "your-fishtalk-server",
    "database": "FishTalk",
    "uid": "your-username",
    "pwd": "your-password",
    "port": 1433
  }
}
```

### 3. Test Connection

```bash
python scripts/migration/test_fishtalk_connection.py
```

### 4. Run Real Migration

```bash
python scripts/migration/fishtalk_event_engine.py
```

## Scripts Overview

- `fishtalk_event_engine.py` - Main migration orchestrator
- `setup_master_data.py` - Initialize reference data
- `clear_migration_db.py` - Reset migration database
- `test_fishtalk_connection.py` - Connection testing utility
- `migration_config.json` - Configuration file

## Configuration

All migration settings are controlled via `migration_config.json`:

- **Database connections**: FishTalk, AVEVA Historian, and AquaMind credentials
- **Multiple SQL sources**: Per-phase overrides (`source_profile`, `source_database`, `source_container`) make it easy to switch infrastructure extracts from FishTalk to `aveva_readonly` without editing code.
- **Migration parameters**: Batch size, date ranges, validation settings
- **Phase control**: Enable/disable specific migration phases
- **Performance tuning**: Parallel workers, memory limits, timeouts

## Troubleshooting

### Migration Database Issues

If you encounter Django migration errors, the system has been fixed and should work cleanly:

```bash
# Fresh migration database setup
python manage.py migrate --database=migr_dev --verbosity=2
```

### Connection Issues

- Verify ODBC driver installation
- Check firewall and network connectivity
- Confirm database credentials in `migration_config.json`

### Data Issues

- Use `--dry-run` mode first
- Check migration logs for validation errors
- Review `migration_config.json` validation settings

## Support

For issues or questions, refer to the main migration documentation:
`aquamind/docs/progress/migration/MIGRATION_FRAMEWORK_IMPLEMENTATION_SUMMARY.md`














