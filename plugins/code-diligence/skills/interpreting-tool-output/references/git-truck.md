# git-truck

`git-truck/git-truck` v3 npm package. v3 is a long-running Express + React Router web app, not a one-shot CLI exporter — `--headless` only suppresses the browser auto-open. The wrapper drives the server, waits for it to finish analysis, then reads the DuckDB cache directly.

## Warehouse mapping

| git-truck output | Warehouse table | Notes |
|---|---|---|
| `getDominantAuthorPerFile` (extracted SQL) over the per-repo DuckDB cache | `ownership_share (source='git-truck')` | Cross-check only — author keys are name-based, not email-based |

## Invocation (`src/code_diligence/tools/git_truck.py`)

The wrapper performs six ordered steps:

1. **Spawn** `npx -y git-truck@3.3.0 --headless` with `cwd=<realpath(repo)>` and `start_new_session=True` so it owns its process group. The positional repo argv is ignored by v3; the server uses `process.cwd()`.
2. **Drain stdout** to find the Express listening port via the `http://localhost:NNNNN` regex. Timeout: 120s. If the process exits before printing a port, raise `GitTruckError` with the log tail.
3. **Kick `/view`** on a daemon thread (`_kick_view`) — `viewMiddleware` loads the analysis lazily and React Router v7 aborts the loader when the client disconnects, so we keep the request open with a long timeout while the main thread polls for completion.
4. **Poll `$TMPDIR/git-truck-cache/metadata.json`** until `completions["<absRepoPath>---<branch>"]` appears. Timeout: 180s. `absRepoPath` uses `os.path.realpath` because macOS resolves a subprocess's `cwd` through `/private/var/folders/...`, and git-truck stores the completion key under the resolved form — without the realpath, polling never finds the key.
5. **SIGTERM the process group** (`os.killpg`), wait up to 10s, then SIGKILL if needed. Termination must happen via the process group because `npx` forks a child; killing the parent alone leaves the child writing to DuckDB. The graceful shutdown path lets git-truck's `stopHandler -> InstanceManager.closeAllDBConnections` flush cleanly.
6. **Open the per-repo DuckDB cache read-only** at `$TMPDIR/git-truck-cache/<sanitized_repo>/<sanitized_branch>.db` and run the dominant-author SQL extracted verbatim from git-truck's bundled server.

`sanitize(s) = re.sub(r'\W', '_', s) + '_'` — applied to both the absolute repo path and the branch name to match how v3 builds the cache path.

## SQL we run

The wrapper queries `filechanges_commits_renamed` (the on-disk view) rather than git-truck's in-memory `filechanges_commits_renamed_cached` materialization. The two have the same columns; the cached form lives only on git-truck's writer connection. A read-only connection from a separate process must read the base view.

## Persistence shape

git-truck reports contributor **names** but not emails. `persist_git_truck` synthesizes a pseudo-email `name:<slug>` (lowercase, spaces → underscores) so rows have a stable join key without colliding with real email addresses from git-fame. Existing `ownership_share` rows for `(repo_id, source='git-truck')` are deleted before insert.

## Why cross-check, not canonical

- **Name-keyed.** Two committers with the same display name on different machines collapse into one row.
- **Insertions + deletions, not surviving LOC.** The dominant-author SQL sums `insertions + deletions`, which is contribution volume — not blame-derived surviving lines. git-fame gives the surviving-blame answer.

Disagreements with git-fame surface on the Health tab; the dashboard always treats git-fame as canonical.

## Prerequisites

- `node` and `npx` on PATH. Node 20+ recommended.
- First run downloads `git-truck@3.3.0` via npx; subsequent runs reuse the npx cache.
- `$TMPDIR` must be writable — that's where the analysis cache lives.
