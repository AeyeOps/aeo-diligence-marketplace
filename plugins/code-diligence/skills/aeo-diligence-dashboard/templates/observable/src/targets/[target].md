# ${target.name}

```js
import {query, axisConfidence, headlines} from "../data/warehouse.js";
import {abandonedRepos, busFactor, ciHealth, codeAge, couplings, delivery, hotspots, issueTriage, ownershipByPerson, peopleByLabel, singleOwnerFiles} from "../data/metrics.js";
import {confidenceLine, count, hours, pct, personNames, when, wrap} from "../data/labels.js";

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
const [bus, ownership, labels, single, ages, hot, pairs, abandoned, repo_rows, ci_rows, issue_rows] = await Promise.all([
  busFactor(target_id), ownershipByPerson(target_id), peopleByLabel(target_id), singleOwnerFiles(target_id),
  codeAge(target_id), hotspots(target_id), couplings(target_id), abandonedRepos(target_id),
  delivery(target_id), ciHealth(target_id), issueTriage(target_id),
]);

function findings(axis) {
  return html`<dl class="headlines">${cards.filter(card => card.axis === axis).flatMap(card => [
    html`<dt><a href="${target_id}/${axis}.html#${card.anchor}">${card.title}</a></dt>`,
    html`<dd>${card.headline}</dd>`,
  ])}</dl>`;
}

function area(axis, title, rows) {
  return html`<section class="summary-area">
    <h3><a href="${target_id}/${axis}.html">${title}</a></h3>
    <p class="summary-confidence">${confidenceLine(confidence[axis])}</p>
    <dl>${rows.filter(Boolean).map(([section_key, label, value, note]) => html`<div class="summary-row">
      <dt><a href="${target_id}/${axis}.html#${anchor[section_key]}">${label}</a><span>${note}</span></dt>
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
const source_lines = ages.reduce((sum, row) => sum + row.surviving_loc, 0);
const source_repos = new Set(ages.map(row => row.repo)).size;
const runs = ci_rows.reduce((sum, row) => sum + row.runs, 0);
const passing = runs ? ci_rows.reduce((sum, row) => sum + row.runs * row.success_rate, 0) / runs : null;
const merged = repo_rows.reduce((sum, row) => sum + row.merged_prs, 0);
const cycle = merged ? repo_rows.reduce((sum, row) => sum + row.merged_prs * (row.avg_pr_cycle_time_h ?? 0), 0) / merged : null;
const releases = repo_rows.reduce((sum, row) => sum + row.releases_l30d, 0);
const uses_releases = repo_rows.some(row => row.releases_total > 0);
const issues = issue_rows.reduce((sum, row) => sum + row.total_issues, 0);
const stale = issue_rows.reduce((sum, row) => sum + row.stale_open, 0);

display(html`<div class="summary">
  ${area("people", "People", [
    ["bus_factor_map", "Bus factor", lowest ?? "Not established",
      lowest === null
        ? `in all ${bus.length} repositories`
        : `in ${at_lowest} of ${bus.length} repositories${unestablished ? `; not established in ${unestablished}` : ""}`],
    ownership.length && ["knowledge_concentration", "Largest owner", pct(ownership[0].owned_loc / owned_total), `${nameOf(ownership[0].person)}, share of surviving lines`],
    ["contributor_activity_timeline", "Employees", count(employees), others.length ? `plus ${others.join(", ")}` : "no other contributors"],
    ["hero_dependency_register", "Single-owner files", pct(single.single_owner / single.files), `${count(single.single_owner)} of ${count(single.files)} files`],
  ])}
  ${area("product", "Product", [
    ["code_aging_chart", "Source lines", count(source_lines), `surviving today in ${source_repos} repositories`],
    ["abandoned_area_register", "Abandoned repositories", count(abandoned.length), `of ${repo_rows.length}`],
    hot.length && ["hotspot_map", "Most changes to one file", count(hot[0].revisions), wrap(hot[0].path)],
    ["hidden_coupling_matrix", "Hidden couplings", count(pairs.length), "file pairs that change together"],
  ])}
  ${area("process", "Process", [
    ["ci_health", "CI runs passing", passing === null ? "No runs" : pct(passing), `of ${count(runs)} completed runs`],
    ["dora_quadrant", "PR open to merge", cycle === null ? "No merged PRs" : hours(cycle), `average over ${count(merged)} merged PRs`],
    uses_releases && ["dora_quadrant", "GitHub releases", count(releases), "in the last 30 days"],
    ["issue_triage_health", "Issues open over 90 days", count(stale), issues ? `of ${count(issues)} GitHub issues` : "no GitHub issues recorded"],
  ])}
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
