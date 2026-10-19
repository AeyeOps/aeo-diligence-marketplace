# Pipeline stages — what the `ingest` CLI does, in order

Entry point: `src/code_diligence/cli.py::ingest`. Each stage is idempotent — repeated runs do not double-count.

## Stage 1 — Schema migrate

`migrate(conn)` brings the warehouse to current `SCHEMA_VERSION`. Fresh runs create every table from `src/code_diligence/warehouse/schema.py`. Existing warehouses run any missing migrations registered in `warehouse/migrations.py`.

## Stage 2 — Target + repo registration

`register_target(...)` upserts a row in `targets`. When GitHub is enabled, the CLI enumerates the configured organizations, applies `include_archived`, and clones or fast-forwards repositories under `<repo_clone_root>/<owner>/<repo>`. Existing local repositories at one or two directory levels are also discovered. Fetch failures are recorded and excluded from that run; divergent branches are not reset. Repositories are registered with `upsert_repo(...)`.

## Stage 3 — Git walk (per repo, isolated)

For each repo, `walk_commits` streams `git log --no-renames --numstat`. `persist_repo_git_facts` writes:

- `commits_fact` — one row per commit
- `commit_file_authors` — one row per (commit, file) — backs the People communication graph
- `authors` — per-target aggregate (first/last seen, total commits)
- `file_metrics` — per-file revisions, distinct authors, last modified

The walker runs inside `isolated(...)`, so a failure in one repo does not poison siblings; the failure is logged into `tool_failures`.

## Stage 4 — Cheap tools (quick + full tier)

`run_cheap_tools_for_repo` runs each tool sequentially (DuckDB is not thread-safe for concurrent writes from the same process):

| Tool | Wrapper | Warehouse outputs |
|---|---|---|
| git-fame | `tools/git_fame.py` | `ownership_share (source='git-fame')` |
| git-of-theseus | `tools/git_of_theseus.py` | `code_age_buckets` |
| git-truck | `tools/git_truck.py` | `ownership_share (source='git-truck')` |

Each wrapper is wrapped by `isolated()`. Missing binaries → `tool_failures (class='prereq_missing')`.

## Stage 5 — Curation pass

`run_curation_pass(...)` runs three heuristics:

1. **Identity merging** — emails likely belonging to one person (name + domain similarity) → `identity_map`
2. **FTE classification** — internal vs. external vs. bot, based on email domain + commit cadence + tenure + repo breadth → `contributor_classification`
3. **Repo classification** — production vs. abandoned vs. tooling, based on commit recency vs. `heuristics.abandoned_threshold_days` → `repo_classification`

Each heuristic writes a YAML to `storage.curation_dir/` with `status: needs_review` for low-confidence entries. The dashboard surfaces those counts on the curation page.

## Stage 6 — Expensive tools (full tier only)

`run_expensive_tools_for_repo` runs three tools per repo, each isolated:

| Tool | Wrapper | Warehouse outputs |
|---|---|---|
| code-maat | `tools/code_maat.py` | updates `file_metrics.revisions` and `top_owner_email/pct`; writes `coupling_pairs (source='code-maat')` |
| hercules | `tools/hercules.py` | `burndown_series` |
| repowise | `tools/repowise.py` | `repowise_findings` |

## Stage 7 — GitHub platform pass (full tier only, any `sources.github_platform` switch true)

Per repo: `pr_metrics`, `actions_metrics`, `release_metrics`, `issue_metrics`. Driven by the token from `sources.github.token_env`. Local checkouts take their GitHub repository from the `origin` URL, so platform data does not require organization discovery.

## Stage 8 — Axis confidence + taxonomy

`compute_axis_confidence(...)` writes `axis_confidence` (per-axis signal completeness). `load_taxonomy_into_warehouse(...)` writes the canonical card list to `axes_taxonomy`. See `skills/aeo-diligence-axes/SKILL.md` for the card map.

## Stage 9 — Tooling versions and completion

`update_tooling_versions(...)` records available tool versions in `targets.tooling_versions`. The CLI prints curation counts and recorded failures, stores the completion instant as UTC in `last_refreshed_at`, and closes the warehouse. The dashboard converts that instant to the viewer's local time.

## After the CLI — Narration and dashboard

The ingesting skill runs a narrator through the runtime's native subagent tool after the CLI closes its warehouse connection. The narrator uses the registered warehouse MCP tools. Then the skill invokes the dashboard renderer with the target's configured paths and privacy setting. Ingest alone does not invoke an LLM or build HTML.
