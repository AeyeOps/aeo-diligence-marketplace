# git-of-theseus

Erik Bernhardsson's cohort-survival analyzer. Answers: "Of the LOC introduced in cohort C, how many lines are still in HEAD?"

## Warehouse mapping

| git-of-theseus output | Warehouse table | Notes |
|---|---|---|
| `cohorts.json` (latest snapshot row) | `code_age_buckets (repo_id, bucket_start_year, surviving_loc, deleted_loc)` | Canonical for Product `code_aging_chart` on quick tier; hercules supplies the time-series view |

## Invocation (`src/code_diligence/tools/git_of_theseus.py`)

The wrapper shells out to:

    git-of-theseus-analyze <repo> --outdir <tmpdir>

- `--outdir` directs git-of-theseus to write its analysis artifacts (we only consume `cohorts.json`) to a `tempfile.TemporaryDirectory` that the wrapper cleans up.
- No other flags are set. In particular, `--follow-renames` is **not** passed — renames mid-life appear as deleted-then-added across cohort labels.
- Timeout: 600s. Non-zero exit raises `GitOfTheseusError`; `isolated()` converts it to a `tool_failures` row of class `runtime`.

## What it does

For each historical snapshot, git-of-theseus computes how much of each prior cohort's introduction is still present. The wrapper reads only the **last** row of `cohorts.json["y"]` — the most recent snapshot — and zips it against `cohorts.json["labels"]`.

## Persistence shape

`parse_cohorts_json` normalizes each label to a 4-digit year (`int(str(label)[:4])`). Labels that don't start with a parseable year are silently skipped. `persist_git_of_theseus` deletes prior `code_age_buckets` rows for the repo and re-inserts; `deleted_loc` is currently always written as `0` (the latest snapshot only carries surviving LOC).

## Quirks

- **Latest snapshot only.** The wrapper deliberately ignores the time series — use hercules for evolution.
- **Expensive on deep history.** git-of-theseus checks out one snapshot per cohort interval. Repos with 10+ year history take minutes.
- **Renames not followed.** Because the wrapper omits `--follow-renames`, a renamed file's LOC can appear split across cohorts. Trust totals; treat per-cohort fine detail with caution.

## Common confusion

"Why doesn't this match `cloc`?" — usually because of:

- Generated files included in one but not the other
- `.gitignore` differences between the snapshot git-of-theseus walked and the working tree
- Binary-file detection differences

Trust git-of-theseus for cohort breakdown; trust the walker's `commits_fact.lines_added/lines_removed` for running totals.

## Wrapper

`src/code_diligence/tools/git_of_theseus.py`. Binary expected on PATH as `git-of-theseus-analyze`. Tests under `tests/tools/test_git_of_theseus.py` skip cleanly when the binary is absent.
