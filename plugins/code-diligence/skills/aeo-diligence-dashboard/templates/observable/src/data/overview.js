import {html, svg} from "npm:htl";
import {classLabel, count, day, pct} from "./labels.js";
import {securityChart} from "./charts.js";

const OWNER_COLORS = ["#385bc5", "#94a5c5", "#277a78", "#b87438", "#8566a2", "#587a56"];
const month = new Intl.DateTimeFormat(undefined, {month: "short", timeZone: "UTC"});
const monthYear = new Intl.DateTimeFormat(undefined, {month: "short", year: "numeric", timeZone: "UTC"});
const shortDate = new Intl.DateTimeFormat(undefined, {month: "short", day: "numeric"});
const share = value => value > 0 && value < 0.001 ? "<0.1%" : pct(value);
const plural = (value, singular, multiple = `${singular}s`) => `${count(value)} ${value === 1 ? singular : multiple}`;
const compactLines = value => value < 1000 ? count(value) : `${(value / 1000).toFixed(1)}k`;

function source(name) {
  return html`<span class="dashboard-source">Source: <strong>${name}</strong></span>`;
}

function heading(id, title, href, provider) {
  return html`<div class="panel-head"><h2 id=${id}><a href=${href}>${title}</a></h2>${source(provider)}</div>`;
}

function healthBand(score) {
  if (score >= 8.5) return {label: "Excellent", color: "#26734f"};
  if (score >= 7) return {label: "Good", color: "#26734f"};
  if (score >= 5.5) return {label: "Fair", color: "#8a6e00"};
  if (score >= 4) return {label: "Needs work", color: "#b35c16"};
  return {label: "At risk", color: "#a73f49"};
}

function healthBar(label, score) {
  if (score === null) return html`<div class="dashboard-empty">${label}: not collected</div>`;
  const band = healthBand(score);
  return html`<div class="health-bar-row" style=${{color: band.color}} aria-label=${`${label}: ${score.toFixed(1)} out of 10, ${band.label}`}>
    <span class="health-measure">${label}</span><div class="health-track"><div class="health-fill" style=${{width: `${score * 10}%`, background: band.color}}></div></div>
    <b class="health-value">${score.toFixed(1)}</b><span class="health-grade">${band.label}</span>
  </div>`;
}

function ownershipGroups(rows, nameOf) {
  const people = rows.filter(row => row.class !== "bot").map(row => ({
    name: nameOf(row.person), role: classLabel(row.class).toLowerCase(), value: row.owned_loc,
  }));
  const automated = rows.filter(row => row.class === "bot").reduce((sum, row) => sum + row.owned_loc, 0);
  if (automated) people.push({name: "Automation accounts", role: "", value: automated});
  return people.sort((a, b) => b.value - a.value).map((row, index) => ({...row, color: OWNER_COLORS[index % OWNER_COLORS.length]}));
}

function ownershipChart(groups, total) {
  const circumference = 2 * Math.PI * 66;
  let offset = 0;
  const segments = groups.map(group => {
    const length = group.value / total * circumference;
    const segment = svg`<circle cx="90" cy="90" r="66" fill="none" stroke=${group.color} stroke-width="22"
      stroke-dasharray=${`${length} ${circumference - length}`} stroke-dashoffset=${-offset} transform="rotate(-90 90 90)">
      <title>${group.name}: ${share(group.value / total)}</title></circle>`;
    offset += length;
    return segment;
  });
  return svg`<svg viewBox="0 0 180 180" role="img" aria-label=${`Share of surviving lines. ${groups.map(group => `${group.name}: ${share(group.value / total)}`).join(". ")}`}>
    ${segments}<text x="90" y="91" text-anchor="middle" class="ownership-value">${share(groups[0].value / total)}</text>
    <text x="90" y="113" text-anchor="middle" class="ownership-label">Largest share</text>
  </svg>`;
}

function activityTrack(value, maximum, color) {
  return html`<div class="activity-track"><span style=${{width: `${maximum === 0 ? 0 : value / maximum * 100}%`, background: color}}></span></div>`;
}

