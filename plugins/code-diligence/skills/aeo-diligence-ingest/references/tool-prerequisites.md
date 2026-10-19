# Tool prerequisites and coverage

Each external binary the ingest pipeline expects, what it needs, and what happens when it's missing.

## Contents

- [Choose the installation environment](#choose-the-installation-environment)
- [Explain and resolve coverage gaps](#explain-and-resolve-coverage-gaps)
- [Local analysis and network use](#local-analysis-and-network-use)
- [Required tools](#required-for-all-tiers), [lightweight analyzers](#optional-analyzers-used-by---quick-and---full), [deep analyzers](#additional-optional-analyzers-used-by---full), and [vendored assets](#vendored)
- [Native installation details](#native-installation-details)
- [Failure recording](#how-the-pipeline-records-missing-tools), [warehouse outputs](#what-each-present-tool-populates), and [CI coverage](#ci-behavior)

## Choose the installation environment

Identify the OS and CPU architecture where ingestion and MCP will actually run, including any container, emulation or WSL environment. Match binaries, Python wheels and runtime dependencies to that environment. ARM64 assets may be named `arm64` or `aarch64`; Intel/AMD 64-bit assets may be named `x86_64` or `amd64`.

On macOS (Apple Silicon or Intel) and Linux (ARM64 or x86_64), use the host's existing package or runtime manager and compatible upstream releases. On Windows, choose a Linux execution environment such as an existing [WSL distribution](https://learn.microsoft.com/en-us/windows/wsl/about): the current git-truck adapter uses POSIX process-group cleanup. Keep the project, analyzers and warehouse MCP in that same environment. If a new environment is needed, explain the choice before setting it up.

When a matching binary or wheel is unavailable, check the upstream source-build path and its compiler or development-header requirements. Use the version-specific remedies below when the installed version and failure match.

## Explain and resolve coverage gaps

Before ingest or refresh, select tools for the [execution environment](#choose-the-installation-environment), then check the requested tier's executables with `command -v` and their supported version commands. Check Java and the exact JAR path separately; `java -version` alone does not establish code-maat availability. Verify the active runtime exposes the warehouse MCP tools and query `targets` to confirm the warehouse, after closing any ingest writer. A configured server is not a connected server. For an initial target, connect it after the warehouse exists.

When a full run requests GitHub platform data, check that the variable named by `sources.github.token_env` is set, without printing its value. A missing variable is a gap: tell the user which variable to set, that pull-request, CI, release and issue data depend on it, and that the ingest stops until it is set or those switches are turned off. The user sets the token in their environment. Never create, fetch or store one.

For every confirmed gap, tell the user:

1. What is missing or failing, with the probe result. Distinguish an absent package, missing asset, unsupported build, connection problem, and successful analysis with no findings.
2. Which result it supplies and the downside of proceeding without it, using the tables below. Installing tools does not resolve analyst-owned contributor classifications.
3. The concrete remedy and any download, build, connection, restart, model use, or cost it requires. Recommend closing the gap when it supplies a requested result.
4. Whether existing authorization covers that remedy. If it does, perform it and validate the recovered capability. Otherwise ask whether to close the gap or continue with the stated reduced coverage, batching the known gaps into one choice.

Carry the user's choice through the run. Newly discovered failures receive the same explanation and recovery decision. When recovery is authorized, finish it, rerun the affected analyses, recompute confidence and rebuild; do not stop at listing missing tools. Report what actually ran and what remains unavailable. A successful command or populated confidence table does not prove complete repository or analyzer coverage.

## Local analysis and network use

Separate local computation from installation downloads, repository fetching, GitHub API collection and hosted narration. Do not describe the whole workflow as offline because an analyzer reads a local checkout.

- Git history, git-fame, git-of-theseus, code-maat, Hercules burndown and Repowise health/dead-code can analyze local repositories. Hercules can also clone remote URLs; use the configured local checkout for local analysis.
- `npx` downloads git-truck and dependencies on first use. Git-truck 3.3.0 also contains an npm version check in its local server. Cached installation alone does not establish no outbound traffic; use network isolation for a local-only run.
- Repowise has opt-out anonymous usage telemetry. The adapter sets `REPOWISE_TELEMETRY_DISABLED=1` for its subprocesses. For direct CLI use, run `DO_NOT_TRACK=1 repowise telemetry disable` and verify `repowise telemetry status` before analysis. Its `--generate-code` mode invokes a configured model; this adapter does not request it.
- The warehouse MCP reads a local DuckDB file over stdio. Narration is generated by the agent's model; a hosted agent sends its queried evidence to that model. A connected local MCP does not make model inference local. Explain this boundary before promising local-only narration.

When no external traffic is required, verify the actual analyzer invocation in the environment's supported network isolation after dependencies are installed. On Linux with unprivileged user namespaces, `unshare --user --map-root-user --net` can deny external networking; enable loopback inside that namespace if an analyzer needs a local server. Isolate the local analyzer stage, not an ingest that still needs to fetch repositories or query GitHub: the existing CLI fetches an origin before analysis and excludes a repository when that fetch fails. Keep one-off verification transient. Distinguish prevented external traffic from evidence that a tool never attempted a connection.

## Required for all tiers

| Binary | How to install | Skip behavior |
|---|---|---|
| `git` | system package manager | Hard fail — the walker cannot run |
| `uv` | `brew install uv` / `pipx install uv` | Hard fail — `bin/run` starts every command through `uv run` |

## Optional analyzers used by `--quick` and `--full`

| Binary | How to install | Skip behavior when missing |
|---|---|---|
| `git-fame` | `uv tool install git-fame`; verify `git-fame --version` | No git-fame ownership data for the People bus-factor estimate or knowledge concentration. Git-truck does not substitute for the dashboard's git-fame queries. |
| `git-of-theseus-analyze` | `uv tool install git-of-theseus` | `code_age_buckets` stays empty; Product `code_aging_chart` shows "data unavailable" |
| `npx` (drives `git-truck@3.3.0`) | Node 22+; `npx` ships with Node. First run downloads `git-truck` via `npx --yes`. | `ownership_share (source='git-truck')` stays empty; cross-check only |

## Additional optional analyzers used by `--full`

| Binary | How to install | Skip behavior when missing |
|---|---|---|
| `java` (≥17) and the JAR below | Use the host's package manager, or `mise use --global java@temurin-17.0.20+8` when mise manages tools; verify `java -version` and `java -jar <jar> --help` | No hidden-coupling pairs or code-maat file-owner enrichment; file-owner estimates remain unavailable. |
| `hercules` | Native binary from [v10.7.2](https://github.com/src-d/hercules/releases/tag/v10.7.2), or build below; verify `hercules version` | No historical code-survival series; current code age from git-of-theseus cannot show that trajectory. |
| `repowise` | `uv tool install repowise`; verify `repowise --version`, disable telemetry as above | No Code health card: no Repowise health scores or findings by severity. |
| AWS Inspector access (optional) | boto3 installs with the plugin; the user supplies an AWS CLI profile that can call `inspector2:ListFindings` in the target account and region | No Security findings card or summary column. |
| Native warehouse MCP | Configure the existing stdio server for the target; see [connection boundary](../../aeo-diligence-ask/references/asker-boundary.md) | No native asker queries or persisted agent narration. Metrics and dashboard rendering can still work; an empty narrative is not an analytical finding. |

## Vendored

| Asset | Location | Notes |
|---|---|---|
| `code-maat-1.0.4-standalone.jar` | `vendor/` at the plugin root | Download the [released standalone JAR](https://github.com/adamtornhill/code-maat/releases/tag/v1.0.4). The filename must match `tools/code_maat.py`; installing Java does not supply it. Keep the binary out of git. |

## Native installation details

Hercules v10.7.2 releases provide amd64 binaries, not a Linux ARM64 binary. Its module uses replacement directives, so `go install ...@version` is not the source-build path. From a checkout of tag `v10.7.2`, run:

```sh
go generate ./cmd/hercules
go build -o "$HOME/.local/bin/hercules" ./cmd/hercules
hercules version
```

Repowise 0.57.0 depends on tree-sitter-gdscript 6.1.0. That dependency has no Linux ARM64 wheel and its source archive omits `tree_sitter/parser.h`. If installation fails with that exact missing-header diagnostic, place the header from [the matching upstream tag](https://github.com/prestonknopp/tree-sitter-gdscript/blob/v6.1.0/src/tree_sitter/parser.h) under a local include directory's `tree_sitter/`, and supply that include directory through `CPATH` while running `uv tool install repowise==0.57.0`. This supplies the missing build input without changing project dependencies or the curated agent venv. Validate the actual health and dead-code commands after installation.

Repowise 0.57.0 also spawns a fresh duplication worker at 1,000 parsed files. That worker does not inherit the CLI's logging configuration and can prefix JSON stdout with `duplication_token_cache` debug output. The worker logging patch, `vendor/repowise-0.57.0-worker-logging.patch` under the plugin root, routes its diagnostics to stderr without changing findings. Apply it to this version's installed `repowise/core/analysis/health/duplication/isolation.py` using a fresh file inode so uv's shared package cache remains unchanged. Reinstallation replaces that local repair; validate actual JSON commands after any upgrade. Do not hide malformed output by discarding arbitrary lines in the adapter.

## How the pipeline records missing tools

Each tool runs inside the `isolated()` envelope (`src/code_diligence/ingest/isolation.py`). On `FileNotFoundError` (missing binary) or non-zero exit, a `tool_failures` row is written and the pipeline moves on. When the tool later succeeds for that repository, its earlier failure rows are deleted, so `tool_failures` and Health show only current failures. After every run, `update_tooling_versions` writes `{tool_name: version}` JSON into `targets.tooling_versions`, recording each absent tool as `"not-installed"`. Inspect via:

    SELECT tooling_versions FROM targets WHERE target_id = '<target>';

That column records the installed tool inventory, not successful execution. Check current-run failures and actual output rows as well. An initial missing analyzer leaves its tables empty; a failed refresh preserves the previous snapshot through the isolation transaction, so existing rows alone do not establish refreshed coverage.

## What each present tool populates

| Tool present | Tables written |
|---|---|
| `git` (always) | `commits_fact`, `commit_file_authors`, `authors`, `file_metrics` (initial revisions/distinct authors/last-modified, and whether the file exists at HEAD), `repos` |
| `git-fame` | `ownership_share (source='git-fame')` |
| `git-of-theseus-analyze` | `code_age_buckets` |
| `git-truck` (via `npx`) | `ownership_share (source='git-truck')` |
| `hercules` | `burndown_series` |
| `code-maat` (Java + vendored JAR) | `coupling_pairs (source='code-maat')`, updates `file_metrics.revisions`, updates `file_metrics.top_owner_email/pct` |
| `repowise` | `repowise_findings`, `repowise_health` |
| AWS Inspector (optional, `sources.aws_inspector`) | `security_reads`, `security_observations`, `security_monthly` |
| Native narrator agent with connected warehouse MCP | `narratives` |

If a card shows "data unavailable," reverse-engineer back to the missing tool by looking at the column above.

## CI behavior

The GitHub Actions workflow installs Node 22 and Java 17, runs the project and MCP server tests, Ruff and Pyright. It does not install the optional analyzer packages or download the code-maat JAR; git-truck is invoked through npx by its existing integration checks. Tests requiring unavailable tools can skip. Passing CI therefore does not establish those analyzers ran against the user's repositories.
