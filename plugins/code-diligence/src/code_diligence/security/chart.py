"""Prepare period-based security chart data from observations or supplied counts."""

import argparse
import json
import resource
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import duckdb
from pydantic import BaseModel, ConfigDict, Field

from code_diligence.security.periods import (
    Period,
    calendar_periods,
    period_floor,
    period_label,
    period_next,
    read_balance,
)
from code_diligence.warehouse.migrations import migrate

Measure = Literal["added", "removed", "opening_backlog", "closing_backlog", "adjustment"]
MOVEMENTS: tuple[Measure, ...] = ("added", "removed", "adjustment")
STOCKS: tuple[Measure, ...] = ("opening_backlog", "closing_backlog")
Basis = Literal["events", "snapshots", "provider_aggregate", "distinct_findings", "mixed"]


class Coverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime | None = None
    end: datetime | None = None
    status: Literal["complete", "partial", "unknown"] = "unknown"


class ChartRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: datetime
    period_end: datetime
    severity: str | None = None
    added: int | None = Field(default=None, ge=0)
    removed: int | None = Field(default=None, ge=0)
    opening_backlog: int | None = Field(default=None, ge=0)
    closing_backlog: int | None = Field(default=None, ge=0)
    adjustment: int | None = None
    coverage: dict[Measure, Coverage] = Field(default_factory=dict)
    opening_from_first_read: bool = False


class Point(BaseModel):
    model_config = ConfigDict(extra="forbid")

    at: datetime
    value: int = Field(ge=0)
    description: str


class RequestedPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime


class ChartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    interval: Literal["day", "week", "month", "quarter", "year", "custom"] = "month"
    range_start: datetime | None = None
    range_end: datetime | None = None
    timezone: str | None = None
    week_start: int = Field(default=0, ge=0, le=6)
    fiscal_year_start_month: int = Field(default=1, ge=1, le=12)
    periods: list[RequestedPeriod] = Field(default_factory=list)
    as_of: datetime | None = None
    source: str | None = None
    scope: str | None = None
    counting_basis: Basis | None = None
    severities: list[str] | None = None
    rows: list[ChartRow] | None = None
    baseline: Point | None = None
    backlog_anchor: Point | None = None
    backlog_estimates: list[Point] = Field(default_factory=list)


def read_chart_input(path: Path) -> ChartInput:
    return ChartInput.model_validate_json(path.expanduser().read_text())


def local_time(value: datetime, zone: ZoneInfo) -> datetime:
    return value.replace(tzinfo=zone) if value.tzinfo is None else value.astimezone(zone)


def utc_time(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC)


def requested_periods(request: ChartInput, start: datetime, end: datetime) -> list[Period]:
    zone = ZoneInfo(request.timezone or "UTC")
    if start >= end:
        raise ValueError("Security chart range_start must be before range_end")
    if request.interval == "custom":
        periods = []
        for supplied in request.periods:
            first, last = local_time(supplied.start, zone), local_time(supplied.end, zone)
            if first >= last:
                raise ValueError("Each custom period must start before it ends")
            if first < end and last > start:
                periods.append(Period(
                    max(first, start), min(last, end),
                    period_label(first, last, "custom", request.fiscal_year_start_month),
                ))
        periods.sort(key=lambda period: period.start)
        if any(first.end > second.start for first, second in pairwise(periods)):
            raise ValueError("Custom security periods must not overlap")
        return periods
    return list(calendar_periods(
        start, end, request.interval,
        week_start=request.week_start, fiscal_start=request.fiscal_year_start_month,
    ))


def native_rows(
    conn: duckdb.DuckDBPyConnection, request: ChartInput, periods: list[Period], as_of: datetime,
) -> list[ChartRow]:
    rows = []
    for period in periods:
        cutoff = min(period.end, as_of + timedelta(microseconds=1))
        if period.start >= cutoff:
            continue
        for balance in read_balance(conn, request.target_id, period.start, cutoff):
            if request.severities is not None and balance["severity"] not in request.severities:
                continue
            last = utc_time(balance["last_read_at"])
            opening = utc_time(balance["opening_at"])
            movement = Coverage(
                start=max(period.start, opening), end=last,
                status="partial" if last < period.end or opening > period.start else "complete",
            )
            rows.append(ChartRow(
                period_start=period.start, period_end=period.end, severity=balance["severity"],
                added=balance["added"], removed=balance["removed"],
                opening_backlog=balance["opening"], closing_backlog=balance["closing"], adjustment=0,
                coverage={
                    "added": movement, "removed": movement, "adjustment": movement,
                    "opening_backlog": Coverage(
                        start=opening, end=opening,
                        status="complete" if opening == period.start else "partial",
                    ),
                    "closing_backlog": Coverage(
                        start=last, end=last,
                        status="complete" if last == period.end else "partial",
                    ),
                },
                opening_from_first_read=balance["opening_from_first_read"],
            ))
    return rows


