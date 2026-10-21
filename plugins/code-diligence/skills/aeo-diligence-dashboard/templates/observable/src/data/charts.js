import * as echarts from "npm:echarts@6.1.0";
import {count, severityLabel} from "./labels.js";

const COLORS = {CRITICAL: "#9d4264", HIGH: "#c47b27", MEDIUM: "#3776a1", LOW: "#659284", INFORMATIONAL: "#a3b3c4", UNTRIAGED: "#777d87"};
const ORDER = Object.keys(COLORS);
const escape = value => String(value).replace(/[&<>"']/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[char]);
const valuePresent = value => typeof value === "number";
const periodKey = (start, end) => `${+new Date(start)}/${+new Date(end)}`;
const key = period => periodKey(period.start, period.end);

export function securityChart(data, {width, height, invalidation}) {
  const printing = new URLSearchParams(location.search).has("print");
  const root = document.createElement("div");
  root.className = "security-chart";
  if (!data.periods.length) {
    root.textContent = "No security data for this range.";
    return root;
  }
  const date = value => value ? new Intl.DateTimeFormat(undefined, {
    timeZone: data.timezone, year: "numeric", month: "short", day: "numeric",
  }).format(new Date(value)) : "";
  const severities = [...data.severities].sort((a, b) => {
    const first = ORDER.indexOf(a), second = ORDER.indexOf(b);
    return (first < 0 ? ORDER.length : first) - (second < 0 ? ORDER.length : second) || a.localeCompare(b);
  });
  const rowGroups = new Map();
  for (const row of data.rows) {
    const rowKey = periodKey(row.period_start, row.period_end);
    if (!rowGroups.has(rowKey)) rowGroups.set(rowKey, []);
    rowGroups.get(rowKey).push(row);
  }
  const rows = data.periods.map(period => rowGroups.get(key(period)) ?? []);
  const calculated = new Map(data.calculated_backlog.filter(point => valuePresent(point.value))
    .map(point => [periodKey(point.period_start, point.period_end), point]));
  const differences = new Map(data.calculated_backlog.filter(point => valuePresent(point.balance_difference))
    .map(point => [periodKey(point.period_start, point.period_end), point.balance_difference]));
  const labels = data.counting_basis === "events" ? {added: "Opened", removed: "Closed"} : {added: "Added", removed: "Removed"};
  const basis = {events: "Recorded events", snapshots: "Changes between snapshots", provider_aggregate: "Provider totals", distinct_findings: "Distinct findings", mixed: "Mixed counting methods"}[data.counting_basis];
  const stock = (index, measure) => {
    const group = rows[index], total = group.find(row => row.severity == null && valuePresent(row[measure]));
    const parts = group.filter(row => severities.includes(row.severity) && valuePresent(row[measure]));
    const observationTime = row => row.coverage[measure]?.end ?? (measure === "opening_backlog" ? row.period_start : row.period_end);
    if (total) return {value: total[measure], rows: [total], at: observationTime(total)};
    if (!severities.length || parts.length !== severities.length) return null;
    const times = parts.map(observationTime);
    if (new Set(times.map(time => +new Date(time))).size !== 1) return null;
    return {value: parts.reduce((sum, row) => sum + row[measure], 0), rows: parts, at: times[0]};
  };
  const backlog = data.periods.map((period, index) => {
    const observed = stock(index, "closing_backlog");
    if (observed) return {...observed, calculated: false};
    if (calculated.has(key(period))) return calculated.get(key(period));
    const opening = stock(index, "opening_backlog");
    return opening ? {...opening, calculated: false, description: "Opening backlog"} : null;
  });
  const pointIndex = at => {
    const instant = +new Date(at);
    return data.periods.findIndex((period, index) =>
      (instant > +new Date(period.start) || index === 0 && instant === +new Date(period.start)) &&
      instant <= +new Date(period.end));
  };
  if (data.backlog_anchor) {
    const index = pointIndex(data.backlog_anchor.at);
    if (index >= 0 && !backlog[index]) backlog[index] = {...data.backlog_anchor, calculated: false};
  }
  for (const point of [...data.backlog_estimates].sort((a, b) => +new Date(a.at) - +new Date(b.at))) {
    const index = pointIndex(point.at);
    if (index >= 0 && (!backlog[index] || backlog[index].estimated)) {
      backlog[index] = {...point, calculated: true, estimated: true};
    }
  }
  const movement = Object.fromEntries(["added", "removed"].map(measure => [measure, rows.map(group => {
    const parts = group.filter(row => severities.includes(row.severity) && valuePresent(row[measure]));
    const total = group.find(row => row.severity == null && valuePresent(row[measure]));
    const sum = parts.reduce((value, row) => value + row[measure], 0);
    const useTotal = total && (!parts.length || parts.length !== severities.length || sum !== total[measure]);
    return {
      values: useTotal ? new Map([["Total", total[measure]]]) : new Map(parts.map(row => [severityLabel(row.severity), row[measure]])),
      partial: !useTotal && parts.length < severities.length,
      rows: useTotal ? [total] : parts,
    };
  })]));
  const names = severities.map(severityLabel);
  if (Object.values(movement).some(periods => periods.some(period => period.values.has("Total")))) names.push("Total");
  let selected = Object.fromEntries([...names, "Backlog", "Starting point"].map(name => [name, true]));
  const barTotal = (measure, index) => {
    const values = [...movement[measure][index].values].filter(([name]) => selected[name]);
    return values.length ? values.reduce((sum, [, value]) => sum + value, 0) : null;
  };
  const scroll = document.createElement("div");
  scroll.className = "security-chart-scroll";
  const plot = document.createElement("div");
  plot.setAttribute("role", "img");
  plot.setAttribute("aria-label", `${labels.added}, ${labels.removed.toLowerCase()}, and backlog of security findings`);
  scroll.append(plot);
  root.append(scroll);
  const chartWidth = Math.max(680, Math.floor(width));
  const chartHeight = Math.max(420, height);
  plot.style.width = `${chartWidth}px`;
  plot.style.height = `${chartHeight}px`;
  const chart = echarts.init(plot, null, {renderer: "svg", width: chartWidth, height: chartHeight});
  invalidation.then(() => chart.dispose());
  const coverageText = (row, measure) => {
    const coverage = row.coverage[measure];
    if (!coverage) return "Coverage unknown";
    const start = date(coverage.start), end = date(coverage.end);
    const span = start && end ? start === end ? start : `${start} to ${end}` : start || end;
    const status = coverage.status === "unknown" ? "Coverage unknown" : coverage.status === "partial" && !measure.endsWith("_backlog") ? "Partial period" : "";
    return [status, span].filter(Boolean).join(" · ");
  };
  const barMaxWidth = 70;
  const series = names.toReversed().flatMap(name => ["added", "removed"].map(measure => ({
    id: `${measure}-${name}`, name, type: "bar", stack: "movement", stackStrategy: "samesign", barMaxWidth,
    itemStyle: {color: name === "Total" ? "#617b93" : COLORS[severities[names.indexOf(name)]] ?? "#777d87", opacity: .88},
    data: movement[measure].map(period => period.values.has(name) ? period.values.get(name) * (measure === "added" ? 1 : -1) : null),
    emphasis: {focus: "series"},
  })));
  const hasBacklog = backlog.some(point => point);
  if (hasBacklog) series.push({
    id: "backlog-line", name: "Backlog", type: "line", z: 2, connectNulls: false, symbol: "none",
    lineStyle: {color: "#152d47", width: 2.5, type: "dashed"},
    data: backlog.map(point => point?.value ?? null),
  }, {
    id: "backlog", name: "Backlog", type: "scatter", z: 5, symbol: "circle", symbolSize: 8,
    itemStyle: {color: "white", borderColor: "#152d47", borderWidth: 2},
    label: {show: true, position: printing ? "top" : "right", distance: printing ? 28 : barMaxWidth / 2 + 8, formatter: params => count(params.value), color: "#152d47", fontWeight: 700, backgroundColor: "white", padding: [2, 3]},
    data: backlog.map(point => point ? {value: point.value, itemStyle: {color: point.calculated === false ? "#152d47" : "white"}} : null),
  });
  const baselineIndex = data.baseline ? pointIndex(data.baseline.at) : -1;
  if (baselineIndex >= 0) series.push({
    id: "baseline", name: "Starting point", type: "scatter", z: 6, symbol: "diamond", symbolSize: 12,
    itemStyle: {color: "white", borderColor: "#28604e", borderWidth: 2},
    label: {show: true, position: printing ? "left" : "right", distance: printing ? 12 : barMaxWidth / 2 + 8, offset: [0, -16], formatter: () => count(data.baseline.value), color: "#28604e", fontWeight: 700},
    data: data.periods.map((_, index) => index === baselineIndex ? data.baseline.value : null),
  });
  const totalSeries = () => ["added", "removed"].map(measure => ({
    id: `${measure}-total`, name: `${measure}-total`, type: "scatter", symbolSize: 0, silent: true, tooltip: {show: false}, z: 7,
    label: {
      show: true, position: measure === "added" ? "top" : "bottom", distance: 8,
      fontWeight: 700, color: "#536270",
      formatter: params => `${measure === "added" ? "+" : "−"}${count(Math.abs(params.value))}${movement[measure][params.dataIndex].partial ? "*" : ""}`,
    },
    data: data.periods.map((_, index) => {
      const value = barTotal(measure, index);
      return value === null ? null : value * (measure === "added" ? 1 : -1);
    }),
  }));
  series.push(...totalSeries(), {
    id: "missing", type: "scatter", symbolSize: 0, silent: true, tooltip: {show: false},
    label: {show: true, position: "bottom", color: "#627180", formatter: () => "No data"},
    data: data.periods.map((_, index) =>
      !movement.added[index].values.size && !movement.removed[index].values.size && !backlog[index] && index !== baselineIndex ? 0 : null),
  });
  const maximum = Math.max(1, ...data.periods.flatMap((_, index) =>
    [barTotal("added", index) ?? 0, barTotal("removed", index) ?? 0, Math.abs(backlog[index]?.value ?? 0)]), Math.abs(data.baseline?.value ?? 0));
  const magnitude = 10 ** Math.floor(Math.log10(maximum));
  const limit = Math.ceil(maximum / magnitude) * magnitude;
  const legend = [...names];
  if (hasBacklog) legend.push("Backlog");
  if (baselineIndex >= 0) legend.push("Starting point");
  const hasAdded = movement.added.some(period => period.values.size);
  const hasRemoved = movement.removed.some(period => period.values.size);
  const legendHeight = legend.length > 6 && chartWidth < 850 ? 56 : 32;
  const periodDetails = index => {
        const period = data.periods[index];
        const group = rows[index].filter(row => selected[row.severity == null ? "Total" : severityLabel(row.severity)] !== false)
          .sort((a, b) => (a.severity == null ? severities.length : severities.indexOf(a.severity)) - (b.severity == null ? severities.length : severities.indexOf(b.severity)));
        const content = [`<strong>${escape(period.label)}</strong>`, `<div class="security-tip-source">${escape(data.source ?? "")} · ${escape(basis ?? "")}</div>`];
        if (data.scope) content.push(`<div class="security-tip-source">${escape(data.scope)}</div>`);
        const showAdjustment = group.some(row => valuePresent(row.adjustment) && row.adjustment !== 0);
        const measures = ["added", "removed", ...(showAdjustment ? ["adjustment"] : []), "closing_backlog"];
        content.push(`<table class="security-tip-table"><tr><th>Severity</th><th>${labels.added}</th><th>${labels.removed}</th>${showAdjustment ? "<th>Adjustment</th>" : ""}<th>Backlog</th></tr>`);
        for (const row of group) {
          const name = row.severity == null ? "Total" : severityLabel(row.severity);
          content.push(`<tr><td>${escape(name)}</td>${measures.map(measure =>
            `<td title="${escape(coverageText(row, measure))}">${valuePresent(row[measure]) ? count(row[measure]) : "No data"}</td>`).join("")}</tr>`);
        }
        content.push("</table>");
        const coverage = new Map();
        for (const measure of measures) {
          const bySpan = new Map();
          for (const row of group.filter(row => valuePresent(row[measure]))) {
            const span = coverageText(row, measure);
            if (!bySpan.has(span)) bySpan.set(span, []);
            bySpan.get(span).push(row.severity == null ? "Total" : severityLabel(row.severity));
          }
          for (const [span, parts] of bySpan) {
            const subset = parts.length === group.length ? "" : parts.join(", ");
            const key = `${subset}\n${span}`;
            if (!coverage.has(key)) coverage.set(key, {span, subset, measures: []});
            coverage.get(key).measures.push(measure === "closing_backlog" ? "Backlog" : measure === "adjustment" ? "Adjustment" : labels[measure]);
          }
        }
        for (const {span, subset, measures} of coverage.values()) {
          const label = `${measures.join(" / ")}${subset ? ` (${subset})` : ""}`;
          content.push(`<div class="security-tip-source">${escape(label)}: ${escape(span)}</div>`);
        }
        if (calculated.has(key(period)) && selected.Backlog) {
          const point = calculated.get(key(period));
          content.push(`<div>Backlog: <b>${count(point.value)}</b> · ${escape(point.description)}</div>`);
        }
        if (backlog[index]?.estimated && selected.Backlog) {
          content.push(`<div class="security-tip-source">Backlog: <b>${count(backlog[index].value)}</b> · ${escape(backlog[index].description)}</div>`);
        }
        if (backlog[index]?.description === "Opening backlog" && selected.Backlog) {
          content.push(`<div>Opening backlog: <b>${count(backlog[index].value)}</b> · ${escape(date(backlog[index].at))}</div>`);
        }
        if (baselineIndex === index && selected["Starting point"]) {
          content.push(`<div>Starting point: <b>${count(data.baseline.value)}</b> · ${escape(date(data.baseline.at))} · ${escape(data.baseline.description)}</div>`);
        }
        if (data.backlog_anchor && pointIndex(data.backlog_anchor.at) === index && selected.Backlog) {
          content.push(`<div>Known backlog: <b>${count(data.backlog_anchor.value)}</b> · ${escape(date(data.backlog_anchor.at))} · ${escape(data.backlog_anchor.description)}</div>`);
        }
        if (differences.has(key(period))) content.push(`<div>Balance difference: ${count(differences.get(key(period)))}</div>`);
        if (movement.added[index].partial || movement.removed[index].partial) content.push("<div class=\"security-tip-source\">* Some severity counts are unavailable.</div>");
        if (!rows[index].length && !backlog[index] && baselineIndex !== index) content.push("<div>No counts are available for this period.</div>");
        return content.join("");
  };
  chart.setOption({
    animation: false,
    textStyle: {fontFamily: "Arial,sans-serif", color: "#24394b"},
    grid: {left: 65, right: 35, top: legendHeight + 42, bottom: 76},
    legend: {data: legend, selected, top: 0, left: 0, itemWidth: 12, itemHeight: 12, itemGap: 18, textStyle: {fontSize: 12}},
    xAxis: {
      type: "category", data: data.periods.map(period => period.label), axisTick: {show: false}, axisLine: {show: false},
      axisLabel: {color: "#24394b", fontWeight: 600, margin: 22, hideOverlap: true},
    },
    yAxis: {
      type: "value", min: hasRemoved || backlog.some(point => point?.value < 0) ? -limit : 0, max: limit, interval: limit / 2,
      axisLine: {show: false}, axisTick: {show: false}, splitLine: {lineStyle: {color: "#e0e5ea"}},
      axisLabel: {color: "#627180", formatter: value => Math.abs(value) >= 1000 ? `${value / 1000}k` : String(value)},
    },
    graphic: [
      ...(hasAdded ? [{type: "text", left: 65, top: legendHeight + 14, style: {text: labels.added, fill: "#627180", font: "12px Arial"}}] : []),
      ...(hasRemoved ? [{type: "text", left: 65, bottom: 24, style: {text: labels.removed, fill: "#627180", font: "12px Arial"}}] : []),
    ],
    tooltip: {
      trigger: "axis", confine: true, backgroundColor: "rgba(255,255,255,.98)", borderColor: "#cbd3dc",
      textStyle: {color: "#24394b", fontFamily: "Arial,sans-serif"}, axisPointer: {type: "line"},
      formatter: params => params.length ? periodDetails(params[0].dataIndex) : "",
    },
    series,
  });
  chart.on("legendselectchanged", event => {
    selected = event.selected;
    chart.setOption({series: totalSeries()});
  });
  if (printing) {
    const notes = document.createElement("div");
    notes.className = "security-print-notes";
    notes.innerHTML = `<h3>Security evidence by period</h3>${data.periods.map((_, index) => `<section>${periodDetails(index)}</section>`).join("")}`;
    root.append(notes);
  }
  return root;
}
