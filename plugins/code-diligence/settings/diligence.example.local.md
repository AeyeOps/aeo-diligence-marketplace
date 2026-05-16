---
target_id: example-target
target_name: Example Target
description: Series C AI infra startup; 4 GH orgs, ~280 repos
---
sources:
  github:
    enabled: true
    token_env: EXAMPLE_DILIGENCE_GH_TOKEN
    orgs: [example-corp, example-labs]
    include_archived: false
  github_platform:
    pr_data: true
    actions_data: true
    issues_data: true
storage:
  warehouse_path: ~/data/code-diligence/example-target.duckdb
  repo_clone_root: ~/data/code-diligence/repos/example-target/
  curation_dir: ~/data/code-diligence/example-target/curation/
dashboard:
  theme: default
  output_path: ~/data/code-diligence/dashboard/
heuristics:
  abandoned_threshold_days: 180
  bus_factor_coverage_pct: 50
  fte_inference: true
  fte_inference_signals: [email_domain, commit_cadence, tenure, repo_breadth]
  # Aggregated to repo level (no individual surveillance), but gated for privacy-sensitive contexts
  allow_working_pattern_card: false
