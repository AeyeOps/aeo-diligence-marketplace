"""Walk a git repo's history and yield structured commit records."""
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class FileChange:
    path: str
    lines_added: int
    lines_removed: int


@dataclass
class CommitRecord:
    sha: str
    author_name: str
    author_email: str
    author_date: datetime
    message_first_line: str
    is_merge: bool
    file_changes: list[FileChange] = field(default_factory=list)


_RECORD_SEP = "\x1e"
_FIELD_SEP = "\x1f"
# _RECORD_SEP leads each record so splitting on it yields clean chunks where
# the first line is always the header and subsequent lines are numstat output.
_FORMAT = f"{_RECORD_SEP}%H{_FIELD_SEP}%aN{_FIELD_SEP}%aE{_FIELD_SEP}%aI{_FIELD_SEP}%P{_FIELD_SEP}%s"


def walk_commits(repo: Path) -> Iterator[CommitRecord]:
    """Yield CommitRecord objects for every commit reachable from HEAD.

    Uses git log --numstat --no-renames so per-commit file changes have stable paths.
    """
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
        capture_output=True, text=True,
    )
    if head.returncode != 0:
        return

    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "--no-renames", "--numstat",
         f"--pretty=format:{_FORMAT}"],
        capture_output=True, text=True, check=True,
    )
    raw = proc.stdout
    if not raw.strip():
        return

    for chunk in raw.split(_RECORD_SEP):
        if not chunk.strip():
            continue
        header, _, numstat = chunk.partition("\n")
        sha, name, email, iso_date, parents, msg = header.split(_FIELD_SEP, 5)
        file_changes: list[FileChange] = []
        for line in numstat.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added_s, removed_s, path = parts
            added = int(added_s) if added_s != "-" else 0
            removed = int(removed_s) if removed_s != "-" else 0
            file_changes.append(FileChange(path=path, lines_added=added, lines_removed=removed))
        yield CommitRecord(
            sha=sha,
            author_name=name,
            author_email=email.lower(),
            author_date=datetime.fromisoformat(iso_date),
            message_first_line=msg,
            is_merge=len(parents.split()) > 1,
            file_changes=file_changes,
        )
