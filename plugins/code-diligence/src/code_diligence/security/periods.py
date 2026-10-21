"""Calendar periods and finding balances computed from saved observations."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb


@dataclass(frozen=True)
class Period:
    start: datetime
    end: datetime
    label: str


def month_shift(value: datetime, months: int) -> datetime:
    year, month = divmod(value.year * 12 + value.month - 1 + months, 12)
    return value.replace(year=year, month=month + 1, day=1)


def period_floor(value: datetime, interval: str, week_start: int, fiscal_start: int) -> datetime:
    start = value.replace(hour=0, minute=0, second=0, microsecond=0)
    if interval == "day":
        return start
    if interval == "week":
        return start - timedelta(days=(start.weekday() - week_start) % 7)
    start = start.replace(day=1)
    if interval == "month":
        return start
    offset = (start.month - fiscal_start) % 12
    if interval == "quarter":
        return month_shift(start, -(offset % 3))
    if interval == "year":
        return month_shift(start, -offset)
    raise ValueError(f"Unknown calendar interval: {interval}")


def period_next(value: datetime, interval: str) -> datetime:
    if interval == "day":
        return value + timedelta(days=1)
    if interval == "week":
        return value + timedelta(days=7)
    return month_shift(value, {"month": 1, "quarter": 3, "year": 12}[interval])


def period_label(start: datetime, end: datetime, interval: str, fiscal_start: int) -> str:
    if interval == "month":
        return start.strftime("%b %Y")
    if interval == "quarter":
        quarter = ((start.month - fiscal_start) % 12) // 3 + 1
        return f"Q{quarter} {start.year}" if fiscal_start == 1 else f"Q{quarter} · {start:%b %Y}"
    if interval == "year":
        return str(start.year) if fiscal_start == 1 else f"{start:%b %Y} to {end - timedelta(microseconds=1):%b %Y}"
    if interval == "day":
        return start.strftime("%b %d, %Y")
    return f"{start:%b %d} to {end - timedelta(microseconds=1):%b %d, %Y}"


def calendar_periods(
    start: datetime,
    end: datetime,
    interval: str,
    *,
    week_start: int = 0,
    fiscal_start: int = 1,
) -> Iterator[Period]:
    cursor = period_floor(start, interval, week_start, fiscal_start)
    while cursor < end:
        next_cursor = period_next(cursor, interval)
        yield Period(
            max(start, cursor),
            min(end, next_cursor),
            period_label(cursor, next_cursor, interval, fiscal_start),
        )
        cursor = next_cursor


def read_balance(
    conn: duckdb.DuckDBPyConnection, target_id: str, start: datetime, end: datetime,
) -> list[dict]:
    """Count distinct membership changes within a period without loading finding sets into Python."""
    result = conn.execute(
        """
        WITH covering AS (
            SELECT read_at, source, unnest(string_split(severities, ',')) AS severity
            FROM security_reads WHERE target_id = ?
        ), observations AS (
            SELECT read_at, source, finding_id, severity
            FROM security_observations WHERE target_id = ?
        ), prior AS (
            SELECT *, row_number() OVER (
                PARTITION BY severity ORDER BY read_at DESC, source DESC
            ) AS position
            FROM covering WHERE read_at < ?
        ), current AS (
            SELECT *,
                row_number() OVER (PARTITION BY severity ORDER BY read_at, source) AS first_position,
                row_number() OVER (PARTITION BY severity ORDER BY read_at DESC, source DESC) AS last_position
            FROM covering WHERE read_at >= ? AND read_at < ?
        ), bounds AS (
            SELECT first.severity,
                coalesce(prior.read_at, first.read_at) AS opening_at,
                coalesce(prior.source, first.source) AS opening_source,
                first.read_at AS first_read_at, last.read_at AS last_read_at,
                last.source AS last_source, prior.read_at IS NULL AS opening_from_first_read
            FROM current first
            JOIN current last ON first.severity = last.severity AND last.last_position = 1
            LEFT JOIN prior ON prior.severity = first.severity AND prior.position = 1
            WHERE first.first_position = 1
        ), opening AS (
            SELECT DISTINCT b.severity, o.finding_id FROM bounds b
            JOIN observations o ON o.read_at = b.opening_at
                AND o.source = b.opening_source AND o.severity = b.severity
        ), seen AS (
            SELECT DISTINCT c.severity, o.finding_id FROM current c
            JOIN observations o ON o.read_at = c.read_at
                AND o.source = c.source AND o.severity = c.severity
        ), closing AS (
            SELECT DISTINCT b.severity, o.finding_id FROM bounds b
            JOIN observations o ON o.read_at = b.last_read_at
                AND o.source = b.last_source AND o.severity = b.severity
        ), added AS (
            SELECT * FROM seen EXCEPT SELECT * FROM opening
        ), present AS (
            SELECT * FROM opening UNION SELECT * FROM seen
        ), removed AS (
            SELECT * FROM present EXCEPT SELECT * FROM closing
        )
        SELECT b.*,
            (SELECT count(*) FROM opening o WHERE o.severity = b.severity) AS opening,
            (SELECT count(*) FROM added a WHERE a.severity = b.severity) AS added,
            (SELECT count(*) FROM removed r WHERE r.severity = b.severity) AS removed,
            (SELECT count(*) FROM closing c WHERE c.severity = b.severity) AS closing
        FROM bounds b ORDER BY b.severity
        """,
        [
            target_id, target_id, start.astimezone(UTC).replace(tzinfo=None),
            start.astimezone(UTC).replace(tzinfo=None), end.astimezone(UTC).replace(tzinfo=None),
        ],
    )
    columns = [column[0] for column in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