function historyRange(repositories) {
  const starts = repositories.map(row => row.first_commit_at).filter(Boolean).map(value => new Date(value)).sort((a, b) => a - b);
  if (!starts.length) return "Not collected";
  const first = monthYear.format(starts[0]);
  const last = monthYear.format(starts.at(-1));
  return first === last ? first : `${first}–${last}`;
}

export function overview({targetId, target, repositories, ownership, people, ages, health, ci, activity, security, labels, nameOf, width, invalidation}) {
  const repoLabel = name => labels.repositories?.[name] ?? name;
  const workflowLabel = name => labels.workflows?.[name] ?? name;
  const groups = ownershipGroups(ownership, nameOf);
  const totalOwned = groups.reduce((sum, row) => sum + row.value, 0);
  const codeLines = ages.reduce((sum, row) => sum + row.surviving_loc, 0);
  const scoredFiles = health.reduce((sum, row) => sum + row.file_count, 0);
  const classes = ["fte", "contractor", "unknown"];
  const headcount = people.filter(row => row.class !== "bot").sort((a, b) => classes.indexOf(a.class) - classes.indexOf(b.class)).map(row => plural(row.people,
    {fte: "employee", contractor: "contractor", unknown: "unclassified contributor"}[row.class] ?? row.class));
  const runs = ci.reduce((sum, row) => sum + row.runs, 0);
  const passed = ci.reduce((sum, row) => sum + row.passed, 0);
  const noRuns = repositories.filter(repo => !ci.some(row => row.repo === repo.name));
  const runDates = ci.flatMap(row => [row.first_run_at, row.last_run_at]).filter(Boolean).map(value => new Date(value)).sort((a, b) => a - b);
  const commits = activity.reduce((sum, row) => sum + row.commits, 0);
  const maxCommits = Math.max(0, ...activity.map(row => row.commits));
  const maxLines = Math.max(0, ...activity.flatMap(row => [row.added, row.removed]));
  const multipleYears = new Set(activity.map(row => row.month.slice(0, 4))).size > 1;
  const monthFormat = multipleYears ? monthYear : month;
  const through = target.last_refreshed_at ? shortDate.format(new Date(target.last_refreshed_at)) : "collection date unavailable";
  return html`<div class="dashboard-overview">
    <div class="dashboard-meta">Code data: ${target.last_refreshed_at ? day(target.last_refreshed_at) : "not collected"}${security.as_of ? ` · Security: ${day(security.as_of)}` : ""}</div>
    <div class="dashboard-scope"><span><strong>${count(repositories.length)}</strong> repositories</span><span><strong>${ages.length ? count(codeLines) : "Not collected"}</strong> lines of code</span><strong>${headcount.join(" · ") || "No contributors recorded"}</strong><span>Repository history starts <strong>${historyRange(repositories)}</strong></span></div>
    <div class="board-top">
      <section class="panel ownership" aria-labelledby="ownership-title">
        ${heading("ownership-title", "Code ownership", `${targetId}/people.html#knowledge-concentration`, "git-fame")}
        <p class="subhead">Share of surviving lines, all file types</p>
        ${totalOwned ? html`<div class="ownership-visual">${ownershipChart(groups, totalOwned)}</div><ul class="owner-list">${groups.map(group => html`<li><i class="owner-dot" style=${{background: group.color}}></i><span>${group.name}${group.role ? html`<span class="owner-role"> · ${group.role}</span>` : ""}</span><strong>${share(group.value / totalOwned)}</strong></li>`)}</ul>` : html`<p class="dashboard-empty">Ownership has not been collected.</p>`}
        <p class="panel-source">${count(totalOwned)} surviving lines</p>
      </section>
      <section class="panel health" aria-labelledby="health-title">
        ${heading("health-title", "Code health", `${targetId}/product.html#code-health`, "Repowise")}
        <p class="subhead">Scores out of 10 · Higher is healthier</p>
        ${health.length ? health.map(row => html`<div class="health-row"><div class="health-repo" title=${row.repo}>${repoLabel(row.repo)}</div><div class="health-bars">${healthBar("Average", row.average_health)}${healthBar("Hotspots", row.hotspot_health)}</div></div>`) : html`<p class="dashboard-empty">Code health has not been collected.</p>`}
        <p class="panel-source">${count(scoredFiles)} files scored<br>Hotspots: the most-changed code</p>
      </section>
    </div>
    <div class="board-bottom">
      <section class="panel ci" aria-labelledby="ci-title">
        ${heading("ci-title", "CI results", `${targetId}/process.html#ci-health`, "GitHub Actions")}
        ${runs ? html`<div class="ci-top"><div class="ci-total"><strong>${pct(passed / runs)}</strong><span>passed · ${count(runs)} completed runs</span></div><div class="ci-legend"><span><i style="background:#385bc5"></i>Passed</span><span><i style="background:#d2dae5"></i>Other</span></div></div>
        <div class="ci-head"><span>Workflow</span><span></span><span>Passed</span><span>Last run</span></div>
        ${ci.map(row => html`<div class="ci-row"><div class="ci-name" title=${row.repo}>${repoLabel(row.repo)}<small title=${row.workflow_name}>${workflowLabel(row.workflow_name)} · ${count(row.runs)} runs</small></div><div class="ci-track" title=${`${count(row.passed)} of ${count(row.runs)} passed`}><span style=${{width: `${row.success_rate * 100}%`}}></span></div><div class="ci-pct">${pct(row.success_rate)}</div><div class="ci-date">${row.last_run_at ? shortDate.format(new Date(row.last_run_at)) : "Unknown"}</div></div>`)}` : ""}
        ${noRuns.map(repo => html`<div class="no-runs"><strong>${repoLabel(repo.name)}</strong><span>No Actions runs recorded</span></div>`)}
        <p class="panel-source">${runDates.length ? `${shortDate.format(runDates[0])}–${shortDate.format(runDates.at(-1))} · ` : ""}Other includes cancelled runs</p>
      </section>
      <section class="panel activity" aria-labelledby="activity-title">
        ${heading("activity-title", "Development activity", `${targetId}/people.html#contributor-activity-timeline`, "Git history")}
        <div class="activity-total"><strong>${count(commits)}</strong><span>commits across ${plural(repositories.length, "repository", "repositories")}</span></div>
        ${activity.length ? html`<div class="activity-columns"><span></span><strong>Commits</strong><div><strong>LOC changed</strong><div class="activity-keys"><span>+ Added</span><span>− Removed</span></div></div></div>
        ${activity.map(row => html`<div class="activity-month" aria-label=${`${monthYear.format(new Date(row.month))}: ${count(row.commits)} commits, ${count(row.added)} code lines added and ${count(row.removed)} removed`}><span class="activity-month-name">${monthFormat.format(new Date(row.month))}</span><div class="activity-metric"><div class="activity-value">${count(row.commits)}</div>${activityTrack(row.commits, maxCommits, "#385bc5")}</div><div class="activity-metric" title=${`${count(row.added)} code lines added; ${count(row.removed)} removed`}><div class="activity-value loc-values"><span>+${compactLines(row.added)}</span><span>−${compactLines(row.removed)}</span></div><div class="loc-tracks">${activityTrack(row.added, maxLines, "#277a78")}${activityTrack(row.removed, maxLines, "#b87438")}</div></div></div>`)}` : html`<p class="dashboard-empty">Commit history has not been collected.</p>`}
        <p class="panel-source">LOC counts code files · Through ${through}<br>Commits and LOC use separate scales</p>
      </section>
    </div>
    <section class="board-security" aria-labelledby="security-title">
      ${heading("security-title", "Security", `${targetId}/product.html#security-findings`, security.source)}
      ${security.periods.length ? securityChart(security, {width: Math.min(width, 1040), height: 440, invalidation}) : html`<p class="dashboard-empty">Security findings have not been collected.</p>`}
    </section>
  </div>`;
}
