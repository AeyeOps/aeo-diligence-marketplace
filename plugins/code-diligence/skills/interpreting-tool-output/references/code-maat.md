# code-maat

Adam Tornhill's CLI for behavioral code analysis. Reads a git-log dump and emits one CSV per analysis (`revisions`, `coupling`, `entity-ownership`, plus several others code-maat supports natively but we do not persist).

## Warehouse mapping

| code-maat analysis | Warehouse target | Notes |
|---|---|---|
| `revisions` | `file_metrics.revisions` (UPDATE) | Walker also populates this; code-maat overwrites with its own count. |
| `coupling` | `coupling_pairs (source='code-maat')` | Canonical for the Product hidden-coupling card. |
| `entity-ownership` | `file_metrics.top_owner_email`, `file_metrics.top_owner_pct` (UPDATE) | Cross-check against git-fame. |
| `soc`, `communication`, others | not invoked | The pipeline only runs the three analyses listed in `ingest/expensive_tools.py`. |

## Invocation (`src/code_diligence/tools/code_maat.py`)

Two-step shell flow per repo:

1. **Build the log dump** via raw `git log` (not pygit2):

       git -C <repo> log --all --numstat --date=short --no-renames \
           --pretty=format:--%h--%ad--%aN

   `build_log_dump` writes the captured stdout to a temporary file. Timeout: 300s.

2. **Invoke code-maat** once per analysis:

       java -jar <plugin-root>/vendor/code-maat-1.0.4-SNAPSHOT-standalone.jar \
            -l <log_dump> -c git2 -a <analysis>

   The JAR is vendored under `vendor/` at the plugin root. If it's absent, `run_code_maat_analysis` raises `CodeMaatError` with a pointer to `vendor/README.md`. Timeout per analysis: 600s.

## Persistence shape

- **`persist_revisions`** parses `entity,n-revs` CSV and issues per-file `UPDATE file_metrics SET revisions = ?` — it assumes the walker has already inserted the row, so missing rows are silently no-ops.
- **`persist_coupling`** parses `entity,coupled,degree,average-revs`, deletes prior `coupling_pairs` rows for `(repo_id, source='code-maat')`, and inserts new ones with a placeholder `support_pct = degree/100` and `lift = 1.0`. These placeholders are recorded honestly — the Health tab surfaces them as low-confidence values when compared against hercules.
- **`persist_entity_ownership`** parses `entity,author,added,added-pct`, aggregates to the top author per file, and `UPDATE`s `file_metrics.top_owner_email` / `top_owner_pct`. Note the `author` column from code-maat is a display name, not an email — see "Author normalization" below.

## Quirks

- **No JVM tuning.** The wrapper invokes `java -jar` with default heap; there is no `-Xmx` flag or `CODE_MAAT_XMX` env var. On large monorepos that OOM, increase heap via `JAVA_TOOL_OPTIONS` before re-running, or add the flag in `run_code_maat_analysis`.
- **No analysis batching.** The wrapper invokes one JVM per analysis (three JVM starts per repo). Java startup overhead is real; treat code-maat as one of the more expensive tools per repo.
- **Author normalization is name-based.** code-maat sees `--pretty=format:...--%aN` and never sees emails. The `top_owner_email` column gets a display name today; map to canonical email via `identity_map` at the dashboard layer if you need the join.
- **`--no-renames`** is set on the underlying `git log`, matching code-maat's expectation. Renamed files appear as separate entities.

## When to trust it

- **Hidden coupling** — yes, canonical. Cross-check with hercules when available.
- **Ownership** — directional. Trust git-fame for the email-keyed answer.
- **Revisions** — equivalent to the walker; either source is fine, but the walker's value is what stage 3 wrote.
