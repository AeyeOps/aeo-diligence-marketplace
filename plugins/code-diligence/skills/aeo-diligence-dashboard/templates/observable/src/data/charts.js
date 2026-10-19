import * as Plot from "npm:@observablehq/plot";
import {SEVERITY_COLORS, count, monthLabel, severityLabel} from "./labels.js";

const CHARTED = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const MONTHS = 6;

export function securityChart(rows, {width, height}) {
  const latest = new Date(Math.max(...rows.map(row => +row.month)));
  const domain = Array.from({length: MONTHS}, (_, i) =>
    monthLabel(Date.UTC(latest.getUTCFullYear(), latest.getUTCMonth() - MONTHS + 1 + i, 1)));
  const covered = new Set(rows.map(row => monthLabel(row.month)));
  const bars = rows
    .filter(row => CHARTED.includes(row.severity) && domain.includes(monthLabel(row.month)))
    .map(row => ({month: monthLabel(row.month), severity: severityLabel(row.severity), findings: row.opening + row.opened}))
    .filter(bar => bar.findings > 0);
  const severities = CHARTED.map(severityLabel);
  return Plot.plot({
    marks: [
      Plot.barY(bars, {x: "month", y: "findings", fill: "severity", order: severities, tip: true}),
      Plot.text(bars, Plot.groupX({y: "sum", text: "sum"}, {x: "month", y: "findings", text: "findings", dy: -8, fill: "currentColor"})),
      Plot.text(domain.filter(month => !covered.has(month)), {x: month => month, frameAnchor: "bottom", dy: -6, text: () => "No data", fill: "var(--theme-foreground-muted)"}),
      Plot.ruleY([0]),
    ],
    color: {domain: severities, range: SEVERITY_COLORS.slice(0, CHARTED.length), legend: true},
    x: {domain, label: null, tickFormat: month => month.replace(" ", "\n")},
    y: {label: "Fixable findings in the month", grid: true, tickFormat: count},
    width,
    height,
  });
}
