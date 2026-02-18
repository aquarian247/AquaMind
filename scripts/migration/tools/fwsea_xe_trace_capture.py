#!/usr/bin/env python3
"""Extended Events capture helper for FWSEA trace-target investigation.

This is migration tooling only. It does not modify FishTalk source data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.migration.extractors.base import BaseExtractor, ExtractionContext


DEFAULT_TRACE_PACK = (
    PROJECT_ROOT
    / "aquamind"
    / "docs"
    / "progress"
    / "migration"
    / "analysis_reports"
    / "2026-02-12"
    / "fw20_reverse_flow_trace_target_pack_2026-02-12.summary.json"
)
DEFAULT_SESSION = "FWSEA_ReverseFlow_Trace"
DEFAULT_EVENT_FILE = "/var/opt/mssql/log/fwsea_reverse_flow_trace"


def normalize(value: str | None) -> str:
    return (value or "").strip()


def quote_sql_string(value: str) -> str:
    return value.replace("'", "''")


def safe_sql_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(
            "Invalid SQL identifier. Use letters, digits, "
            "and underscores only."
        )
    return name


def load_operation_ids(summary_path: Path) -> list[str]:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    ids = [normalize(op_id) for op_id in payload.get("operation_ids") or []]
    return sorted(op_id for op_id in ids if op_id)


def build_event_rows_cte(session_name: str) -> str:
    session = quote_sql_string(session_name)
    return f"""
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
WITH target_data AS (
  SELECT CAST(t.target_data AS xml) AS x
  FROM sys.dm_xe_sessions s
  JOIN sys.dm_xe_session_targets t
    ON s.address = t.event_session_address
  WHERE s.name = N'{session}'
    AND t.target_name = N'ring_buffer'
),
events AS (
  SELECT q.ev.query('.') AS event_xml
  FROM target_data td
  CROSS APPLY td.x.nodes('/RingBufferTarget/event') AS q(ev)
),
event_rows AS (
  SELECT
    event_xml.value('(/event/@name)[1]', 'nvarchar(128)') AS event_name,
    event_xml.value('(/event/@timestamp)[1]', 'datetime2') AS event_time_utc,
    event_xml.value(
      '(/event/action[@name="client_app_name"]/value)[1]',
      'nvarchar(512)'
    )
      AS client_app_name,
    event_xml.value(
      '(/event/action[@name="database_name"]/value)[1]',
      'nvarchar(256)'
    )
      AS database_name,
    event_xml.value(
      '(/event/action[@name="server_principal_name"]/value)[1]',
      'nvarchar(256)'
    )
      AS server_principal_name,
    event_xml.value(
      '(/event/action[@name="sql_text"]/value)[1]',
      'nvarchar(max)'
    ) AS sql_text,
    event_xml.value(
      '(/event/data[@name="statement"]/value)[1]',
      'nvarchar(max)'
    ) AS statement_text,
    event_xml.value(
      '(/event/data[@name="batch_text"]/value)[1]',
      'nvarchar(max)'
    ) AS batch_text
  FROM events
)
"""


def arm_session(
    extractor: BaseExtractor,
    session_name: str,
    event_file_prefix: str,
) -> None:
    session = safe_sql_identifier(session_name)
    event_file = quote_sql_string(event_file_prefix)
    query = f"""
IF EXISTS (
  SELECT 1
  FROM sys.dm_xe_sessions
  WHERE name = N'{session}'
)
BEGIN
  ALTER EVENT SESSION [{session}] ON SERVER STATE = STOP;
END;

IF EXISTS (
  SELECT 1
  FROM sys.server_event_sessions
  WHERE name = N'{session}'
)
BEGIN
  DROP EVENT SESSION [{session}] ON SERVER;
END;

