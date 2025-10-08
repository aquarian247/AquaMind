# Finance BI Migration Troubleshooting

Use this note when a database shows only `finance_dimcompany` / `finance_dimsite` tables and the Issue 7 views (`vw_fact_harvest`, `vw_intercompany_transactions`) are missing.

## 1. Symptom

```
SELECT * FROM vw_fact_harvest;  -- ERROR: relation does not exist
```

pgAdmin reveals only two finance tables, yet Django migrations should have created the full export stack.

## 2. Root Cause

The database was provisioned outside normal Django migrations. Tables such as `batch_historicalbatchtransfer` already exist, but no entries for the corresponding migrations appear in `django_migrations`. When we run `python manage.py migrate`, Django tries to create those tables again and aborts with `psycopg2.errors.DuplicateTable`, preventing the finance migration (`0004_bi_delivery_views`) from executing.

## 3. Recovery Checklist

1. **Inspect migration history**
   ```sql
   SELECT app, name FROM django_migrations WHERE app = 'batch';
   ```
   If rows are missing for migrations that created existing tables, you have a drifted schema.

2. **Option A – Fresh schema (preferred)**
   * Drop and recreate the database, then run `python manage.py migrate` from scratch.
   * Confirm the views exist via `\dv vw_fact_harvest`.

3. **Option B – Fake missing migrations**
   * Manually mark the already-applied migrations:
     ```bash
     python manage.py migrate batch --fake 0019
     ```
   * Repeat for any other apps that exhibit `DuplicateTable` errors.
   * Re-run `python manage.py migrate finance` to apply `0004_bi_delivery_views`.

4. **Verify**
   ```sql
   SELECT COUNT(*) FROM vw_fact_harvest;
   SELECT COUNT(*) FROM vw_intercompany_transactions;
   ```
   Successful queries confirm the views now exist.

## 4. Preventive Measures

* Always run migrations via Django rather than direct DDL changes.
* Avoid copying tables between environments without synchronising `django_migrations`.
* In CI, add a sanity check that finance views resolve before running BI automation.

Once the schema and migration history are aligned, the Issue 7 migration is idempotent and can be rerun safely.
