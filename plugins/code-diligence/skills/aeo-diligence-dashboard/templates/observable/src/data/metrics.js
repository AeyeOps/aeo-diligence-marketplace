import {query} from "./warehouse.js";

export const SINGLE_OWNER_SHARE = 0.9;

export function busFactor(targetId) {
  return query(`
    WITH ownership AS (
      SELECT r.repo_id, r.name AS repo,
             COALESCE(im.canonical_email, os.author_email) AS author,
             SUM(os.owned_loc) AS owned_loc,
             cc.class AS contributor_class
      FROM repos r
      JOIN ownership_share os ON os.repo_id = r.repo_id AND os.source = 'git-fame'
      LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = os.author_email
      LEFT JOIN contributor_classification cc ON cc.target_id = r.target_id AND cc.author_email = COALESCE(im.canonical_email, os.author_email)
      JOIN repo_classification rc ON rc.repo_id = r.repo_id
      WHERE r.target_id = ? AND rc.class IN ('production', 'tooling')
      GROUP BY r.repo_id, r.name, author, cc.class
    ), totals AS (
      SELECT repo_id, repo, SUM(owned_loc) AS total_loc FROM ownership GROUP BY repo_id, repo
    ), ranked AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY owned_loc DESC, author) AS author_rank,
             SUM(owned_loc) OVER (PARTITION BY repo_id ORDER BY owned_loc DESC, author) AS cumulative_loc
      FROM ownership WHERE contributor_class = 'fte'
    )
    SELECT totals.repo, COUNT(ranked.author) AS confirmed_ftes,
           MIN(CASE WHEN cumulative_loc >= totals.total_loc * 0.5 AND totals.total_loc > 0 THEN author_rank END) AS bus_factor_estimate
    FROM totals LEFT JOIN ranked ON ranked.repo_id = totals.repo_id
    GROUP BY totals.repo_id, totals.repo ORDER BY bus_factor_estimate, totals.repo
  `, [targetId]);
}

export function ownershipByPerson(targetId) {
  return query(`
    SELECT COALESCE(im.canonical_email, os.author_email) AS person, SUM(os.owned_loc) AS owned_loc
    FROM ownership_share os
    JOIN repos r ON r.repo_id = os.repo_id
    LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = os.author_email
    WHERE r.target_id = ? AND os.source = 'git-fame'
    GROUP BY 1 HAVING SUM(os.owned_loc) > 0 ORDER BY owned_loc DESC
  `, [targetId]);
}

export function peopleByLabel(targetId) {
  return query(`
    SELECT COALESCE(cc.class, 'unknown') AS class, COUNT(DISTINCT COALESCE(im.canonical_email, cf.author_email)) AS people
    FROM commits_fact cf
    JOIN repos r ON r.repo_id = cf.repo_id
    LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = cf.author_email
    LEFT JOIN contributor_classification cc ON cc.target_id = r.target_id AND cc.author_email = COALESCE(im.canonical_email, cf.author_email)
    WHERE r.target_id = ?
    GROUP BY 1
  `, [targetId]);
}

export function heroFiles(targetId) {
  return query(`
    SELECT r.name AS repo, fm.path AS file,
           COALESCE(im.canonical_email, fm.top_owner_email) AS owner,
           fm.top_owner_pct AS owned_pct, fm.revisions
    FROM file_metrics fm
    JOIN repos r ON r.repo_id = fm.repo_id
    LEFT JOIN identity_map im ON im.target_id = r.target_id AND im.raw_email = fm.top_owner_email
    WHERE r.target_id = ? AND fm.top_owner_pct >= ${SINGLE_OWNER_SHARE}
    ORDER BY fm.top_owner_pct DESC, fm.revisions DESC
    LIMIT 50
  `, [targetId]);
}

export async function singleOwnerFiles(targetId) {
  const [row] = await query(`
    SELECT COUNT(*) FILTER (WHERE fm.top_owner_pct >= ${SINGLE_OWNER_SHARE}) AS single_owner, COUNT(*) AS files
    FROM file_metrics fm JOIN repos r ON r.repo_id = fm.repo_id
    WHERE r.target_id = ?
  `, [targetId]);
  return row;
}

