# Repowise adapter

The full-tier adapter calls the current Repowise CLI for one repository:

```sh
repowise health <repo> --format json --no-workspace --recompute
repowise dead-code <repo> --format json --no-workspace
```

Health recomputation in JSON mode does not persist a Repowise index or request model-generated code. Dead-code uses the provider's stored result when applicable and otherwise analyzes the working tree. The adapter retains provider defaults for detection and confidence.

Health returns an object with `findings`; dead-code returns an array. The adapter keeps each raw finding and derives a scope from its file and function/symbol, and a type from `biomarker_type` or `kind`. Multiple provider hits can share that scope and type, so the warehouse preserves them without a uniqueness constraint. These records enter `repowise_findings`. Health's `kpis` summary enters `repowise_health`, one row per repository: average and hotspot health, maintainability and performance scores from 1 to 10 where higher is healthier, files scored, and the lowest-scoring file. Its structure and history averages are deductions from 10, not scores, and are not stored. Both tables feed the Code health card.

A missing executable, failed command, or invalid response is a failed tool run, not an empty finding set. The per-tool transaction preserves the prior snapshot on failure. A successful empty result clears it. Each subprocess has a 300-second timeout.

Repowise defaults to anonymous usage telemetry. The adapter sets `REPOWISE_TELEMETRY_DISABLED=1` for both subprocesses. For manual CLI analysis, disable and verify telemetry first; see [prerequisite coverage](../../aeo-diligence-ingest/references/tool-prerequisites.md#local-analysis-and-network-use). Package downloads and permitted npm version checks are separate from vendor telemetry and model-generated code.

In 0.57.0, the spawned duplication worker can write debug logs to JSON stdout for repositories with at least 1,000 parsed files. Use the provider worker fix, `vendor/repowise-0.57.0-worker-logging.patch` under the plugin root, documented in the prerequisite reference. Keep the adapter's strict JSON parse: worker diagnostics belong on stderr, and malformed provider output remains a visible failure.

The plugin does not register a Repowise MCP server. The asker reads persisted findings through the warehouse MCP. See upstream [health](https://github.com/repowise-dev/repowise/blob/main/packages/cli/src/repowise/cli/commands/health_cmd/command.py) and [dead-code](https://github.com/repowise-dev/repowise/blob/main/packages/cli/src/repowise/cli/commands/dead_code_cmd.py) for their CLI contracts.
