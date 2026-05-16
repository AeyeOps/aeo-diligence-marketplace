# diligence-asker boundary

## Read-only contract

The `diligence-asker` agent (`agents/diligence-asker.md`) is allowlisted to only these tools:

| Tool | Purpose |
|---|---|
| `mcp__diligence-warehouse__list_tables` | Enumerate warehouse tables |
| `mcp__diligence-warehouse__describe_table` | Inspect a table's columns |
| `mcp__diligence-warehouse__read_query` | Run `SELECT` queries (no writes) |
| `Read` | Read repo files at `storage.repo_clone_root` |
| `Grep` | Pattern-search the cloned repos |
| `Glob` | File discovery in repo clones |

The warehouse MCP server (`mcp/diligence-warehouse`) intentionally exposes only read paths. The agent cannot run `INSERT`, `UPDATE`, `DELETE`, or DDL through any surfaced tool. The repowise MCP is registered globally in `.mcp.json` but not allowlisted for the asker — narrator-only.

## Why read-only

Two reasons:

1. **Auditability.** Anything the asker discovers should be reproducible by a partner running the same SQL by hand. Write paths would let the agent silently re-derive curation YAMLs or narratives mid-conversation, breaking that trace.
2. **Cost containment.** The narrator is the only write-side actor and is gated behind `/code-diligence:refresh`. The asker runs cheap synchronous queries; partners can ask 20 follow-ups in a session without budget concern.

## When the asker should refuse

- The user asks for re-narration of an axis card → redirect to `skills/refreshing-target/SKILL.md`.
- The user asks for curation overrides → redirect them to edit the YAMLs in `storage.curation_dir` directly, then refresh.
- The user asks the asker to "fix" a warehouse row → not in scope; refuse with the redirect above.

## Cross-references

- Agent definition (tools allowlist + system prompt): `agents/diligence-asker.md`
- Warehouse MCP server: `mcp/diligence-warehouse/`
- Per-target settings location: `~/.claude/code-diligence-<target>.local.md` (user-owned, outside plugin root)