export function hotspots(targetId) {
  return query(`
    SELECT r.name AS repo, fm.path, fm.revisions
    FROM file_metrics fm
    JOIN repos r ON r.repo_id = fm.repo_id
    JOIN repo_classification rc ON rc.repo_id = fm.repo_id
    WHERE r.target_id = ? AND rc.class IN ('production', 'tooling')
    ORDER BY fm.revisions DESC, fm.path LIMIT 25
  `, [targetId]);
}

export function couplings(targetId) {
  return query(`
    SELECT r.name AS repo, cp.file_a, cp.file_b, cp.co_change_count, cp.support_pct, cp.lift
    FROM coupling_pairs cp
    JOIN repos r ON r.repo_id = cp.repo_id
    WHERE r.target_id = ? AND cp.lift > 1.5 AND cp.support_pct > 0.05
    ORDER BY cp.lift DESC LIMIT 100
  `, [targetId]);
}

export function codeAge(targetId) {
  return query(`
    SELECT r.name AS repo, cab.bucket_start_year AS year, SUM(cab.surviving_loc) AS surviving_loc
    FROM code_age_buckets cab
    JOIN repos r ON r.repo_id = cab.repo_id
    WHERE r.target_id = ?
    GROUP BY 1, 2 ORDER BY 2, 1
  `, [targetId]);
}

export function abandonedRepos(targetId) {
  return query(`
    SELECT r.name AS repo, r.last_commit_at, r.is_archived,
           (SELECT cf.author_email FROM commits_fact cf WHERE cf.repo_id = r.repo_id ORDER BY cf.author_date DESC LIMIT 1) AS last_author,
           (SELECT cf.message_first_line FROM commits_fact cf WHERE cf.repo_id = r.repo_id ORDER BY cf.author_date DESC LIMIT 1) AS last_msg
    FROM repos r JOIN repo_classification rc ON rc.repo_id = r.repo_id
    WHERE r.target_id = ? AND rc.class = 'abandoned'
    ORDER BY r.last_commit_at ASC
  `, [targetId]);
}

export function delivery(targetId) {
  return query(`
    SELECT r.name AS repo,
           (SELECT COUNT(*) FROM release_metrics rm WHERE rm.repo_id = r.repo_id
             AND rm.released_at >= CURRENT_DATE - INTERVAL '30 days') AS releases_l30d,
           (SELECT COUNT(*) FROM release_metrics rm WHERE rm.repo_id = r.repo_id) AS releases_total,
           (SELECT COUNT(*) FROM pr_metrics pm WHERE pm.repo_id = r.repo_id AND pm.merged_at IS NOT NULL) AS merged_prs,
           (SELECT AVG(EXTRACT(EPOCH FROM (pm.merged_at - pm.opened_at))/3600.0)
             FROM pr_metrics pm WHERE pm.repo_id = r.repo_id AND pm.merged_at IS NOT NULL) AS avg_pr_cycle_time_h,
           (SELECT 1.0 - AVG(CASE WHEN am.conclusion='success' THEN 1.0 ELSE 0.0 END)
             FROM actions_metrics am WHERE am.repo_id = r.repo_id AND am.conclusion IS NOT NULL) AS workflow_failure_rate
    FROM repos r WHERE r.target_id = ? ORDER BY r.name
  `, [targetId]);
}

export function ciHealth(targetId) {
  return query(`
    SELECT r.name AS repo, am.workflow_name, COUNT(*) AS runs,
           AVG(CASE WHEN am.conclusion='success' THEN 1.0 ELSE 0.0 END) AS success_rate,
           AVG(am.duration_seconds) AS avg_duration_s
    FROM actions_metrics am JOIN repos r ON r.repo_id = am.repo_id
    WHERE r.target_id = ? AND am.conclusion IS NOT NULL GROUP BY r.repo_id, r.name, am.workflow_name
    ORDER BY runs DESC
  `, [targetId]);
}

export function issueTriage(targetId) {
  return query(`
    SELECT r.name AS repo,
           COUNT(*) AS total_issues,
           AVG(im.days_to_first_response) AS avg_first_response_days,
           SUM(CASE WHEN im.state='open' AND im.opened_at < CURRENT_DATE - INTERVAL '90 days' THEN 1 ELSE 0 END) AS stale_open
    FROM issue_metrics im JOIN repos r ON r.repo_id = im.repo_id
    WHERE r.target_id = ? GROUP BY r.repo_id, r.name ORDER BY r.name
  `, [targetId]);
}
