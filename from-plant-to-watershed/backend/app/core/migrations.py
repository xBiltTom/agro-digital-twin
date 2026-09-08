"""Small, ordered SQL migration runner for the project's pre-Alembic schema."""

from pathlib import Path
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
ADD_COLUMN = re.compile(r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", re.IGNORECASE)
SCHEMA_MIGRATIONS_DDL = (
    "CREATE TABLE IF NOT EXISTS schema_migrations "
    "(version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
)


def _apply_migrations_sync(connection: Connection) -> None:
    connection.exec_driver_sql(SCHEMA_MIGRATIONS_DDL)
    applied = {row[0] for row in connection.exec_driver_sql("SELECT version FROM schema_migrations")}
    inspector = inspect(connection)
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        existing_columns = {table: {column["name"] for column in inspector.get_columns(table)} for table in inspector.get_table_names()}
        for statement in path.read_text(encoding="utf-8").split(";"):
            sql = statement.strip()
            if not sql:
                continue
            match = ADD_COLUMN.search(sql)
            if match and match.group(2) in existing_columns.get(match.group(1), set()):
                continue
            connection.exec_driver_sql(sql)
        connection.execute(text("INSERT INTO schema_migrations (version) VALUES (:version)"), {"version": path.name})


async def apply_pending_migrations(engine: AsyncEngine) -> None:
    """Apply repository SQL migrations once, without dropping or rewriting rows."""
    async with engine.begin() as connection:
        await connection.run_sync(_apply_migrations_sync)
