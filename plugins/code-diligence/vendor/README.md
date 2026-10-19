# Vendored binaries

These tools are vendored to pin versions and avoid repeated downloads.

- `code-maat-1.0.4-standalone.jar` — Adam Tornhill's code-maat. Source: https://github.com/adamtornhill/code-maat/releases/tag/v1.0.4. License: GPLv3 (see code-maat repo).

Do **not** commit the JARs themselves to git (`.gitignore` excludes them). Plugin-install instructions point users to download into this dir.

[`repowise-0.57.0-worker-logging.patch`](repowise-0.57.0-worker-logging.patch) repairs the provider's spawned duplication worker, which otherwise emits debug logs into CLI JSON stdout on repositories with at least 1,000 parsed files. It routes diagnostics to stderr without changing findings. Apply to the installed 0.57.0 package with a fresh file inode; installation details are in [tool prerequisites](../skills/aeo-diligence-ingest/references/tool-prerequisites.md#native-installation-details).
