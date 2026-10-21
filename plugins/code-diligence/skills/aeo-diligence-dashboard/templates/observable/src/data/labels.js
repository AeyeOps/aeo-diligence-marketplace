import {html} from "npm:htl";
import {FileAttachment} from "observablehq:stdlib";
import {query} from "./warehouse.js";

const percent = new Intl.NumberFormat(undefined, {style: "percent", maximumFractionDigits: 1});
const whole = new Intl.NumberFormat();

export const pct = value => typeof value === "number" ? percent.format(value) : value;
export const count = value => typeof value === "number" ? whole.format(value) : value;
export const hours = value => typeof value === "number" ? `${value.toFixed(1)} h` : value;
export const day = value => value ? new Date(value).toLocaleDateString(undefined, {year: "numeric", month: "short", day: "numeric"}) : "";
export const when = value => value ? new Date(value).toLocaleString(undefined, {dateStyle: "medium", timeStyle: "short"}) : "";
export const wrap = value => html`<span class="wrap">${value}</span>`;

export function duration(seconds) {
  if (typeof seconds !== "number") return seconds;
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  return minutes ? `${minutes}m ${String(total % 60).padStart(2, "0")}s` : `${total}s`;
}

const CLASS_LABELS = {fte: "Employee", contractor: "Contractor", bot: "Bot", unknown: "Unclassified"};
export const CLASS_ORDER = Object.values(CLASS_LABELS);
export const classLabel = value => CLASS_LABELS[value ?? "unknown"] ?? value;

const REPO_CLASS_LABELS = {production: "Production", tooling: "Tooling", experiment: "Experiment", abandoned: "Abandoned", docs: "Docs", fork: "Fork", unknown: "Unclassified"};
export const repoClassLabel = value => REPO_CLASS_LABELS[value ?? "unknown"] ?? value;

const SOURCE_LABELS = {
  commits_fact: "Git history",
  ownership_share: "Ownership (git-fame)",
  contributor_classification: "Contributor labels",
  file_metrics: "File changes",
  coupling_pairs: "Coupling (code-maat)",
  code_age_buckets: "Code age (git-of-theseus)",
  burndown_series: "Code survival (hercules)",
  pr_metrics: "Pull requests",
  actions_metrics: "CI runs",
  release_metrics: "GitHub releases",
  issue_metrics: "GitHub issues",
};
export const sourceLabel = value => SOURCE_LABELS[value] ?? value;

const SEVERITY_LABELS = {CRITICAL: "Critical", HIGH: "High", MEDIUM: "Medium", LOW: "Low", INFORMATIONAL: "Informational", UNTRIAGED: "Untriaged", UNKNOWN: "Unknown"};
export const SEVERITY_ORDER = Object.values(SEVERITY_LABELS);
export const SEVERITY_COLORS = ["#8f1d21", "#d9480f", "#e8a317", "#6f8aa6", "#aab4bf", "#cfd5db", "#777d87"];
export const severityLabel = value => SEVERITY_LABELS[value] ?? value;
export const monthLabel = value => new Date(value).toLocaleDateString(undefined, {month: "short", year: "numeric", timeZone: "UTC"});

export function missingSources(confidence) {
  return JSON.parse(confidence.missing_sources ?? "[]").map(sourceLabel);
}

export function confidenceLine(confidence) {
  const level = confidence.confidence_class[0].toUpperCase() + confidence.confidence_class.slice(1);
  const missing = missingSources(confidence);
  return `${level} confidence · ${missing.length ? `missing ${missing.join(", ")}` : "all sources present"}`;
}

export async function targetName(targetId) {
  const rows = await query("SELECT name FROM targets WHERE target_id = ?", [targetId]);
  return rows[0]?.name ?? targetId;
}

export async function personNames(targetId) {
  const config = await FileAttachment("./config.json").json();
  const labels = config.display_labels[targetId]?.contributors ?? {};
  const rows = await query(`
    SELECT COALESCE(im.canonical_email, a.author_email) AS person, a.author_email, a.display_name
    FROM authors a
    LEFT JOIN identity_map im ON im.target_id = a.target_id AND im.raw_email = a.author_email
    WHERE a.target_id = ?
    ORDER BY (a.author_email = COALESCE(im.canonical_email, a.author_email)) DESC, a.total_commits DESC
  `, [targetId]);
  const canonical = new Map(rows.map(row => [row.author_email, row.person]));
  const names = new Map();
  for (const row of rows) if (!names.has(row.person) && row.display_name) names.set(row.person, row.display_name);
  return email => {
    const person = canonical.get(email) ?? email;
    return labels[person] ?? names.get(person) ?? email;
  };
}
