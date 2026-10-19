# ${target.name}

```js
import {query, axisConfidence, headlines} from "../data/warehouse.js";
import {abandonedRepos, busFactor, ciHealth, codeAge, codeHealth, couplings, delivery, hotspots, issueTriage, ownershipByPerson, peopleByLabel, securityMonthly, singleOwnerFiles} from "../data/metrics.js";
import {confidenceLine, count, day, hours, pct, personNames, severityLabel, when, wrap} from "../data/labels.js";
import {securityChart} from "../data/charts.js";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const config = await FileAttachment("../data/config.json").json();
const cards = (await headlines(target_id))
  .filter(card => card.section_key !== "working_pattern_signals" || config.allow_working_pattern_card);
const card_by_key = Object.fromEntries(cards.map(card => [card.section_key, card]));
const confidence = Object.fromEntries(await Promise.all(
  ["people", "product", "process"].map(async axis => [axis, await axisConfidence(target_id, axis)])
));
const nameOf = await personNames(target_id);
const [bus, ownership, labels, single, ages, health, hot, pairs, abandoned, repo_rows, ci_rows, issue_rows, security] = await Promise.all([
  busFactor(target_id), ownershipByPerson(target_id), peopleByLabel(target_id), singleOwnerFiles(target_id),
  codeAge(target_id), codeHealth(target_id), hotspots(target_id), couplings(target_id),
  abandonedRepos(target_id), delivery(target_id), ciHealth(target_id), issueTriage(target_id), securityMonthly(target_id),
]);

function findings(axis) {
  return html`<dl class="headlines">${cards.filter(card => card.axis === axis).flatMap(card => [
    html`<dt><a href="${target_id}/${axis}.html#${card.anchor}">${card.title}</a></dt>`,
    html`<dd>${card.headline}</dd>`,
  ])}</dl>`;
}

function area(axis, title, rows, status = confidenceLine(confidence[axis])) {
  return html`<section class="summary-area">
    <h3><a href="${target_id}/${axis}.html">${title}</a></h3>
    <p class="summary-confidence">${status}</p>
    <dl>${rows.filter(Boolean).map(([section_key, label, value, note, source]) => html`<div class="summary-row">
      <dt><a href="${target_id}/${card_by_key[section_key].axis}.html#${card_by_key[section_key].anchor}">${label}</a><span>${source ? html`<b class="summary-source">${source}</b> · ` : ""}${note}</span></dt>
      <dd>${value}</dd>
    </div>`)}</dl>
  </section>`;
}
```

<p class="subtitle">${target.description ?? ""}${target.description ? " · " : ""}Refreshed ${when(target.last_refreshed_at) || "never"}</p>

## Summary

