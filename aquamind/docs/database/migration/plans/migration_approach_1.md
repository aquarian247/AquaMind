# AquaMind Migration Approach (Summary)

Audience: IT Lead and AVEVA System Owner

## Goal
Migrate 6–7 years of operational data from FishTalk and 6–7 years of environmental history from AVEVA into AquaMind with full auditability and minimal downtime, avoiding load on AVEVA production APIs. We will pilot on a smaller window first to de‑risk, then scale to the full history.

## Principles (Plain English)
- Chronological, real-world rebuild: We “replay” events (assignments, feedings, growth, mortality) in time order so AquaMind’s audit trail reflects who did what and when.
- Local, read‑only extraction: Work from local backups/restores of FishTalk and AVEVA DBs to eliminate risk and load on production systems.
- Validate before go‑live: Automated counts, variance checks (e.g., biomass/FCR), and sign‑off.

## What We Will Do
1) Prepare and Extract
- Restore AVEVA databases locally (SQL Server/Azure SQL Edge on Mac) read‑only; extract sensor/weather data for the full 6–7 years (pilot first on a smaller slice).
- Extract FishTalk data for 6–7 years of active and historical operations (assignments, feeding, mortality, sampling, users/infrastructure) from a backup/read‑only source; pilot first on a smaller slice.

2) Load and Rebuild Chronology
- Map data to AquaMind’s schema (field mappings agreed in advance).
- Rebuild batch container assignments and then replay events in date order to preserve history (django-simple-history captures audit trail).
- Backfill transfer workflows by analyzing closed→opened assignment pairs to create completed workflows and actions.
- Bulk‑load 6–7 years of AVEVA time‑series into TimescaleDB using chunked COPY loads (efficient, no audit required).

3) Validate and Cutover
- Automated reconciliation: record counts, totals, and tolerances (≤2% for biomass/FCR), spot checks, and dashboards parity.
- Sign‑offs, then a short cutover window (target <48h). Rollback plan prepared.

## Responsibilities & Prerequisites
- IT:
  - Provide read‑only backups/exports for FishTalk and AVEVA (e.g., .bak/.bacpac/CSV) and service accounts for local restore.
  - Allow a local SQL Server/Azure SQL Edge container and disk space for extracts.
  - Approvals for data handling and compliance (PII/security).
- AVEVA Owner:
  - Confirm scope (tables, parameters) and date ranges; provide basic data dictionary and sensor→container/site mapping.
  - Agree on refresh cadence for any near‑real‑time deltas post‑backfill.
- AquaMind Team:
  - Run ETL, mappings, loaders, validations, and produce reconciliation reports and sign‑off packs.

## Indicative Timeline
- Week 1: Environment setup, sample extract, 1‑batch pilot end‑to‑end (small window), validation.
- Weeks 2–3: Scaled backfill of 6–7 years (FishTalk ops + AVEVA time‑series) with rolling validations.
- Week 4: UAT, reconciliations, approvals, and production cutover (<48h).

## Risks & Mitigations
- Production load on AVEVA API → Mitigated by local DB restore; APIs only for future deltas.
- Data consistency → Idempotent loaders, mapping tables (GUID↔IDs), checksums, rollback.
- Downtime → Staged cutover with rollback and optional read‑only dual‑run period.

## Success Criteria
- 100% of targeted 6–7 years migrated (batches, events, and time‑series); ≤2% variance on key operational metrics; full audit trail present; environmental backfill complete; no impact on AVEVA production performance; sign‑offs obtained.

## Next Steps
1) Approvals to receive/read backups and proceed with local restores.
2) Share table lists/mappings; confirm the backfill window.
3) Schedule the 1‑batch pilot window and name technical contacts.
