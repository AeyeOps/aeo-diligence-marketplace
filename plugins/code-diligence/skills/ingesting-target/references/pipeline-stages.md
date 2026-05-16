# Pipeline stages — what the `ingest` CLI does, in order

Entry point: `src/code_diligence/cli.py::ingest`. Each stage is idempotent — repeated runs do not double-count.

## Stage 1 — Schema migrate

`migrate(conn)` brings the warehouse to current `SCHEMA_VERSION`. Fresh runs create every table from `src/code_diligence/warehouse/schema.py`. Existing warehouses run any missing migrations registered in `warehouse/migrations.py`.

## Stage 2 — Target + repo registration

`register_target(...)` upserts a row in `targets`. Each subdirectory of `storage.repo_clone_root` that contains `.git/` is registered via `upsert_repo(...)` in `repos`.

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

## Stage 7 — GitHub platform pass (full tier only, `sources.github.enabled: true`)

Per repo: `pr_metrics`, `actions_metrics`, `release_metrics`, `issue_metrics`. Driven by the token from `sources.github.token_env`.

## Stage 8 — Axis confidence + taxonomy

`compute_axis_confidence(...)` writes `axis_confidence` (per-axis signal completeness). `load_taxonomy_into_warehouse(...)` writes the canonical card list to `axes_taxonomy`. See `skills/understanding-pe-diligence-axes/SKILL.md` for the card map.

## Stage 9 — Narrator (if `claude` CLI + `ANTHROPIC_API_KEY` present)

`run_narrator_for_target(...)` spawns the `diligence-narrator` agent, which writes one narrative per `(axis, section_key)` into `narratives`. Missing CLI → stage skipped; dashboard still renders, without prose.

## Stage 10 — Tooling versions snapshot

`update_tooling_versions(...)` writes `{tool_name: version}` JSON into `targets.tooling_versions`. Missing tools recorded as `"not-installed"`, so the column reflects environment provenance even on partial runs.
