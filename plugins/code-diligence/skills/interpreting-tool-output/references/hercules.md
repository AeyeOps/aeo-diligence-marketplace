# hercules

src-d's git-history analyzer. Emits per-tick per-vintage surviving-LOC matrices used to build the burndown time series.

## Warehouse mapping

| hercules output | Warehouse table | Notes |
|---|---|---|
| `Burndown.project.matrix` | `burndown_series (repo_id, snapshot_at, vintage_year, surviving_loc)` | Canonical for the Product `burndown_over_time` card |

Coupling and dev-edge outputs from hercules are not persisted — code-maat is canonical for `coupling_pairs`, and the walker is canonical for `commit_file_authors`.

## Invocation (`src/code_diligence/tools/hercules.py`)

The wrapper shells out to:

    hercules --burndown --burndown-people --yaml <repo>

- `--burndown` enables the burndown analysis.
- `--burndown-people` adds per-author burndown alongside the project matrix.
- `--yaml` forces YAML output on stdout; the wrapper parses it with `yaml.safe_load`.
- Timeout: 600s. On non-zero exit it raises `HerculesError`; the `isolated()` envelope in the pipeline converts that to a `tool_failures` row of class `runtime` and the repo moves on.

The wrapper pins to `HERCULES_VERSION = "10.7.2"` for documentation purposes; the binary on PATH must be a compatible release.

## Why a time series, not a snapshot

git-of-theseus and hercules overlap, but:

- git-of-theseus returns the **latest** snapshot's per-vintage surviving LOC → `code_age_buckets`
- hercules returns **every tick's** matrix → `burndown_series`

Use git-of-theseus for the static "how old is the code now" chart and hercules for "how is the code base aging over time." The dashboard prefers hercules when present.

## Persistence shape

`persist_burndown` reads `Burndown.project.matrix` (a list-of-lists indexed `[tick_idx][vintage_idx]`) plus the project's `granularity` and `sampling` (days-per-tick) values, and emits one row per non-zero `(tick, vintage)` cell. Zeros are skipped to keep the table sparse. Existing `burndown_series` rows for the repo are deleted first — the wrapper is idempotent on re-run.

## Caveats

- The wrapper passes a repo path directly; no git-log dump is required (unlike code-maat).
- Vintage resolution is per-tick (typically 30-day buckets), normalized to `vintage_year` on persist.
- Files renamed via `git mv` follow blame across renames inside hercules itself.
