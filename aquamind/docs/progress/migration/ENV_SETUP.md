# Deprecated: FishTalk Migration Environment Setup

> **Deprecated:** This document is out of date. See `aquamind/docs/progress/migration/MIGRATION_CANONICAL.md`.

This document captures the canonical local environment for running migration
scripts against the restored FishTalk database and the dedicated AquaMind
migration database. Keeping these details in one place ensures the team has a
repeatable setup that is isolated from day-to-day development work.

## 1. FishTalk SQL Server (Docker)

| Item | Value |
| --- | --- |
| Container name | `sqlserver` |
| Image | `mcr.microsoft.com/mssql/server:2022-latest` |
| Host port | `1433` |
| Internal address | `172.17.0.2` (bridge network) |
| SA password | `2).nV(Ze2TZ8` |

Use the following connection string for ad‑hoc tools (note `TrustServerCertificate=yes`
to avoid SSL validation errors when talking to the Docker container):

```
Driver={ODBC Driver 18 for SQL Server};
Server=localhost,1433;
Database=FishTalk;
Uid=sa;
Pwd=2).nV(Ze2TZ8;
TrustServerCertificate=yes;
```

### 1.1 Read-only Login

Development scripts should use the read-only login to avoid accidental writes.
The login is already created inside the container:

| Account | Type | Password | Access |
| --- | --- | --- | --- |
| `fishtalk_reader` | SQL Login | `FishtalkReader#2025` | `db_datareader` on `FishTalk` |

ODBC example for the read-only account:

```
Driver={ODBC Driver 18 for SQL Server};
Server=localhost,1433;
Database=FishTalk;
Uid=fishtalk_reader;
Pwd=FishtalkReader#2025;
TrustServerCertificate=yes;
```

If you ever need to recreate it, run the snippet below (either via `sqlcmd` in
the Docker container or any SQL Server client):

```
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'fishtalk_reader')
    CREATE LOGIN fishtalk_reader WITH PASSWORD = 'FishtalkReader#2025',
        CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;
GO
USE FishTalk;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'fishtalk_reader')
    CREATE USER fishtalk_reader FOR LOGIN fishtalk_reader;
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.database_role_members drm
    JOIN sys.database_principals dp ON drm.role_principal_id = dp.principal_id
    JOIN sys.database_principals dp2 ON drm.member_principal_id = dp2.principal_id
    WHERE dp.name = 'db_datareader' AND dp2.name = 'fishtalk_reader'
)
    ALTER ROLE db_datareader ADD MEMBER fishtalk_reader;
GO
```

### 1.2 Connectivity Smoke Test

Run the helper script (defaults to the read-only login) to verify ODBC access:

```
python scripts/migration/test_fishtalk_connection.py --conn-key fishtalk_readonly
```

Add `--conn-key fishtalk` to test the `sa` account when necessary.

### 1.3 AVEVA Historian SQL Server (Docker)

| Item | Value |
| --- | --- |
| Container name | `aveva-sql` |
| Image | `mcr.microsoft.com/mssql/server:2022-latest` (AVEVA Historian bundle) |
| Host port | `1435` |
| Internal address | `172.17.0.3` |
| SA password | `2).nV(Ze2TZ8` |

Connection string for host tools (note the custom port):

```
Driver={ODBC Driver 18 for SQL Server};
Server=localhost,1435;
Database=RuntimeDB;
Uid=sa;
Pwd=2).nV(Ze2TZ8;
TrustServerCertificate=yes;
```

> The container bind-mounts `/Users/aquarian247/dev/aveva` at `/host-backup` so we can drop new backup folders or historian block files without rebuilding the image.

### 1.4 Connectivity Smoke Test (AVEVA)

Use the same helper script but pass the new profile:

```
python scripts/migration/test_fishtalk_connection.py --conn-key aveva_readonly
```

This verifies the Historian runtime database is reachable and exposes the expected catalog.

