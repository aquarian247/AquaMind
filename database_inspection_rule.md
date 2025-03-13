# Database Inspection Rule

## Purpose
This rule ensures that when there is any uncertainty about the database schema, model fields, or relationships, a direct inspection of the database is performed to understand the actual schema deployed in the production environment.

## When to Apply This Rule
Apply this rule in the following scenarios:
1. When encountering field name mismatches or "unexpected keyword arguments" errors
2. When models have been modified but tests are still using old field names
3. Before adding new fields or relationships to ensure compliance with existing schema
4. When TimescaleDB hypertables must be identified for time-series optimizations
5. When debugging validation errors related to model constraints

## Procedure
1. Use the `/workspaces/AquaMind/inspect_db_schema.py` script to examine the full database schema:
   ```bash
   python inspect_db_schema.py
   ```

2. For targeted queries of specific tables, use the `/workspaces/AquaMind/run_sql_query.py` script with a modified query:
   ```bash
   # Edit the script to change the query
   # Then run:
   python run_sql_query.py
   ```

3. Common useful queries:
   - Table structure: `SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'table_name';`
   - Foreign keys: `SELECT conname, conrelid::regclass, confrelid::regclass FROM pg_constraint WHERE confrelid = 'table_name'::regclass::oid;`
   - Hypertables check: `SELECT * FROM timescaledb_information.hypertables;`
   - Indexes: `SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'table_name';`

## Connection Details
Always connect to the database using the connection string defined in `/aquamind/settings.py`:
- Host: timescale-db
- Database: aquamind_db
- User: postgres
- Password: aquapass12345
- Port: 5432

## Important Notes
1. In the Django test environment, tests run against a separate test database which is empty by default - always inspect the production database for reference.
2. For TimescaleDB hypertables, be especially careful with time-series data fields which should conform to TimescaleDB's expectations.
3. Remember that some fields may have validation constraints beyond their database type definitions, implemented at the Django model level.
4. For fields that expect Decimal values, ensure that values are properly converted using `Decimal('value')` rather than float literals.