```js
const established = bus.filter(row => row.bus_factor_estimate !== null);
const lowest = established.length ? Math.min(...established.map(row => row.bus_factor_estimate)) : null;
const at_lowest = established.filter(row => row.bus_factor_estimate === lowest).length;
const unestablished = bus.length - established.length;
const owned_total = ownership.reduce((sum, row) => sum + row.owned_loc, 0);
const employees = labels.find(row => row.class === "fte")?.people ?? 0;
const NOUNS = {contractor: ["contractor", "contractors"], bot: ["bot", "bots"], unknown: ["unclassified person", "unclassified people"]};
const others = labels.filter(row => row.class !== "fte" && row.people > 0)
  .map(row => `${row.people} ${(NOUNS[row.class] ?? [row.class, row.class])[row.people === 1 ? 0 : 1]}`);
const code_lines = ages.reduce((sum, row) => sum + row.surviving_loc, 0);
const scored_files = health.reduce((sum, row) => sum + row.file_count, 0);
const average_health = scored_files ? health.reduce((sum, row) => sum + row.average_health * row.file_count, 0) / scored_files : null;
const runs = ci_rows.reduce((sum, row) => sum + row.runs, 0);
const passing = runs ? ci_rows.reduce((sum, row) => sum + row.runs * row.success_rate, 0) / runs : null;
const merged = repo_rows.reduce((sum, row) => sum + row.merged_prs, 0);
const cycle = merged ? repo_rows.reduce((sum, row) => sum + row.merged_prs * (row.avg_pr_cycle_time_h ?? 0), 0) / merged : null;
const releases = repo_rows.reduce((sum, row) => sum + row.releases_l30d, 0);
const uses_releases = repo_rows.some(row => row.releases_total > 0);
const issues = issue_rows.reduce((sum, row) => sum + row.total_issues, 0);
const stale = issue_rows.reduce((sum, row) => sum + row.stale_open, 0);
const coverage = Array.from(
  security.reduce((starts, row) => starts.set(row.severity, Math.min(starts.get(row.severity) ?? Infinity, +row.first_read_at)), new Map()),
  ([sev, start]) => ({sev, start})
).reduce((groups, {sev, start}) => groups.set(start, [...(groups.get(start) ?? []), severityLabel(sev).toLowerCase()]), new Map());
const covered = [];
const coverage_line = Array.from(coverage).sort(([a], [b]) => a - b).map(([start, names]) => {
  covered.push(...names);
  return `${covered.length === 6 ? "all severities" : covered.join(" and ")} since ${day(start)}`;
}).join("; ");

display(html`<div class="summary">
  ${area("people", "People", [
    ["bus_factor_map", "Bus factor", lowest ?? "Not established",
      lowest === null
        ? `in all ${bus.length} repositories`
        : `in ${at_lowest} of ${bus.length} repositories${unestablished ? `; not established in ${unestablished}` : ""}`,
      "git-fame"],
    ownership.length && ["knowledge_concentration", "Largest owner", pct(ownership[0].owned_loc / owned_total), `${nameOf(ownership[0].person)}, share of all lines`, "git-fame"],
    ["contributor_activity_timeline", "Employees", count(employees), others.length ? `plus ${others.join(", ")}` : "no other contributors", null],
    ["hero_dependency_register", "Single-owner files", pct(single.single_owner / single.files), `${count(single.single_owner)} of ${count(single.files)} files that exist today`, "code-maat"],
  ])}
  ${area("product", "Product", [
    ["code_aging_chart", "Lines of code", count(code_lines), "code files only, no JSON, YAML, Markdown or text", "git-of-theseus"],
    ["knowledge_concentration", "Lines in all files", count(owned_total), "includes JSON, Markdown and data files", "git-fame"],
    ["code_health", "Code health", average_health === null ? "Not collected" : `${average_health.toFixed(1)} of 10`, `average over ${count(scored_files)} files, higher is healthier`, "Repowise"],
    hot.length && ["hotspot_map", "Most changes to one file", count(hot[0].revisions), wrap(hot[0].path), "code-maat"],
    ["hidden_coupling_matrix", "Hidden couplings", count(pairs.length), "file pairs that change together", "code-maat"],
    ["abandoned_area_register", "Abandoned repositories", count(abandoned.length), `of ${repo_rows.length}`, null],
  ])}
  ${area("process", "Process", [
    ["ci_health", "CI runs passing", passing === null ? "No runs" : pct(passing), `of ${count(runs)} completed runs`, "GitHub Actions"],
    ["dora_quadrant", "PR open to merge", cycle === null ? "No merged PRs" : hours(cycle), `average over ${count(merged)} merged PRs`, "GitHub"],
    uses_releases && ["dora_quadrant", "GitHub releases", count(releases), "in the last 30 days", "GitHub"],
    ["issue_triage_health", "Issues open over 90 days", count(stale), issues ? `of ${count(issues)} GitHub issues` : "no GitHub issues recorded", "GitHub Issues"],
  ])}
  ${security.length ? html`<section class="summary-area summary-wide">
    <h3><a href="${target_id}/process.html#${card_by_key.security_findings.anchor}">Security</a></h3>
    <p class="summary-confidence"><b class="summary-source">AWS Inspector</b> · fixable findings per month · ${coverage_line}</p>
    ${securityChart(security, {width: Math.min(width, 1040), height: 220})}
  </section>` : ""}
</div>`);
```

## People

```js
display(findings("people"));
```

## Product

```js
display(findings("product"));
```

## Process

```js
display(findings("process"));
```