def normalise_rows(rows: list[ChartRow], zone: ZoneInfo) -> list[ChartRow]:
    result = []
    keys = set()
    for row in rows:
        row = row.model_copy(deep=True)
        row.period_start = local_time(row.period_start, zone)
        row.period_end = local_time(row.period_end, zone)
        if row.period_start >= row.period_end:
            raise ValueError("Each security row must start before it ends")
        key = row.period_start, row.period_end, row.severity
        if key in keys:
            raise ValueError(f"Duplicate security period and severity: {key}")
        keys.add(key)
        for coverage in row.coverage.values():
            if coverage.start is not None:
                coverage.start = local_time(coverage.start, zone)
            if coverage.end is not None:
                coverage.end = local_time(coverage.end, zone)
            if coverage.start is not None and coverage.end is not None and coverage.start > coverage.end:
                raise ValueError("Coverage start must not follow coverage end")
        result.append(row)
    return sorted(result, key=lambda row: (row.period_start, row.period_end, row.severity or ""))


def combined_coverage(rows: list[ChartRow], measure: Measure, period: Period) -> Coverage:
    coverage = [row.coverage.get(measure, Coverage()) for row in rows]
    starts = [item.start for item in coverage if item.start is not None]
    ends = [item.end for item in coverage if item.end is not None]
    contiguous = bool(rows) and rows[0].period_start == period.start and rows[-1].period_end == period.end
    contiguous = contiguous and all(first.period_end == second.period_start for first, second in pairwise(rows))
    complete = contiguous and all(item.status == "complete" for item in coverage)
    status = "complete" if complete else "unknown" if any(item.status == "unknown" for item in coverage) else "partial"
    return Coverage(start=min(starts) if starts else None, end=max(ends) if ends else None, status=status)


def supplied_rows(request: ChartInput, periods: list[Period], as_of: datetime | None) -> list[ChartRow]:
    rows = normalise_rows(request.rows or [], ZoneInfo(request.timezone or "UTC"))
    if as_of is not None:
        for row in rows:
            for measure in (*MOVEMENTS, *STOCKS):
                coverage = row.coverage.get(measure, Coverage())
                at = coverage.end or (row.period_start if measure == "opening_backlog" else row.period_end)
                if at > as_of:
                    setattr(row, measure, None)
                    row.coverage.pop(measure, None)
    selected = [row for row in rows if row.severity is None or request.severities is None or row.severity in request.severities]
    result = []
    for period in periods:
        contained = [row for row in selected if row.period_start >= period.start and row.period_end <= period.end]
        for severity in dict.fromkeys(row.severity for row in contained):
            group = [row for row in contained if row.severity == severity]
            exact = [row for row in group if row.period_start == period.start and row.period_end == period.end]
            if exact:
                if len(group) != 1:
                    raise ValueError("Supplied security rows overlap at the requested interval")
                result.append(exact[0])
                continue
            if any(first.period_end > second.period_start for first, second in pairwise(group)):
                raise ValueError("Supplied security rows overlap at the requested interval")
            combined = ChartRow(period_start=period.start, period_end=period.end, severity=severity)
            if request.counting_basis == "events":
                for measure in MOVEMENTS:
                    available = [row for row in group if getattr(row, measure) is not None]
                    if available:
                        setattr(combined, measure, sum(getattr(row, measure) for row in available))
                        combined.coverage[measure] = combined_coverage(available, measure, period)
            first, last = group[0], group[-1]
            if first.period_start == period.start:
                combined.opening_backlog = first.opening_backlog
                combined.opening_from_first_read = first.opening_from_first_read
                if "opening_backlog" in first.coverage:
                    combined.coverage["opening_backlog"] = first.coverage["opening_backlog"]
            closing = [row for row in group if row.closing_backlog is not None]
            if closing:
                last = closing[-1]
                combined.closing_backlog = last.closing_backlog
                combined.coverage["closing_backlog"] = last.coverage.get("closing_backlog", Coverage()).model_copy()
                if last.period_end != period.end:
                    combined.coverage["closing_backlog"].status = "partial"
            result.append(combined)
    return result


def measure_total(
    rows: list[ChartRow], measure: Measure, severities: list[str], start: datetime, end: datetime,
) -> tuple[int | None, bool]:
    explicit = [row for row in rows if row.severity is None and getattr(row, measure) is not None]
    values = explicit or [row for row in rows if row.severity in severities and getattr(row, measure) is not None]
    if not values or (not explicit and {row.severity for row in values} != set(severities)):
        return None, False
    return (
        sum(getattr(row, measure) for row in values),
        all(
            (coverage := row.coverage.get(measure, Coverage())).status == "complete"
            and (coverage.start is None or coverage.start == start)
            and (coverage.end is None or coverage.end == end)
            for row in values
        ),
    )


