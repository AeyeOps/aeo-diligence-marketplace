# Tool prerequisites and skip behavior

Each external binary the ingest pipeline expects, what it needs, and what happens when it's missing.

## Required for all tiers

| Binary | How to install | Skip behavior |
|---|---|---|
| `git` | system package manager | Hard fail — the walker cannot run |
| `uv` | `brew install uv` / `pipx install uv` | Hard fail — entry point is `uv run` |

## Required for `--quick` (cheap tools)

| Binary | How to install | Skip behavior when missing |
|---|---|---|
| `git-fame` | `uv tool install git-fame` (callable as `git fame`) | `ownership_share (source='git-fame')` stays empty; People `knowledge_concentration` card shows "data unavailable" |
| `git-of-theseus-analyze` | `uv tool install git-of-theseus` | `code_age_buckets` stays empty; Product `code_aging_chart` shows "data unavailable" |
| `npx` (drives `git-truck@3.3.0`) | Node 20+; `npx` ships with Node. First run downloads `git-truck` via `npx --yes`. | `ownership_share (source='git-truck')` stays empty; cross-check only |

## Required for `--full` (expensive tools + platform pass)

| Binary | How to install | Skip behavior when missing |
|---|---|---|
| `java` (≥17) | `brew install openjdk@17` | code-maat fails → no `coupling_pairs (source='code-maat')`; `file_metrics.top_owner_email/pct` left as walker default |
| `hercules` | `go install github.com/src-d/hercules/cmd/hercules@latest` | `burndown_series` empty → `burndown_over_time` card shows "data unavailable" |
| `repowise` | per repowise install guide | `repowise_findings` empty; cross-check only |
| `claude` CLI + `ANTHROPIC_API_KEY` | `npm install -g @anthropic-ai/claude-code` | Narrator stage skipped → dashboard renders without prose summaries |

## Vendored

| Asset | Location | Notes |
|---|---|---|
| `code-maat-1.0.4-SNAPSHOT-standalone.jar` | `vendor/` at the plugin root | Drop the JAR there once; `tools/code_maat.py` invokes it via `java -jar`. Missing JAR raises `CodeMaatError`; see `vendor/README.md`. |

## How the pipeline records missing tools

Each tool runs inside the `isolated()` envelope (`src/code_diligence/ingest/isolation.py`). On `FileNotFoundError` (missing binary) or non-zero exit, a `tool_failures` row is written and the pipeline moves on. After every run, stage 10 (`update_tooling_versions`) writes `{tool_name: version}` JSON into `targets.tooling_versions`, recording each absent tool as `"not-installed"`. Inspect via:

    SELECT tooling_versions FROM targets WHERE target_id = '<target>';

That column is the canonical record of "what did this refresh actually run against."

## What each present tool populates

| Tool present | Tables written |
|---|---|
| `git` (always) | `commits_fact`, `commit_file_authors`, `authors`, `file_metrics` (initial revisions/distinct authors/last-modified), `repos` |
| `git-fame` | `ownership_share (source='git-fame')` |
| `git-of-theseus-analyze` | `code_age_buckets` |
| `git-truck` (via `npx`) | `ownership_share (source='git-truck')` |
| `hercules` | `burndown_series` |
| `code-maat` (Java + vendored JAR) | `coupling_pairs (source='code-maat')`, updates `file_metrics.revisions`, updates `file_metrics.top_owner_email/pct` |
| `repowise` | `repowise_findings` |
| `claude` CLI + key | `narratives` |

If a card shows "data unavailable," reverse-engineer back to the missing tool by looking at the column above.

## CI behavior

The plugin's GitHub Actions workflow runs pytest only — it does not install hercules, code-maat, repowise, git-truck, git-fame, git-of-theseus, or Java. Tests that depend on those binaries use `pytest.mark.skipif` to skip when the binary is absent, which is the default in CI. See the test files under `tests/tools/` for the skip markers.
