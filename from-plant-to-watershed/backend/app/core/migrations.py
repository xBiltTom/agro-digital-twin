"""Small, ordered SQL migration runner for the project's pre-Alembic schema."""

from pathlib import Path
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
ADD_COLUMN = re.compile(r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", re.IGNORECASE)
DROP_NOT_NULL = re.compile(r"ALTER\s+TABLE\s+(\w+)\s+ALTER\s+COLUMN\s+(\w+)\s+DROP\s+NOT\s+NULL", re.IGNORECASE)
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
            nullable = DROP_NOT_NULL.fullmatch(sql)
            if nullable and connection.dialect.name == "sqlite":
                _sqlite_drop_not_null(connection, nullable.group(1), nullable.group(2))
                continue
            connection.exec_driver_sql(sql)
        connection.execute(text("INSERT INTO schema_migrations (version) VALUES (:version)"), {"version": path.name})


async def apply_pending_migrations(engine: AsyncEngine) -> None:
    """Apply repository SQL migrations once, without dropping or rewriting rows."""
    async with engine.begin() as connection:
        await connection.run_sync(_apply_migrations_sync)


def _sqlite_drop_not_null(connection: Connection, table: str, column: str) -> None:
    """Apply this additive nullability migration on SQLite without losing rows.

    SQLite has no ``ALTER COLUMN DROP NOT NULL``. Rebuild only the target table
    from its own DDL, preserving its data, indexes and triggers. A legacy table
    without the column is left intact and the migration is still recorded.
    """
    columns = {row[1] for row in connection.exec_driver_sql(f'PRAGMA table_info("{table}")')}
    if column not in columns:
        return
    original = connection.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).scalar_one_or_none()
    if not original:
        return
    column_pattern = re.compile(rf"(\b[\"`\[]?{re.escape(column)}[\"`\]]?\s+[^,]*?)\s+NOT\s+NULL\b", re.IGNORECASE)
    nullable_ddl, replacements = column_pattern.subn(r"\1", original, count=1)
    if not replacements:
        return
    object_rows = connection.exec_driver_sql(
        "SELECT type, sql FROM sqlite_master WHERE tbl_name=? AND type IN ('index','trigger') AND sql IS NOT NULL",
        (table,),
    ).all()
    saved_objects = [sql for _, sql in object_rows]
    temporary = f"{table}_nullable_migration"
    if connection.exec_driver_sql(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (temporary,)
    ).first():
        raise RuntimeError(f"SQLite migration staging table {temporary!r} already exists")
    create_prefix = re.compile(rf"^(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?)[\"`\[]?{re.escape(table)}[\"`\]]?", re.IGNORECASE)
    temporary_ddl, replaced_table = create_prefix.subn(rf"\1{temporary}", nullable_ddl, count=1)
    if not replaced_table:
        raise RuntimeError(f"Could not identify CREATE TABLE for {table!r}")
    names = ", ".join(f'"{name}"' for name in columns)
    connection.exec_driver_sql(f'ALTER TABLE "{table}" RENAME TO "{temporary}_old"')
    connection.exec_driver_sql(temporary_ddl)
    connection.exec_driver_sql(
        f'INSERT INTO "{temporary}" ({names}) SELECT {names} FROM "{temporary}_old"'
    )
    connection.exec_driver_sql(f'DROP TABLE "{temporary}_old"')
    connection.exec_driver_sql(f'ALTER TABLE "{temporary}" RENAME TO "{table}"')
    for ddl in saved_objects:
        connection.exec_driver_sql(ddl)
