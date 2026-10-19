# ${target.name}

```js
import {query, axisConfidence, headlines} from "../data/warehouse.js";
import {abandonedRepos, busFactor, ciByMonth, ciHealth, codeAge, couplings, delivery, hotspots, issueTriage, ownershipByPerson, peopleByLabel, singleOwnerFiles} from "../data/metrics.js";
import {confidenceLine, count, hours, pct, personNames, when, wrap} from "../data/labels.js";
import * as Plot from "npm:@observablehq/plot";

const target_id = observable.params.target;
const target = (await query(`SELECT name, description, last_refreshed_at FROM targets WHERE target_id = ?`, [target_id]))[0];
const config = await FileAttachment("../data/config.json").json();
const cards = (await headlines(target_id))
  .filter(card => card.section_key !== "working_pattern_signals" || config.allow_working_pattern_card);
const anchor = Object.fromEntries(cards.map(card => [card.section_key, card.anchor]));
const confidence = Object.fromEntries(await Promise.all(
  ["people", "product", "process"].map(async axis => [axis, await axisConfidence(target_id, axis)])
));
const nameOf = await personNames(target_id);

function measure(axis, section_key, label, value, note) {
  return html`<a class="measure" href="${target_id}/${axis}.html#${anchor[section_key]}">
    <span class="measure-label">${label}</span>
    <span class="measure-value">${value}</span>
    <span class="measure-note">${note}</span>
  </a>`;
}

function findings(axis) {
  return html`<dl class="headlines">${cards.filter(card => card.axis === axis).flatMap(card => [
    html`<dt><a href="${target_id}/${axis}.html#${card.anchor}">${card.title}</a></dt>`,
    html`<dd>${card.headline}</dd>`,
  ])}</dl>`;
}

function shareBars(rows, label) {
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const data = rows.map(row => ({...row, share: row.value / total}));
  return Plot.plot({
    marks: [
      Plot.barX(data, {x: "share", y: "name", sort: {y: "-x"}, fill: "var(--theme-foreground-focus)"}),
      Plot.text(data, {x: "share", y: "name", text: row => row.share > 0 && row.share < 0.001 ? "<0.1%" : pct(row.share), textAnchor: "start", dx: 6, fill: "currentColor"}),
    ],
    x: {domain: [0, 1], axis: null},
    y: {label: null},
    marginLeft: 190,
    marginRight: 60,
    width: Math.min(width, 640),
    height: 30 * data.length + 20,
    ariaLabel: label,
  });
}
```

<p class="subtitle">${target.description ?? ""}${target.description ? " · " : ""}Refreshed ${when(target.last_refreshed_at) || "never"}</p>

## People

```js
const [bus, ownership, labels, single] = await Promise.all([
  busFactor(target_id), ownershipByPerson(target_id), peopleByLabel(target_id), singleOwnerFiles(target_id),
]);
```

```js
const established = bus.filter(row => row.bus_factor_estimate !== null);
const lowest = established.length ? Math.min(...established.map(row => row.bus_factor_estimate)) : null;
const at_lowest = established.filter(row => row.bus_factor_estimate === lowest).length;
const unestablished = bus.length - established.length;
const employees = labels.find(row => row.class === "fte")?.people ?? 0;
const NOUNS = {contractor: ["contractor", "contractors"], bot: ["bot", "bots"], unknown: ["unclassified person", "unclassified people"]};
const others = labels.filter(row => row.class !== "fte" && row.people > 0)
  .map(row => `${row.people} ${(NOUNS[row.class] ?? [row.class, row.class])[row.people === 1 ? 0 : 1]}`);

display(html`<p class="subtitle">${confidenceLine(confidence.people)}</p>`);
display(html`<div class="measures">
  ${measure("people", "bus_factor_map", "Bus factor", lowest ?? "Not established",
    lowest === null
      ? `in all ${bus.length} repositories`
      : `in ${at_lowest} of ${bus.length} repositories${unestablished ? `; not established in ${unestablished}` : ""}`)}
  ${measure("people", "contributor_activity_timeline", "Employees", count(employees), others.length ? `plus ${others.join(", ")}` : "no other contributors")}
  ${measure("people", "hero_dependency_register", "Single-owner files", pct(single.single_owner / single.files), `${count(single.single_owner)} of ${count(single.files)} files`)}
