"""diligence-warehouse MCP server.

Tools exposed:
- list_tables() → list of user tables in the warehouse
- describe_table(name) → column names + types
- read_query(sql) → SELECT-only with 10s timeout
- write_narrative(target_id, axis, section_key, body_md, tier) → narrator-only write
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import duckdb
import sqlglot
from sqlglot import exp
from mcp.server.fastmcp import FastMCP


# --- pure handlers (testable without MCP transport) ---

def handle_list_tables(warehouse: Path) -> dict[str, Any]:
    conn = duckdb.connect(str(warehouse), read_only=True)
    try:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
    finally:
        conn.close()
    return {"tables": [{"name": r[0]} for r in rows]}


def handle_describe_table(warehouse: Path, name: str) -> dict[str, Any]:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"invalid table name: {name!r}")
    conn = duckdb.connect(str(warehouse), read_only=True)
    try:
        exists = conn.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_name = ?",
            [name],
        ).fetchone()
        if not exists:
            raise ValueError(f"unknown table: {name!r}")
        rows = conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'main' AND table_name = ? ORDER BY ordinal_position",
            [name],
        ).fetchall()
    finally:
        conn.close()
    return {"name": name, "columns": [{"name": r[0], "type": r[1]} for r in rows]}


# --- MCP wiring ---

mcp = FastMCP("diligence-warehouse")

# Server-wide state set at startup
_warehouse_path: Path | None = None


def _wh() -> Path:
    if _warehouse_path is None:
        raise RuntimeError("warehouse path not set; pass --warehouse on startup")
    return _warehouse_path


@mcp.tool()
def list_tables() -> dict[str, Any]:
    """List all tables in the warehouse."""
    return handle_list_tables(_wh())


@mcp.tool()
def describe_table(name: str) -> dict[str, Any]:
    """Return columns and types for the named table."""
    return handle_describe_table(_wh(), name)


READ_QUERY_TIMEOUT_MS = 10_000


class ReadQueryError(RuntimeError):
    """Raised when read_query rejects a statement."""


def handle_read_query(warehouse: Path, sql: str) -> dict[str, Any]:
    # Parse — single statement only
    try:
        statements = sqlglot.parse(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as e:
        raise ReadQueryError(f"invalid SQL: {e}") from e
    if len(statements) != 1 or statements[0] is None:
        raise ReadQueryError("read_query expects a single statement")
    stmt = statements[0]

    # Allow only Select (CTE-wrapped Select also parses as Select with .with_)
    if not isinstance(stmt, exp.Select):
        kind = type(stmt).__name__
        raise ReadQueryError(f"{kind} is not allowed; read_query is SELECT-only")

    # Reject ATTACH / DETACH / SET / pragma — these may parse as Command
    for node in stmt.walk():
        if isinstance(node[0], (exp.Command, exp.Pragma)):
            raise ReadQueryError(f"{node[0].name} is not allowed in read_query")

    # Execute (DuckDB has no statement_timeout setting; read_only=True prevents writes)
    conn = duckdb.connect(str(warehouse), read_only=True)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
    except duckdb.Error as e:
        raise ReadQueryError(f"query failed: {e}") from e
    finally:
        conn.close()

    return {
        "columns": columns,
        "rows": [list(r) for r in rows],
        "row_count": len(rows),
    }


@mcp.tool()
def read_query(sql: str) -> dict[str, Any]:
    """Execute a SELECT-only DuckDB SQL query against the warehouse.

    Rejects writes, DDL, ATTACH, PRAGMA, and multi-statement input at the SQL parser.
    10-second timeout. Returns columns, rows (list of lists), and row_count.
    """
    return handle_read_query(_wh(), sql)


_VALID_AXES = {"people", "product", "process"}
_VALID_TIERS = {"quick", "full"}


class WriteNarrativeError(RuntimeError): ...


def handle_write_narrative(
    warehouse: Path, *,
    target_id: str, axis: str, section_key: str,
    body_md: str, tier: str,
    generator_version: str | None = None,
) -> dict[str, Any]:
    if axis not in _VALID_AXES:
        raise WriteNarrativeError(f"axis must be one of {sorted(_VALID_AXES)}, got {axis!r}")
    if tier not in _VALID_TIERS:
        raise WriteNarrativeError(f"tier must be one of {sorted(_VALID_TIERS)}, got {tier!r}")
    if not target_id or not section_key or not body_md:
        raise WriteNarrativeError("target_id, section_key, and body_md must be non-empty")

    conn = duckdb.connect(str(warehouse))
    try:
        existing = conn.execute(
            "SELECT 1 FROM narratives WHERE target_id=? AND axis=? AND section_key=?",
            [target_id, axis, section_key],
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE narratives SET body_md=?, generated_at=CURRENT_TIMESTAMP, "
                "generator_version=?, tier=? "
                "WHERE target_id=? AND axis=? AND section_key=?",
                [body_md, generator_version, tier, target_id, axis, section_key],
            )
        else:
            conn.execute(
                "INSERT INTO narratives (target_id, axis, section_key, body_md, "
                "generator_version, tier) VALUES (?, ?, ?, ?, ?, ?)",
                [target_id, axis, section_key, body_md, generator_version, tier],
            )
    finally:
        conn.close()
    return {"ok": True}


@mcp.tool()
def write_narrative(
    target_id: str, axis: str, section_key: str, body_md: str, tier: str,
    generator_version: str = "",
) -> dict[str, Any]:
    """Upsert a narrative row into the warehouse. Narrator-only.

    axis: people | product | process
    tier: quick | full
    """
    return handle_write_narrative(
        _wh(), target_id=target_id, axis=axis, section_key=section_key,
        body_md=body_md, tier=tier,
        generator_version=generator_version or None,
    )


def main() -> None:
    global _warehouse_path
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True, type=Path)
    args = parser.parse_args()
    _warehouse_path = args.warehouse.expanduser().resolve()
    if not _warehouse_path.exists():
        raise SystemExit(f"warehouse not found: {_warehouse_path}")
    mcp.run()


if __name__ == "__main__":
    main()