CREATE EVENT SESSION [{session}] ON SERVER
ADD EVENT sqlserver.rpc_completed(
  ACTION(
    sqlserver.client_app_name,
    sqlserver.client_hostname,
    sqlserver.database_name,
    sqlserver.server_principal_name,
    sqlserver.sql_text
  )
),
ADD EVENT sqlserver.sql_batch_completed(
  ACTION(
    sqlserver.client_app_name,
    sqlserver.client_hostname,
    sqlserver.database_name,
    sqlserver.server_principal_name,
    sqlserver.sql_text
  )
)
ADD TARGET package0.event_file(
  SET filename = N'{event_file}',
      max_file_size = (100),
      max_rollover_files = (4)
),
ADD TARGET package0.ring_buffer(
  SET max_memory = (4096)
)
WITH (
  MAX_MEMORY = 4096 KB,
  EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS,
  MAX_DISPATCH_LATENCY = 10 SECONDS,
  TRACK_CAUSALITY = OFF,
  STARTUP_STATE = OFF
);

ALTER EVENT SESSION [{session}] ON SERVER STATE = START;
"""
    extractor._run_sqlcmd(query, ["_"])


def disarm_session(extractor: BaseExtractor, session_name: str) -> None:
    session = safe_sql_identifier(session_name)
    query = f"""
IF EXISTS (
  SELECT 1
  FROM sys.dm_xe_sessions
  WHERE name = N'{session}'
)
BEGIN
  ALTER EVENT SESSION [{session}] ON SERVER STATE = STOP;
END;
"""
    extractor._run_sqlcmd(query, ["_"])


def drop_session(extractor: BaseExtractor, session_name: str) -> None:
    session = safe_sql_identifier(session_name)
    query = f"""
IF EXISTS (
  SELECT 1
  FROM sys.dm_xe_sessions
  WHERE name = N'{session}'
)
BEGIN
  ALTER EVENT SESSION [{session}] ON SERVER STATE = STOP;
END;

IF EXISTS (
  SELECT 1
  FROM sys.server_event_sessions
  WHERE name = N'{session}'
)
BEGIN
  DROP EVENT SESSION [{session}] ON SERVER;
END;
"""
    extractor._run_sqlcmd(query, ["_"])


def session_status(
    extractor: BaseExtractor,
    session_name: str,
) -> dict[str, str]:
    session = safe_sql_identifier(session_name)
    query = f"""
SELECT
  CONVERT(varchar(5), CASE WHEN EXISTS (
    SELECT 1
    FROM sys.server_event_sessions
    WHERE name = N'{session}'
  ) THEN 1 ELSE 0 END) AS exists_session,
  CONVERT(varchar(5), CASE WHEN EXISTS (
    SELECT 1
    FROM sys.dm_xe_sessions
    WHERE name = N'{session}'
  ) THEN 1 ELSE 0 END) AS running_session
"""
    rows = extractor._run_sqlcmd(query, ["exists_session", "running_session"])
    return rows[0] if rows else {"exists_session": "0", "running_session": "0"}


def analyze_capture(
    extractor: BaseExtractor,
    session_name: str,
    operation_ids: list[str],
) -> dict[str, object]:
    cte = build_event_rows_cte(session_name)

    totals = extractor._run_sqlcmd(
        cte
        + """
SELECT
  CONVERT(varchar(20), COUNT(*)) AS total_events,
  CONVERT(varchar(33), MIN(event_time_utc), 126) AS first_event_utc,
  CONVERT(varchar(33), MAX(event_time_utc), 126) AS last_event_utc
FROM event_rows
""",
        ["total_events", "first_event_utc", "last_event_utc"],
    )
    total_row = totals[0] if totals else {}

    app_rows = extractor._run_sqlcmd(
        cte
        + """
SELECT TOP (10)
  ISNULL(NULLIF(client_app_name, ''), '(blank)') AS client_app_name,
  CONVERT(varchar(20), COUNT(*)) AS event_count
FROM event_rows
GROUP BY ISNULL(NULLIF(client_app_name, ''), '(blank)')
ORDER BY COUNT(*) DESC, client_app_name ASC
""",
        ["client_app_name", "event_count"],
    )

    op_hits: list[dict[str, str]] = []
    for op_id in operation_ids:
        op = quote_sql_string(op_id.lower())
        rows = extractor._run_sqlcmd(
            cte
            + f"""
SELECT
  '{op_id}' AS operation_id,
  CONVERT(
    varchar(20),
    COUNT(*)
  ) AS event_count