</div>`);
display(shareBars(ownership.map(row => ({name: nameOf(row.person), value: row.owned_loc})), "Share of surviving lines by person"));
display(html`<p class="caption">Share of surviving lines held by each person across all repositories (git-fame), after identity merges.</p>`);
display(findings("people"));
```

## Product

```js
const [ages, hot, pairs, abandoned, repo_rows] = await Promise.all([
  codeAge(target_id), hotspots(target_id), couplings(target_id), abandonedRepos(target_id), delivery(target_id),
]);
```

```js
const lines_by_repo = Array.from(
  ages.reduce((totals, row) => totals.set(row.repo, (totals.get(row.repo) ?? 0) + row.surviving_loc), new Map()),
  ([name, value]) => ({name, value})
);
const source_lines = lines_by_repo.reduce((sum, row) => sum + row.value, 0);

display(html`<p class="subtitle">${confidenceLine(confidence.product)}</p>`);
display(html`<div class="measures">
  ${measure("product", "code_aging_chart", "Source lines", count(source_lines), `surviving today across ${lines_by_repo.length} repositories`)}
  ${measure("product", "hotspot_map", "Most-changed file", hot.length ? `${count(hot[0].revisions)} changes` : "None", hot.length ? wrap(hot[0].path) : "no file history")}
  ${measure("product", "hidden_coupling_matrix", "Hidden couplings", count(pairs.length), "file pairs that change together")}
  ${measure("product", "abandoned_area_register", "Abandoned repositories", count(abandoned.length), `of ${repo_rows.length}`)}
</div>`);
if (lines_by_repo.length) {
  display(shareBars(lines_by_repo, "Share of surviving source lines by repository"));
  display(html`<p class="caption">Share of surviving source lines in each repository (git-of-theseus).</p>`);
}
display(findings("product"));
```

## Process

```js
const [ci_rows, ci_months, issue_rows] = await Promise.all([ciHealth(target_id), ciByMonth(target_id), issueTriage(target_id)]);
```

```js
const runs = ci_rows.reduce((sum, row) => sum + row.runs, 0);
const passing = runs ? ci_rows.reduce((sum, row) => sum + row.runs * row.success_rate, 0) / runs : null;
const merged = repo_rows.reduce((sum, row) => sum + row.merged_prs, 0);
const cycle = merged ? repo_rows.reduce((sum, row) => sum + row.merged_prs * (row.avg_pr_cycle_time_h ?? 0), 0) / merged : null;
const releases = repo_rows.reduce((sum, row) => sum + row.releases_l30d, 0);
const uses_releases = repo_rows.some(row => row.releases_total > 0);
const issues = issue_rows.reduce((sum, row) => sum + row.total_issues, 0);
const stale = issue_rows.reduce((sum, row) => sum + row.stale_open, 0);

display(html`<p class="subtitle">${confidenceLine(confidence.process)}</p>`);
display(html`<div class="measures">
  ${measure("process", "ci_health", "CI runs passing", passing === null ? "No runs" : pct(passing), `of ${count(runs)} completed runs`)}
  ${measure("process", "dora_quadrant", "PR open to merge", cycle === null ? "No merged PRs" : hours(cycle), `average over ${count(merged)} merged PRs`)}
  ${uses_releases ? measure("process", "dora_quadrant", "GitHub releases", count(releases), "in the last 30 days") : ""}
  ${measure("process", "issue_triage_health", "Issues open over 90 days", count(stale), issues ? `of ${count(issues)} GitHub issues` : "no GitHub issues recorded")}
</div>`);
if (ci_months.length) {
  display(Plot.plot({
    marks: [
      Plot.rectY(ci_months, {x: "month", interval: "month", y: "success_rate", fill: "var(--theme-foreground-focus)", inset: 2, title: row => `${pct(row.success_rate)} of ${count(row.runs)} runs`}),
      Plot.text(ci_months, {x: row => new Date(+row.month + 14 * 864e5), y: "success_rate", text: row => pct(row.success_rate), dy: -8, fill: "currentColor"}),
      Plot.ruleY([0]),
    ],
    x: {label: null},
    y: {domain: [0, 1.1], label: null, axis: null},
    width: Math.min(width, 640),
    height: 160,
    ariaLabel: "Share of completed CI runs passing each month",
  }));
  display(html`<p class="caption">Completed GitHub Actions runs passing each month. A month with no runs has no bar.</p>`);
}
display(findings("process"));
```
