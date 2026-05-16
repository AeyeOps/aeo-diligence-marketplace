# Adding a new plugin to this marketplace

This marketplace registers one or more Claude Code plugins. Each plugin lives in its own subdirectory under `plugins/` and is announced to Claude Code via the top-level `.claude-plugin/marketplace.json`.

## Directory shape

```
plugins/<your-plugin>/
├── .claude-plugin/
│   └── plugin.json        # required — per-plugin manifest
├── README.md              # required — what the plugin does, how to install, how to use
├── LICENSE                # required if license differs from the marketplace
├── commands/              # optional — slash commands (one .md per command)
├── agents/                # optional — subagent definitions (one .md per agent)
├── skills/                # optional — model-activated skills (one subdir per skill, each with SKILL.md)
├── hooks/
│   └── hooks.json         # optional — event handlers
├── .mcp.json              # optional — MCP server definitions
└── …                      # plugin-private source code, tests, fixtures, vendor blobs
```

Use kebab-case for all names. Keep component directories at the plugin root — never nest them inside `.claude-plugin/`.

## Per-plugin manifest (`plugin.json`)

Minimum:

```json
{
  "name": "your-plugin"
}
```

Recommended:

```json
{
  "name": "your-plugin",
  "version": "0.1.0",
  "description": "One-line summary of what the plugin does.",
  "author": {
    "name": "AeyeOps",
    "email": "275853971+aeyeopsdev@users.noreply.github.com"
  },
  "homepage": "https://github.com/AeyeOps/aeo-diligence-marketplace/tree/main/plugins/your-plugin",
  "repository": {
    "type": "git",
    "url": "https://github.com/AeyeOps/aeo-diligence-marketplace.git"
  },
  "license": "MIT"
}
```

## Registering the plugin in the marketplace manifest

Open `.claude-plugin/marketplace.json` at the repo root and append an entry to the `plugins` array:

```json
{
  "name": "your-plugin",
  "source": "./plugins/your-plugin",
  "description": "One-line summary (mirror plugin.json).",
  "version": "0.1.0",
  "category": "analytics",
  "tags": ["due-diligence", "..."],
  "homepage": "https://github.com/AeyeOps/aeo-diligence-marketplace/tree/main/plugins/your-plugin",
  "license": "MIT"
}
```

- `name` and `source` are required.
- `source` is a path relative to the repo root. It must start with `./`.
- `description`, `version`, `category`, `tags`, `homepage`, `license` are optional but improve `claude plugin list` output.

## Verifying locally before pushing

From any directory:

```sh
# point Claude Code at this checkout (not the GitHub URL) so you can iterate
claude plugin marketplace add /absolute/path/to/aeo-diligence-marketplace

# install your plugin
claude plugin install your-plugin@aeo-diligence
```

If the manifest is malformed, `marketplace add` exits non-zero with a parse error. If the plugin's manifest is malformed, `plugin install` does.

## Verifying from the published location

After pushing to `main`:

```sh
claude plugin marketplace remove aeo-diligence    # drop the local-path version
claude plugin marketplace add AeyeOps/aeo-diligence-marketplace
claude plugin install your-plugin@aeo-diligence
```

A `restart` of the Claude Code session is required for new components (commands, agents, skills, hooks, MCP servers) to load.

## Naming and category conventions

- `name`: kebab-case, no spaces, unique within the marketplace. Avoid generic names like `tools` or `utils`.
- `category`: pick one bucket per plugin — `analytics`, `automation`, `governance`, `data`, `productivity`, etc.
- `tags`: 3-8 lowercase hyphenated tags. The first should be the diligence axis or domain (`due-diligence`, `migration`, `observability`).

## Conventional file locations inside a plugin

These are the locations Claude Code auto-discovers (no manifest entry needed):

| Component | Path | Loader |
|---|---|---|
| Slash commands | `commands/*.md` | each file becomes a `/<plugin-name>:<command>` |
| Subagents | `agents/*.md` | invocable via `Task` tool |
| Skills | `skills/<skill-name>/SKILL.md` | auto-activated by description match |
| Hooks | `hooks/hooks.json` | event handlers |
| MCP servers | `.mcp.json` | started when plugin enables |

Anywhere a path is needed (hook script, MCP command, etc.), reference files via the `${CLAUDE_PLUGIN_ROOT}` env var so the plugin works regardless of install location.
