"""
Shared configuration helpers for migration scripts.

All migration code should pull connection details from this module rather than
opening migration_config.json manually. This keeps DSNs and credential handling
consistent and allows us to swap targets (e.g. aquamind_db vs
aquamind_db_migr_dev) in one place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).with_name("migration_config.json")


class MigrationConfigError(RuntimeError):
    """Raised when the migration configuration file is missing or invalid."""


def _load_raw_config(path: Path | None = None) -> Dict[str, Any]:
    cfg_path = Path(path) if path else CONFIG_PATH
    if not cfg_path.exists():
        raise MigrationConfigError(
            f"Migration config not found at {cfg_path}. "
            "See docs/progress/migration/ENV_SETUP.md for setup instructions."
        )

    with cfg_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


_CONFIG_CACHE: Dict[str, Any] | None = None


def load_config(path: Path | str | None = None) -> Dict[str, Any]:
    """Load and cache the JSON config (optionally overriding the file path)."""
    global _CONFIG_CACHE, CONFIG_PATH
    if path:
        new_path = Path(path)
        if new_path != CONFIG_PATH:
            CONFIG_PATH = new_path
            _CONFIG_CACHE = None
    if _CONFIG_CACHE is None:
        _CONFIG_CACHE = _load_raw_config(CONFIG_PATH)
    return _CONFIG_CACHE


@dataclass(slots=True)
class SqlServerConfig:
    driver: str
    server: str
    database: str
    uid: str
    pwd: str
    port: int = 1433
    trust_server_certificate: bool = False
    container: str | None = None
    container_port: int | None = None

    def to_odbc_string(self) -> str:
        parts = [
            f"DRIVER={self.driver}",
            f"SERVER={self.server}",
            f"DATABASE={self.database}",
            f"UID={self.uid}",
            f"PWD={self.pwd}",
            f"PORT={self.port}",
        ]
        if self.trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        return ";".join(parts)


@dataclass(slots=True)
class PostgresConfig:
    database: str
    host: str
    port: int
    user: str
    password: str

    def to_sqlalchemy_url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    def to_django_dict(self) -> Dict[str, Any]:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.database,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": str(self.port),
        }


def get_sqlserver_config(key: str = "fishtalk_readonly") -> SqlServerConfig:
    config = load_config()
    if key not in config:
        raise MigrationConfigError(f"Connection profile '{key}' not found.")
    entry = config[key]
    return SqlServerConfig(
        driver=entry["driver"],
        server=entry["server"],
        database=entry["database"],
        uid=entry["uid"],
        pwd=entry["pwd"],
        port=int(entry.get("port", 1433)),
        trust_server_certificate=bool(entry.get("trust_server_certificate", False)),
        container=entry.get("container"),
        container_port=entry.get("container_port"),
    )


def get_postgres_config(key: str = "aquamind") -> PostgresConfig:
    config = load_config()
    if key not in config:
        raise MigrationConfigError(f"Connection profile '{key}' not found.")
    entry = config[key]
    return PostgresConfig(
        database=entry["database"],
        host=entry["host"],
        port=int(entry.get("port", 5432)),
        user=entry["user"],
        password=entry["password"],
    )


def get_sqlserver_connection_string(key: str = "fishtalk_readonly") -> str:
    return get_sqlserver_config(key).to_odbc_string()


def get_postgres_dsn(key: str = "aquamind") -> str:
    return get_postgres_config(key).to_sqlalchemy_url()
