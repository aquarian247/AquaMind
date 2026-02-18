# FW20 reverse-flow XE capture readiness

Date: 2026-02-12  
Scope: prepare and validate local SQL Server Extended Events capture for reverse-flow blocker cohorts before Activity Explorer trace reconciliation.

## What was implemented

- Added tooling script:
  - `scripts/migration/tools/fwsea_xe_trace_capture.py`
- Script capabilities:
  - `arm` / `disarm` / `drop` / `status` for XE session lifecycle.
  - `analyze` for ring-buffer capture summaries:
    - total event counts and capture window,
    - per-operation-id hit counts from trace pack,
    - keyword hit counts (`internaldelivery`, `actionmetadata`, `populationlink`, etc.),
    - top client-app contributors.

## Permission precheck (source server)

Result for SQL profile `fishtalk`:

- `is_sysadmin=1`
- `can_alter_xe=1`
- `can_view_server_state=1`

This confirms we can run local XE diagnostics without modifying FishTalk source data.

## Exact commands executed

```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_xe_trace_capture.py drop
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_xe_trace_capture.py arm
```

Self-test probe query (read-only, targeted known reverse-flow operations):

```bash
python - <<'PY'
from scripts.migration.extractors.base import BaseExtractor, ExtractionContext
ex=BaseExtractor(ExtractionContext(profile='fishtalk'))
rows=ex._run_sqlcmd("""
SELECT
  CONVERT(varchar(36), OperationID) AS OperationID,
  CONVERT(varchar(10), OperationType) AS OperationType,
  CONVERT(varchar(19), StartTime, 120) AS StartTime
FROM dbo.Operations
WHERE OperationID IN (
  '68E185BA-CCA3-4981-BAF1-0976CC11B8BB',
  '7AE24FFE-A8A6-40DE-B8B4-0776C9274637',
  '112C6EDD-F14B-48EE-AD8E-0AB709BD6728'
)
ORDER BY StartTime
""", ['OperationID','OperationType','StartTime'])
print('rows', len(rows))
PY
```

Capture analysis:

```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_xe_trace_capture.py analyze \
  --summary-json "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_capture_selftest_2026-02-12.summary.json"
```

Session status:

```bash
python /Users/aquarian247/Projects/AquaMind/scripts/migration/tools/fwsea_xe_trace_capture.py status \
  --summary-json "/Users/aquarian247/Projects/AquaMind/aquamind/docs/progress/migration/analysis_reports/2026-02-12/fw20_reverse_flow_xe_session_status_2026-02-12.summary.json"
```

## Self-test result

- XE self-test captured events successfully:
  - `total_events=62`
  - capture window present (`first_event_utc` / `last_event_utc` populated)
  - operation-id hits found for all 6 reverse-flow target operation IDs.
- Session currently:
  - `exists=1`
  - `running=1`

## GUI checkpoint (when to test)

**Now** is the right time for GUI testing for this step:

1. Keep XE session running.
2. In FishTalk Activity Explorer, open the 3 reverse-flow blocker workflows corresponding to:
   - `BF mars 2025`
   - `BF oktober 2025`
   - `Bakkafrost S-21 jan 25`
3. Trigger the same screens/actions used to inspect internal delivery details.
4. After GUI actions are done, run:
   - `fwsea_xe_trace_capture.py analyze` to capture post-GUI SQL signatures.
   - `fwsea_xe_trace_capture.py disarm` to stop session.

## Decision impact

- This step is **GO** for deterministic trace instrumentation.
- No runtime/API/UI changes.
- No migration policy change.
- Reverse-flow cohorts remain excluded from FW->Sea policy evidence until traced SQL confirms otherwise.