def calculated_backlog(
    request: ChartInput, rows: list[ChartRow], periods: list[Period], severities: list[str], as_of: datetime | None,
) -> list[dict]:
    zone = ZoneInfo(request.timezone or "UTC")
    known: dict[datetime, tuple[int, str, bool]] = {}
    if request.backlog_anchor is not None:
        anchor = request.backlog_anchor
        known[local_time(anchor.at, zone)] = (anchor.value, anchor.description, False)
    groups = []
    for period in periods:
        group = [row for row in rows if row.period_start == period.start and row.period_end == period.end]
        end = min(period.end, as_of) if as_of is not None else period.end
        if end <= period.start:
            continue
        for measure, at in zip(STOCKS, (period.start, end), strict=True):
            value, complete = measure_total(group, measure, severities, at, at)
            if value is not None and complete:
                known[at] = (value, "Supplied backlog", False)
        movements = [measure_total(group, measure, severities, period.start, end) for measure in MOVEMENTS]
        added, removed, adjustment = (value for value, _ in movements)
        delta = None
        if (
            request.counting_basis not in {"provider_aggregate", "mixed"}
            and added is not None and removed is not None and adjustment is not None
            and all(full for _, full in movements)
        ):
            delta = added - removed + adjustment
        groups.append((period, end, group, delta))
    if request.baseline is not None:
        known.setdefault(
            local_time(request.baseline.at, zone),
            (request.baseline.value, request.baseline.description, False),
        )
    for period, end, _, delta in reversed(groups):
        if delta is not None and end in known and period.start not in known:
            known[period.start] = (known[end][0] - delta, "Calculated from supplied movements", True)
    for period, end, _, delta in groups:
        if delta is not None and period.start in known and end not in known:
            known[end] = (known[period.start][0] + delta, "Calculated from supplied movements", True)
    points = []
    for period, end, group, delta in groups:
        value, _ = measure_total(group, "closing_backlog", severities, end, end)
        if value is None and end in known:
            value, description, calculated = known[end]
            points.append({
                "period_start": period.start.isoformat(), "period_end": period.end.isoformat(),
                "at": end.isoformat(), "value": value, "description": description,
                "calculated": calculated,
            })
        if delta is not None and period.start in known and end in known:
            difference = known[end][0] - known[period.start][0] - delta
            if difference:
                points.append({
                    "period_start": period.start.isoformat(), "period_end": period.end.isoformat(),
                    "balance_difference": difference,
                })
    return points


