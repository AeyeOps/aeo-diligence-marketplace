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
  aws_inspector:
    enabled: false
    profile: example-aws-profile
    region: us-east-1
    resource_prefixes: [example-app]
    fix_available: []
    snapshot_dirs: []
    timezone: UTC
storage:
  warehouse_path: ~/data/code-diligence/example-target/warehouse.duckdb
  repo_clone_root: ~/data/code-diligence/example-target/repos/
  curation_dir: ~/data/code-diligence/example-target/curation/
dashboard:
  output_path: ~/data/code-diligence/example-target/dashboard/
  security_chart_path: null
  repository_labels: {}
  workflow_labels: {}
  contributor_labels: {}
heuristics:
  abandoned_threshold_days: 180
  fte_inference: false
  allow_working_pattern_card: false
