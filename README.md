<p align="center">
  <strong>aeo-diligence-marketplace</strong><br/>
  <em>Claude Code plugin marketplace for AeyeOps technical due-diligence tooling</em>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"/></a>
  <a href="https://claude.com/claude-code"><img alt="Claude Code marketplace" src="https://img.shields.io/badge/Claude%20Code-marketplace-d4a574.svg"/></a>
</p>

---

This repository is a **Claude Code plugin marketplace** — a registry that Claude Code can install one or more plugins from with a single command. It is not itself a plugin; the actual plugins live under [`plugins/`](plugins/).

## Install the marketplace

```sh
claude plugin marketplace add AeyeOps/aeo-diligence-marketplace
```

After that, every plugin listed below is installable with one line.

## Plugins in this marketplace

| Plugin | What it does | Install |
|---|---|---|
| [**code-diligence**](plugins/code-diligence/) | Portfolio dashboard for PE technical due diligence — People / Product / Process insights from any set of git repositories. Observable Framework dashboard, DuckDB warehouse, narrator + read-only asker agents. | `claude plugin install code-diligence@aeo-diligence` |

More diligence plugins are planned. Each will land as a sibling under `plugins/` and a new entry in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json).

## Repository layout

```
aeo-diligence-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest — Claude Code reads this
├── plugins/
│   └── code-diligence/           # one plugin per subdirectory
│       ├── .claude-plugin/
│       │   └── plugin.json       # per-plugin manifest
│       ├── agents/   skills/   hooks/   .mcp.json
│       └── README.md             # plugin-specific docs
├── docs/
│   └── adding-a-plugin.md        # how to contribute a new plugin
├── LICENSE
└── README.md                     # this file
```

## Adding a new plugin

See [`docs/adding-a-plugin.md`](docs/adding-a-plugin.md) for the exact directory shape, manifest fields, and the marketplace-registration step.

## License

[MIT](LICENSE) · Copyright © 2026 AeyeOps

Each bundled plugin and any vendored third-party tool retains its own license — see the plugin's own `LICENSE` and per-tool attribution in its README.