def prepare_chart(conn: duckdb.DuckDBPyConnection, request: ChartInput) -> dict:
    request = request.model_copy(deep=True)
    native = request.rows is None
    first = last = None
    if request.rows is None:
        first, last = conn.execute(
            "SELECT min(read_at), max(read_at) FROM security_reads WHERE target_id = ?", [request.target_id],
        ).fetchall()[0]
        zone_row = conn.execute(
            "SELECT month_timezone FROM security_monthly WHERE target_id = ? LIMIT 1", [request.target_id],
        ).fetchone()
        request.timezone = request.timezone or (zone_row[0] if zone_row else "UTC")
        request.source = "AWS Inspector"
        request.counting_basis = "snapshots"
        scopes = conn.execute(
            "SELECT DISTINCT scope, fix_available FROM security_reads WHERE target_id = ? ORDER BY scope, fix_available",
            [request.target_id],
        ).fetchall()
        request.scope = request.scope or "; ".join(
            f"Active findings. {f'Fix availability: {fixes}' if fixes else 'Any fix availability'}. "
            f"{f'Resource prefixes: {prefixes}' if prefixes else 'All resources'}"
            for prefixes, fixes in scopes
        )
        if request.severities is None:
            request.severities = [row[0] for row in conn.execute(
                "SELECT DISTINCT unnest(string_split(severities, ',')) AS severity "
                "FROM security_reads WHERE target_id = ? ORDER BY severity", [request.target_id],
            ).fetchall()]
        first, last = utc_time(first) if first is not None else None, utc_time(last) if last is not None else None
    else:
        request.timezone = request.timezone or "UTC"
        if request.counting_basis is None or request.source is None or request.scope is None:
            raise ValueError("Supplied security rows require counting_basis, source, and scope")
        request.rows = normalise_rows(request.rows, ZoneInfo(request.timezone))
        if request.rows:
            first = min(row.period_start for row in request.rows)
            last = max(row.period_end for row in request.rows)
        if request.severities is None:
            request.severities = list(dict.fromkeys(row.severity for row in request.rows if row.severity is not None))
    zone = ZoneInfo(request.timezone or "UTC")
    for point in (request.baseline, request.backlog_anchor, *request.backlog_estimates):
        if point is not None:
            point.at = local_time(point.at, zone)
            if first is not None and last is not None:
                first, last = min(first, point.at), max(last, point.at)
    as_of = local_time(request.as_of, zone) if request.as_of is not None else local_time(last, zone) if last else None
    if native and last is not None and as_of is not None:
        as_of = min(as_of, local_time(last, zone))
    if as_of is not None:
        if request.baseline is not None and request.baseline.at > as_of:
            request.baseline = None
        if request.backlog_anchor is not None and request.backlog_anchor.at > as_of:
            request.backlog_anchor = None
        request.backlog_estimates = [point for point in request.backlog_estimates if point.at <= as_of]
    start = local_time(request.range_start, zone) if request.range_start is not None else None
    end = local_time(request.range_end, zone) if request.range_end is not None else None
    point_times = [
        point.at for point in (request.baseline, request.backlog_anchor, *request.backlog_estimates)
        if point is not None
    ]
    if request.interval == "custom":
        if not request.periods:
            raise ValueError("Custom security intervals require periods")
        start = start or min(local_time(period.start, zone) for period in request.periods)
        end = end or max(local_time(period.end, zone) for period in request.periods)
    elif first is not None and last is not None:
        start = start or period_floor(
            local_time(first, zone), request.interval, request.week_start, request.fiscal_year_start_month,
        )
        end = end or (
            period_next(period_floor(local_time(last, zone), request.interval, request.week_start,
                                     request.fiscal_year_start_month), request.interval)
            if native else local_time(last, zone)
        )
    elif point_times:
        start = start or period_floor(
            min(point_times), request.interval, request.week_start, request.fiscal_year_start_month,
        )
        end = end or period_next(
            period_floor(max(point_times), request.interval, request.week_start, request.fiscal_year_start_month),
            request.interval,
        )
    periods = requested_periods(request, start, end) if start is not None and end is not None else []
    if native:
        rows = native_rows(conn, request, periods, as_of) if as_of is not None else []
        rows = normalise_rows(rows, zone)
    else:
        rows = supplied_rows(request, periods, as_of)
    calculated = calculated_backlog(request, rows, periods, request.severities, as_of)
    return {
        "target_id": request.target_id, "source": request.source, "scope": request.scope,
        "counting_basis": request.counting_basis, "interval": request.interval, "timezone": request.timezone,
        "range_start": start.isoformat() if start else None, "range_end": end.isoformat() if end else None,
        "as_of": as_of.isoformat() if as_of else None, "severities": request.severities,
        "periods": [{"start": p.start.isoformat(), "end": p.end.isoformat(), "label": p.label} for p in periods],
        "rows": [row.model_dump(mode="json", exclude_none=True) for row in rows],
        "calculated_backlog": calculated,
        "baseline": request.baseline.model_dump(mode="json") if request.baseline else None,
        "backlog_anchor": request.backlog_anchor.model_dump(mode="json") if request.backlog_anchor else None,
        "backlog_estimates": [point.model_dump(mode="json") for point in request.backlog_estimates],
    }


def write_chart_data(conn: duckdb.DuckDBPyConnection, output: Path, targets: list[str], inputs: list[Path]) -> None:
    requests = {}
    for path in inputs:
        request = read_chart_input(path)
        if request.target_id not in targets:
            raise ValueError(f"Security chart target is not in this warehouse: {request.target_id}")
        if request.target_id in requests:
            raise ValueError(f"More than one security chart input for target: {request.target_id}")
        requests[request.target_id] = request
    charts = {target: prepare_chart(conn, requests.get(target, ChartInput(target_id=target))) for target in targets}
    output.write_text(json.dumps(charts, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-id")
    parser.add_argument("--security-chart", action="append", type=Path, default=[])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="code-diligence-chart-") as temporary:
        warehouse = Path(temporary) / "warehouse.duckdb"
        shutil.copyfile(args.warehouse.expanduser(), warehouse)
        with duckdb.connect(str(warehouse)) as conn:
            migrate(conn)
            targets = [row[0] for row in conn.execute("SELECT target_id FROM targets ORDER BY target_id").fetchall()]
            if args.target_id is not None:
                if args.target_id not in targets:
                    raise ValueError(f"Target is not in this warehouse: {args.target_id}")
                targets = [args.target_id]
            write_chart_data(conn, args.output, targets, args.security_chart)
    print(json.dumps({
        "output": str(args.output), "targets": targets,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }))


if __name__ == "__main__":
    main()
