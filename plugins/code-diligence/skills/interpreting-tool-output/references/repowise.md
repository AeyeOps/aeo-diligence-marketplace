# repowise

Source of typed findings — bus factor, hotspot, coupling, ownership, dead code, "why."

> **Note on transport.** repowise also ships an MCP server, but the **ingest wrapper uses the CLI**, not MCP. The `diligence-asker` agent is the only place an MCP path is configured (`.mcp.json` at plugin root) — and the asker uses repowise as a Q&A tool, not for warehouse writes.

## Warehouse mapping

| repowise finding type | Warehouse target | Notes |
|---|---|---|
| `bus_factor` | raw row in `repowise_findings (finding_type='bus_factor', evidence)` | code-maat is canonical for the `bus_factor` table; repowise's bus-factor stays raw for cross-check |
| `hotspot` | raw row in `repowise_findings (finding_type='hotspot', evidence)` | Cross-check `file_metrics`; not directly merged |
| `coupling` | raw row in `repowise_findings (finding_type='coupling', evidence)` | code-maat is canonical for `coupling_pairs`; repowise lives in `evidence` JSON |
| `ownership` | raw row in `repowise_findings (finding_type='ownership', evidence)` | git-fame canonical; raw row preserved |
| `dead_code` | raw row in `repowise_findings (finding_type='dead_code', evidence)` | Drives Product `abandoned_area_register` when present |
| `why` | raw row in `repowise_findings (finding_type='why', evidence)` | Free-text explanations; consumed by the narrator, not surfaced as a card |

## Invocation (`src/code_diligence/tools/repowise.py`)

The wrapper shells out to:

    repowise analyze --json <repo>

- Timeout: 300s.
- On `FileNotFoundError` (binary missing) the wrapper returns `[]` cleanly — no exception. The pipeline still records that repowise was attempted via the `isolated()` envelope; the empty result becomes a no-op insert.
- Non-zero exit also returns `[]` (no exception). This is intentional — repowise's typed findings are a nice-to-have, never a blocker.

## Persistence shape

`persist_repowise` deletes prior `repowise_findings` rows for the repo, then inserts one row per finding with `(scope, finding_type, severity)` extracted from the top-level finding object and the full finding JSON stored verbatim in the `evidence` column. The wrapper does **not** parse repowise's taxonomy — that mapping happens at render time in the dashboard, keeping repowise upgrades from breaking the warehouse schema.

## Why store raw

repowise has its own confidence model distinct from ours. The wrapper preserves the full payload so the narrator and dashboard can re-interpret as repowise evolves, without a schema migration each time.

## Quirks

- **No MCP path in ingest.** The MCP server runs only for the `diligence-asker` agent. The ingest CLI path is independent and does not require the MCP runtime.
- **Quiet on small repos.** Repos with <~50 commits often return zero findings — a true negative, not an error.
- **No version pin.** The wrapper does not check `repowise --version`; whatever's on PATH is what runs. `targets.tooling_versions` records the version observed at run time.

## When to trust it

- `dead_code` and `why` — primary; no other tool in the stack produces them.
- Everything else — cross-check only.
