"""Base classes for FishTalk data extractors."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
from typing import Any, Dict, List

from scripts.migration.config import get_sqlserver_config


@dataclass
class ExtractionContext:
    profile: str = 'fishtalk_readonly'
    database: str | None = None
    container: str | None = None


class BaseExtractor:
    """Shared helpers for concrete extractors."""

    def __init__(self, context: ExtractionContext | None = None) -> None:
        self.context = context or ExtractionContext()
        self.sql_config = get_sqlserver_config(self.context.profile)
        self.database = self.context.database or self.sql_config.database
        self.container = self.context.container or self.sql_config.container or 'sqlserver'
        self.exec_port = self.sql_config.container_port or self.sql_config.port

    def info(self) -> Dict[str, Any]:
        return {
            'server': self.sql_config.server,
            'database': self.database,
            'profile': self.context.profile,
        }

    def _run_sqlcmd(self, query: str, headers: List[str]) -> List[Dict[str, Any]]:
        sql = f"SET NOCOUNT ON; {query}"
        cmd = [
            'docker', 'exec', self.container, '/opt/mssql-tools18/bin/sqlcmd',
            '-C',
            '-S', f"{self.sql_config.server},{self.exec_port}",
            '-U', self.sql_config.uid,
            '-P', self.sql_config.pwd,
            '-d', self.database,
            '-h', '-1',
            '-W',
            '-w', '65535',
            '-s', '|',
            '-Q', sql,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        rows: List[Dict[str, Any]] = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [self._normalize_value(chunk) for chunk in line.split('|')]
            if len(parts) != len(headers):
                continue
            rows.append(dict(zip(headers, parts)))
        return rows

    @staticmethod
    def _normalize_value(value: str) -> str:
        normalized = value.strip()
        return '' if normalized.upper() == 'NULL' else normalized
