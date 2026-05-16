"""Warehouse schema definitions for code-diligence.

Schema version bump policy: increment SCHEMA_VERSION whenever a table
is added, dropped, or has a column added/removed/retyped. Migrations
between versions live in `migrations.py`.
"""
import duckdb

SCHEMA_VERSION = 2

DDL_STATEMENTS: list[str] = [
    # --- meta ---
    """
    CREATE TABLE IF NOT EXISTS schema_version (
      version INTEGER NOT NULL,
      applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # --- dimensions ---
    """
    CREATE TABLE IF NOT EXISTS targets (
      target_id      VARCHAR PRIMARY KEY,
      name           VARCHAR NOT NULL,
      description    VARCHAR,
      ingested_at    TIMESTAMP,
      last_refreshed_at TIMESTAMP,
      tooling_versions JSON
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS repos (
      repo_id        VARCHAR PRIMARY KEY,
      target_id      VARCHAR NOT NULL,
      name           VARCHAR NOT NULL,
      source_url     VARCHAR NOT NULL,
      default_branch VARCHAR,
      language_primary VARCHAR,
      languages      JSON,
      first_commit_at TIMESTAMP,
      last_commit_at TIMESTAMP,
      is_archived    BOOLEAN DEFAULT FALSE,
      source_capability_flags JSON,
      FOREIGN KEY (target_id) REFERENCES targets(target_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS authors (
      author_email   VARCHAR NOT NULL,
      target_id      VARCHAR NOT NULL,
      display_name   VARCHAR,
      first_seen     TIMESTAMP,
      last_seen      TIMESTAMP,
      total_commits  INTEGER DEFAULT 0,
      contributor_class VARCHAR,
      is_active_l90  BOOLEAN DEFAULT FALSE,
      PRIMARY KEY (author_email, target_id),
      FOREIGN KEY (target_id) REFERENCES targets(target_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS axes_taxonomy (
      axis           VARCHAR NOT NULL,
      section_key    VARCHAR NOT NULL,
      title          VARCHAR NOT NULL,
      description    VARCHAR,
      PRIMARY KEY (axis, section_key)
    )
    """,
    # --- curation tables (loaded from analyst YAML at ingest) ---
    """
    CREATE TABLE IF NOT EXISTS identity_map (
      target_id      VARCHAR NOT NULL,
      raw_email      VARCHAR NOT NULL,
      canonical_email VARCHAR NOT NULL,
      confidence     DOUBLE,
      source         VARCHAR NOT NULL,
      PRIMARY KEY (target_id, raw_email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS contributor_classification (
      target_id      VARCHAR NOT NULL,
      author_email   VARCHAR NOT NULL,
      class          VARCHAR NOT NULL,
      confidence     DOUBLE,
      signals        JSON,
      source         VARCHAR NOT NULL,
      PRIMARY KEY (target_id, author_email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS repo_classification (
      repo_id        VARCHAR PRIMARY KEY,
      class          VARCHAR NOT NULL,
      confidence     DOUBLE,
      signals        JSON,
      source         VARCHAR NOT NULL
    )
    """,
    # --- git facts ---
    """
    CREATE TABLE IF NOT EXISTS commits_fact (
      repo_id        VARCHAR NOT NULL,
      commit_sha     VARCHAR NOT NULL,
      author_email   VARCHAR NOT NULL,
      author_date    TIMESTAMP NOT NULL,
      files_changed  INTEGER,
      lines_added    INTEGER,
      lines_removed  INTEGER,
      is_merge       BOOLEAN DEFAULT FALSE,
      is_revert      BOOLEAN DEFAULT FALSE,
      message_first_line VARCHAR,
      PRIMARY KEY (repo_id, commit_sha)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS commit_file_authors (
      repo_id        VARCHAR NOT NULL,
      commit_sha     VARCHAR NOT NULL,
      author_email   VARCHAR NOT NULL,
      author_date    TIMESTAMP NOT NULL,
      file_path      VARCHAR NOT NULL,
      lines_added    INTEGER,
      lines_removed  INTEGER,
      PRIMARY KEY (repo_id, commit_sha, file_path)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS file_metrics (
      repo_id        VARCHAR NOT NULL,
      path           VARCHAR NOT NULL,
      revisions      INTEGER DEFAULT 0,
      total_authors  INTEGER DEFAULT 0,
      top_owner_email VARCHAR,
      top_owner_pct  DOUBLE,
      last_modified_at TIMESTAMP,
      churn_l30d     INTEGER DEFAULT 0,
      churn_l90d     INTEGER DEFAULT 0,
      complexity_proxy DOUBLE,
      PRIMARY KEY (repo_id, path)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS coupling_pairs (
      repo_id        VARCHAR NOT NULL,
      file_a         VARCHAR NOT NULL,
      file_b         VARCHAR NOT NULL,
      co_change_count INTEGER NOT NULL,
      support_pct    DOUBLE,
      lift           DOUBLE,
      source         VARCHAR NOT NULL,
      PRIMARY KEY (repo_id, file_a, file_b, source)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bus_factor (
      repo_id        VARCHAR NOT NULL,
      scope          VARCHAR NOT NULL,
      scope_key      VARCHAR NOT NULL,
      top_n_authors_pct INTEGER,
      knowledge_loss_risk_class VARCHAR,
      PRIMARY KEY (repo_id, scope, scope_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS code_age_buckets (
      repo_id        VARCHAR NOT NULL,
      bucket_start_year INTEGER NOT NULL,
      surviving_loc  INTEGER,
      deleted_loc    INTEGER,
      PRIMARY KEY (repo_id, bucket_start_year)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS burndown_series (
      repo_id        VARCHAR NOT NULL,
      snapshot_at    TIMESTAMP NOT NULL,
      vintage_year   INTEGER NOT NULL,
      surviving_loc  INTEGER,
      PRIMARY KEY (repo_id, snapshot_at, vintage_year)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ownership_share (
      repo_id        VARCHAR NOT NULL,
      author_email   VARCHAR NOT NULL,
      owned_loc      INTEGER,
      owned_files    INTEGER,
      source         VARCHAR NOT NULL,
      PRIMARY KEY (repo_id, author_email, source)
    )
    """,
    # --- tool-specific ---
    """
    CREATE TABLE IF NOT EXISTS repowise_findings (
      repo_id        VARCHAR NOT NULL,
      scope          VARCHAR NOT NULL,
      finding_type   VARCHAR NOT NULL,
      severity       VARCHAR,
      evidence       JSON,
      PRIMARY KEY (repo_id, scope, finding_type)
    )
    """,
    # --- platform facts (Phase 3) ---
    """
    CREATE TABLE IF NOT EXISTS pr_metrics (
      repo_id        VARCHAR NOT NULL,
      pr_number      INTEGER NOT NULL,
      opened_at      TIMESTAMP,
      merged_at      TIMESTAMP,
      closed_at      TIMESTAMP,
      review_latency_hours DOUBLE,
      num_reviewers  INTEGER,
      approvals      INTEGER,
      lines_changed  INTEGER,
      was_self_merged BOOLEAN,
      PRIMARY KEY (repo_id, pr_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS actions_metrics (
      repo_id        VARCHAR NOT NULL,
      workflow_name  VARCHAR NOT NULL,
      run_id         BIGINT NOT NULL,
      ran_at         TIMESTAMP,
      conclusion     VARCHAR,
      duration_seconds DOUBLE,
      PRIMARY KEY (repo_id, run_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS release_metrics (
      repo_id        VARCHAR NOT NULL,
      tag            VARCHAR NOT NULL,
      released_at    TIMESTAMP,
      days_since_prev DOUBLE,
      PRIMARY KEY (repo_id, tag)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS issue_metrics (
      repo_id        VARCHAR NOT NULL,
      issue_number   INTEGER NOT NULL,
      opened_at      TIMESTAMP,
      closed_at      TIMESTAMP,
      state          VARCHAR,
      labels         JSON,
      days_to_first_response DOUBLE,
      PRIMARY KEY (repo_id, issue_number)
    )
    """,
    # --- synthesis ---
    """
    CREATE TABLE IF NOT EXISTS narratives (
      target_id      VARCHAR NOT NULL,
      axis           VARCHAR NOT NULL,
      section_key    VARCHAR NOT NULL,
      body_md        VARCHAR NOT NULL,
      generated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      generator_version VARCHAR,
      tier           VARCHAR NOT NULL,
      PRIMARY KEY (target_id, axis, section_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS axis_confidence (
      target_id      VARCHAR NOT NULL,
      axis           VARCHAR NOT NULL,
      signal_completeness_pct DOUBLE,
      missing_sources JSON,
      confidence_class VARCHAR,
      computed_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (target_id, axis)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_failures (
      target_id      VARCHAR NOT NULL,
      repo_id        VARCHAR,
      tool           VARCHAR NOT NULL,
      tool_version   VARCHAR,
      class          VARCHAR NOT NULL,
      message        VARCHAR,
      occurred_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all tables and record schema version. Idempotent."""
    for ddl in DDL_STATEMENTS:
        conn.execute(ddl)
    existing = conn.execute(
        "SELECT COUNT(*) FROM schema_version WHERE version = ?",
        [SCHEMA_VERSION],
    ).fetchone()[0]
    if existing == 0:
        conn.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            [SCHEMA_VERSION],
        )