## 2. PostgreSQL Targets

Two PostgreSQL databases exist locally:

| Database | Purpose | Tables |
| --- | --- | --- |
| `aquamind_db` | Day-to-day development | 159 |
| `aquamind_db_migr_dev` | Isolated migration/UAT replay | 154 (clean schema) |

**Important:** All migration scripts **must** use `aquamind_db_migr_dev`. The
main `aquamind_db` database has diverged with additional tables and should
remain untouched for development stability.

### 2.1 Django Database Alias

`aquamind/settings.py` already defines a `migr_dev` alias pointing at
`aquamind_db_migr_dev`. Run migrations with:

```
python manage.py migrate --database=migr_dev
```

### 2.2 psycopg / SQLAlchemy DSN

The canonical DSN for scripts is:

```
postgresql://postgres:adminpass1234@localhost:5432/aquamind_db_migr_dev
```

`scripts/migration/config.py` exposes helpers to build these DSNs so that every
script shares the same source of truth.

## 3. Configuration Files

`scripts/migration/migration_config.json` now contains:

* `fishtalk` – privileged connection (used only for administrative operations)
* `fishtalk_readonly` – default reader account for migrations
* `aveva_readonly` – connects to the Historian `RuntimeDB` through the `aveva-sql` container
* `aquamind` – points to `aquamind_db_migr_dev`

The helper module `scripts/migration/config.py` loads the JSON and builds the
ODBC / PostgreSQL connection strings.

## 4. Historical Replay Harness

- Replay definitions live in `docs/database/migration/replay_sets/`. Start with `sample_batch.json` when wiring new extractors.
- Use `scripts/migration/replay_historical_batch.py path/to/replay.json` to drive the EventEngine with recorded data.
- Replay files can ship alongside test cases to validate migrations end-to-end without regenerating synthetic data.

## 5. Verification Checklist

1. `docker ps` shows the `sqlserver` container running and exposing port `1433`.
2. `docker ps` shows the `aveva-sql` container running and exposing port `1435`.
3. `python scripts/migration/test_fishtalk_connection.py --conn-key fishtalk_readonly`
   prints table counts.
4. `python scripts/migration/test_fishtalk_connection.py --conn-key aveva_readonly` validates the Historian profile.
5. `python scripts/migration/tools/dump_schema.py --label fishtalk` refreshes the FishTalk schema snapshot files; rerun with `--label aveva --profile aveva_readonly --database RuntimeDB --container aveva-sql` to capture the Historian schema.
6. `psql -d aquamind_db_migr_dev -c '\dt'` lists the clean migration tables.
7. `python manage.py migrate --database=migr_dev` completes successfully.

## 6. Sensor Data Source Strategy

Until AVEVA historian access is provisioned, treat FishTalk as the authoritative source for sensor objects and their metadata. All migration scripts should pull sensor definitions from the `sqlserver` container (via the `fishtalk_reader` account) so the names stay aligned with the AVEVA catalog we expect to inherit later. Once AVEVA connectivity is available, rerun `dump_schema.py` plus the sensor extractors to reconcile any naming deltas and update `migration_support.ExternalIdMap` accordingly.

### 6.1 Historian Tag Refresh

- New Django app `apps.historian` exposes the bridging tables `historian_tag`, `historian_tag_history`, and `historian_tag_link`.
- Refresh the AVEVA catalog with `python manage.py load_historian_tags --profile aveva_readonly --using <db_alias>` (run once for `default` and again for `migr_dev` to keep schemas in sync).
- `historian_tag_link` stays empty until the joint mapping exercise; a CSV template will be circulated to the AVEVA team.
- Downstream parsers will look up the linked sensor/container/parameter and write directly into `environmental_environmentalreading`.

Now that the Historian container is online, we can progressively validate each sensor dataset against the new schema snapshots (`aveva_*` files under `docs/database/migration/schema_snapshots/`) before switching extractors to the AVEVA profile.
