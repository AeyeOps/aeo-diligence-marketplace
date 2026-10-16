# Repowise adapter

The full-tier adapter calls the current Repowise CLI for one repository:

```sh
repowise health <repo> --format json --no-workspace --recompute
repowise dead-code <repo> --format json --no-workspace
```

Health recomputation in JSON mode does not persist a Repowise index or request model-generated code. Dead-code uses the provider's stored result when applicable and otherwise analyzes the working tree. The adapter retains provider defaults for detection and confidence.

Health returns an object with `findings`; dead-code returns an array. The adapter keeps each raw finding and derives a scope from its file and function/symbol, and a type from `biomarker_type` or `kind`. These records enter `repowise_findings`; they are not automatically merged into dashboard metrics.

A missing executable, failed command, or invalid response is a failed tool run, not an empty finding set. The per-tool transaction preserves the prior snapshot on failure. A successful empty result clears it. Each subprocess has a 300-second timeout.

The plugin does not register a Repowise MCP server. The asker reads persisted findings through the warehouse MCP. See upstream [health](https://github.com/repowise-dev/repowise/blob/main/packages/cli/src/repowise/cli/commands/health_cmd/command.py) and [dead-code](https://github.com/repowise-dev/repowise/blob/main/packages/cli/src/repowise/cli/commands/dead_code_cmd.py) for their CLI contracts.