FROM event_rows
WHERE LOWER(
        ISNULL(sql_text, '')
        + ' '
        + ISNULL(statement_text, '')
        + ' '
        + ISNULL(batch_text, '')
      )
      LIKE '%{op}%'
""",
            ["operation_id", "event_count"],
        )
        op_hits.extend(rows)

    keyword_rows: list[dict[str, str]] = []
    for keyword in (
        "internaldelivery",
        "actionmetadata",
        "populationlink",
        "subtransfers",
        "publictransfers",
        "operations",
    ):
        safe = quote_sql_string(keyword)
        rows = extractor._run_sqlcmd(
            cte
            + f"""
SELECT
  '{keyword}' AS keyword,
  CONVERT(varchar(20), COUNT(*)) AS event_count
FROM event_rows
WHERE LOWER(
        ISNULL(sql_text, '')
        + ' '
        + ISNULL(statement_text, '')
        + ' '
        + ISNULL(batch_text, '')
      )
      LIKE '%{safe}%'
""",
            ["keyword", "event_count"],
        )
        keyword_rows.extend(rows)

    return {
        "totals": total_row,
        "top_client_apps": app_rows,
        "operation_id_hits": op_hits,
        "keyword_hits": keyword_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Arm/disarm/analyze FWSEA Extended Events capture"
    )
    parser.add_argument(
        "action",
        choices=("arm", "disarm", "drop", "status", "analyze"),
        help="XE action to perform",
    )
    parser.add_argument(
        "--sql-profile",
        default="fishtalk",
        help="SQL profile (default: fishtalk / sysadmin)",
    )
    parser.add_argument(
        "--session-name",
        default=DEFAULT_SESSION,
        help="XE session name",
    )
    parser.add_argument(
        "--event-file-prefix",
        default=DEFAULT_EVENT_FILE,
        help="XE event_file target prefix (without .xel)",
    )
    parser.add_argument(
        "--trace-pack-json",
        default=str(DEFAULT_TRACE_PACK),
        help="Trace target summary JSON containing operation_ids",
    )
    parser.add_argument(
        "--summary-json",
        help="Optional summary JSON output path for status/analyze",
    )
    return parser.parse_args()


def main() -> int:  # noqa: C901
    args = parse_args()
    extractor = BaseExtractor(ExtractionContext(profile=args.sql_profile))

    if args.action == "arm":
        arm_session(
            extractor=extractor,
            session_name=args.session_name,
            event_file_prefix=args.event_file_prefix,
        )
        status = session_status(extractor, args.session_name)
        print(
            f"Armed session {args.session_name} "
            f"(exists={status.get('exists_session')} "
            f"running={status.get('running_session')})"
        )
        return 0

    if args.action == "disarm":
        disarm_session(extractor, args.session_name)
        status = session_status(extractor, args.session_name)
        print(
            f"Disarmed session {args.session_name} "
            f"(exists={status.get('exists_session')} "
            f"running={status.get('running_session')})"
        )
        return 0

    if args.action == "drop":
        drop_session(extractor, args.session_name)
        status = session_status(extractor, args.session_name)
        print(
            f"Dropped session {args.session_name} "
            f"(exists={status.get('exists_session')} "
            f"running={status.get('running_session')})"
        )
        return 0

    if args.action == "status":
        status = session_status(extractor, args.session_name)
        if args.summary_json:
            out = Path(args.summary_json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(status, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        print(
            f"Session {args.session_name}: "
            f"exists={status.get('exists_session')} "
            f"running={status.get('running_session')}"
        )
        return 0

    operation_ids = load_operation_ids(Path(args.trace_pack_json))
    summary = analyze_capture(
        extractor=extractor,
        session_name=args.session_name,
        operation_ids=operation_ids,
    )
    if args.summary_json:
        out = Path(args.summary_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    totals = summary["totals"]
    print(
        "Captured events "
        f"total={totals.get('total_events', '0')} "
        f"first={totals.get('first_event_utc') or 'n/a'} "
        f"last={totals.get('last_event_utc') or 'n/a'}"
    )
    print(
        "OperationID hits: "
        + ", ".join(
            f"{row['operation_id']}={row['event_count']}"
            for row in summary["operation_id_hits"]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
