"""Record AWS Inspector findings that have an available fix and their monthly balance."""
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import boto3
import duckdb

from code_diligence.settings.schema import AwsInspectorSource

SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL", "UNTRIAGED")
FIXABLE = ("YES", "PARTIAL")
MONTHS = 6
_SNAPSHOT_NAME = re.compile(r"account-findings-(\d{8}T\d{6}Z)\.json")


@dataclass(frozen=True)
class Read:
    read_at: datetime
    source: str
    severities: tuple[str, ...]
    findings: dict[str, str]


def _resource_names(finding: dict) -> list[str]:
    names = []
    for resource in finding.get("resources", []):
        details = resource.get("details", {})
        names += [
            resource.get("id", ""),
            details.get("awsEcrContainerImage", {}).get("repositoryName", ""),
            details.get("awsLambdaFunction", {}).get("functionName", ""),
            resource.get("tags", {}).get("Name", ""),
        ]
    return [name for name in names if name]


def _qualifying(findings: list[dict], prefixes: tuple[str, ...]) -> dict[str, str]:
    """Active findings with a fix available on in-scope resources, keyed by finding id."""
    return {
        finding["findingArn"].rsplit("/", 1)[-1]: finding["severity"]
        for finding in findings
        if finding.get("status") == "ACTIVE"
        and finding.get("fixAvailable") in FIXABLE
        and (not prefixes or any(name.startswith(prefixes) for name in _resource_names(finding)))
    }


def pull_inspector(profile: str, region: str, prefixes: tuple[str, ...]) -> Read:
    client = boto3.Session(profile_name=profile, region_name=region).client("inspector2")
    read_at = datetime.now(UTC)
    criteria = {
        "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}],
        "fixAvailable": [{"comparison": "EQUALS", "value": value} for value in FIXABLE],
    }
    findings = [
        finding
        for page in client.get_paginator("list_findings").paginate(filterCriteria=criteria)
        for finding in page["findings"]
    ]
    return Read(read_at, "inspector", SEVERITIES, _qualifying(findings, prefixes))


def snapshot_reads(dirs: list[str], known: set[datetime], prefixes: tuple[str, ...]) -> Iterator[Read]:
    """Saved snapshots not yet recorded, each a JSON file of Inspector findings named by its UTC read time."""
    for directory in dirs:
        for path in sorted(Path(directory).expanduser().glob("account-findings-*.json")):
            match = _SNAPSHOT_NAME.fullmatch(path.name)
            if match is None:
                raise ValueError(f"unexpected snapshot file name: {path}")
            read_at = datetime.strptime(match[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            if read_at.replace(tzinfo=None) in known:
                continue
            payload = json.loads(path.read_text())
            yield Read(read_at, "snapshot", tuple(payload["severities"]), _qualifying(payload["findings"], prefixes))


def _persist_read(conn: duckdb.DuckDBPyConnection, *, target_id: str, scope: str, read: Read) -> None:
    read_at = read.read_at.astimezone(UTC).replace(tzinfo=None)
    conn.execute(
        "INSERT INTO security_reads (target_id, read_at, source, severities, scope) VALUES (?, ?, ?, ?, ?)",
        [target_id, read_at, read.source, ",".join(read.severities), scope],
    )
    if read.findings:
        conn.executemany(
            "INSERT INTO security_observations (target_id, read_at, source, finding_id, severity) VALUES (?, ?, ?, ?, ?)",
            [(target_id, read_at, read.source, finding_id, severity) for finding_id, severity in read.findings.items()],
        )


def _month_windows(now: datetime, zone: ZoneInfo) -> list[tuple[date, datetime, datetime]]:
    """The last MONTHS calendar months in the zone, as UTC-naive [start, end) bounds."""
    local = now.astimezone(zone)
    months = []
    year, month = local.year, local.month
    for _ in range(MONTHS):
        months.append((year, month))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    months.sort()
    bounds = [datetime(y, m, 1, tzinfo=zone).astimezone(UTC).replace(tzinfo=None) for y, m in months]
    return [
        (date(y, m, 1), start, end)
        for (y, m), start, end in zip(months, bounds, [*bounds[1:], datetime.max], strict=True)
    ]


def write_monthly_balance(conn: duckdb.DuckDBPyConnection, *, target_id: str, now: datetime, zone: ZoneInfo) -> None:
    """Per month and severity: open at the opening read, newly seen, no longer open, and open at the last read."""
    reads = conn.execute(
        "SELECT read_at, source, severities FROM security_reads WHERE target_id = ? ORDER BY read_at, source",
        [target_id],
    ).fetchall()
    observed: dict[tuple[datetime, str], dict[str, str]] = {}
    for read_at, source, finding_id, severity in conn.execute(
        "SELECT read_at, source, finding_id, severity FROM security_observations WHERE target_id = ?", [target_id]
    ).fetchall():
        observed.setdefault((read_at, source), {})[finding_id] = severity
    conn.execute("DELETE FROM security_monthly WHERE target_id = ?", [target_id])
    windows = _month_windows(now, zone)
    rows = []
    for severity in SEVERITIES:
        covering = [
            (read_at, {fid for fid, sev in observed.get((read_at, source), {}).items() if sev == severity})
            for read_at, source, severities in reads
            if severity in severities.split(",")
        ]
        for month, start, end in windows:
            in_month = [(read_at, ids) for read_at, ids in covering if start <= read_at < end]
            if not in_month:
                continue
            before = [ids for read_at, ids in covering if read_at < start]
            opening = before[-1] if before else in_month[0][1]
            seen = set().union(*(ids for _, ids in in_month))
            closing = in_month[-1][1]
            rows.append((
                target_id, month, severity, len(opening), len(seen - opening),
                len((opening | seen) - closing), len(closing), in_month[0][0], in_month[-1][0], not before, zone.key,
            ))
    if rows:
        conn.executemany(
            "INSERT INTO security_monthly (target_id, month, severity, opening, opened, removed, closing, "
            "first_read_at, last_read_at, opening_from_first_read, month_timezone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def collect_inspector(conn: duckdb.DuckDBPyConnection, *, target_id: str, source: AwsInspectorSource) -> None:
    """Add unrecorded snapshots and a live Inspector read, then recompute the monthly balance."""
    assert source.profile is not None and source.region is not None
    prefixes = tuple(source.resource_prefixes)
    scope = ",".join(sorted(prefixes))
    conn.execute(
        "DELETE FROM security_observations WHERE (target_id, read_at, source) IN "
        "(SELECT target_id, read_at, source FROM security_reads WHERE target_id = ? AND scope <> ?)",
        [target_id, scope],
    )
    conn.execute("DELETE FROM security_reads WHERE target_id = ? AND scope <> ?", [target_id, scope])
    known = {
        row[0] for row in conn.execute(
            "SELECT read_at FROM security_reads WHERE target_id = ? AND source = 'snapshot'", [target_id]
        ).fetchall()
    }
    for read in snapshot_reads(source.snapshot_dirs, known, prefixes):
        _persist_read(conn, target_id=target_id, scope=scope, read=read)
    _persist_read(conn, target_id=target_id, scope=scope, read=pull_inspector(source.profile, source.region, prefixes))
    write_monthly_balance(conn, target_id=target_id, now=datetime.now(UTC), zone=ZoneInfo(source.timezone))
