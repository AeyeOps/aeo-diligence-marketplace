import {readFileSync} from "node:fs";

const {targets} = JSON.parse(readFileSync(new URL("./src/data/config.json", import.meta.url), "utf8"));
const overviewStyles = readFileSync(new URL("./overview.css", import.meta.url), "utf8");
const sections = ["people", "product", "process", "repos", "curation", "health"];

export default {
  root: "src",
  preserveIndex: true,
  preserveExtension: true,
  title: "code-diligence",
  pages: [
    {name: "Portfolio", path: "/"},
    ...targets.map(target => ({
      name: target,
      pages: [
        {name: "Dashboard", path: `/targets/${target}`},
        ...sections.map(section => ({name: section[0].toUpperCase() + section.slice(1), path: `/targets/${target}/${section}`}))
      ]
    })),
    {name: "Compare targets", path: "/compare"},
    {name: "Methodology", path: "/about"}
  ],
  header: ({path}) => {
    const target = targets.find(target => path === `/targets/${target}` || path.startsWith(`/targets/${target}/`));
    const dashboard = target ? `/targets/${target}.html` : "/index.html";
    const section = path.split("/")[3];
    return `<nav class="report-actions" aria-label="Report actions"><a href="${dashboard}">← Dashboard</a>${target ? `<a data-report-pdf="${target}/report">Download full PDF</a>${sections.includes(section) ? `<a data-report-pdf="${target}/${section}">Download section PDF</a>` : ""}` : ""}</nav>`;
  },
  dynamicPaths: targets.flatMap(target => [
    `/targets/${target}`,
    ...sections.map(section => `/targets/${target}/${section}`)
  ]),
  theme: "air",
  head: `<style>
html[data-report-print] #observablehq-sidebar, html[data-report-print] #observablehq-toc, html[data-report-print] #observablehq-header, html[data-report-print] #sidebar-resize { display: none !important; }
html[data-report-print] #observablehq-center { margin: 0 !important; padding: 0 !important; }
html[data-report-print] #observablehq-main { width: 720px !important; max-width: 720px !important; margin: 0 !important; padding: 0 !important; }
.report-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--theme-foreground-faintest); }
.report-actions a { font-size: 0.85rem; text-decoration: none; }
.report-actions a:first-child { margin-right: auto; font-weight: 600; }
.sidebar-report-download { display: block; padding: 0.5rem 0; font-size: 0.875rem; }
:root { --serif: var(--sans-serif); }
#observablehq-main h1 { font-size: 2rem; margin-bottom: 0.25rem; }
#observablehq-main h2 { font-size: 1.35rem; margin-top: 2.25rem; }
.subtitle { color: var(--theme-foreground-muted); margin: 0 0 1.5rem; }
.finding { font-size: 1.05rem; line-height: 1.55; max-width: 72ch; margin: 0.5rem 0 1rem; }
.caption { color: var(--theme-foreground-muted); font-size: 0.85rem; max-width: 72ch; margin: 0.5rem 0 0; }
.wrap { white-space: normal; overflow-wrap: anywhere; }
.code-health-tables { display: grid; grid-template-columns: minmax(0, 1fr); gap: 1.75rem; margin: 1.25rem 0 1rem; }
.code-health-tables h3 { font-size: 1.05rem; margin: 0 0 0.65rem; }
.code-health-tables form { margin: 0; font-size: 0.875rem; line-height: 1.4; }
.code-health-tables table { width: 100%; min-width: 40rem; }
.code-health-tables tr > :first-child { display: none; }
.code-health-tables th, .code-health-tables td { padding: 0.45rem 0.5rem; vertical-align: top; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1.5rem 2rem; max-width: 1040px; }
.summary-area h3 { font-size: 1.05rem; margin: 0; }
.summary-wide { grid-column: 1 / -1; }
.summary-confidence { color: var(--theme-foreground-muted); font-size: 0.85rem; margin: 0.15rem 0 0.5rem; }
.summary-area dl { margin: 0; }
.summary-row { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; padding: 0.55rem 0; border-top: 1px solid var(--theme-foreground-faintest); }
.summary-row dt { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.summary-row dt a { color: var(--theme-foreground); }
.summary-row dt a:hover, .summary-row dt a:focus-visible { color: var(--theme-foreground-focus); }
.summary-row dt span { color: var(--theme-foreground-muted); font-size: 0.8rem; overflow-wrap: anywhere; }
.summary-source { color: var(--theme-foreground); font-weight: 600; }
.summary-row dd { margin: 0; font-size: 1.25rem; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
.headlines { display: grid; grid-template-columns: minmax(9rem, 14rem) minmax(0, 72ch); gap: 0 1.5rem; margin: 1.25rem 0 0; }
.headlines dt, .headlines dd { padding: 0.65rem 0; border-top: 1px solid var(--theme-foreground-faintest); }
.headlines dt { font-weight: 600; }
.headlines dd { margin: 0; line-height: 1.5; }
.source { font-weight: 600; }
.security-chart { max-width: 1040px; margin: 1rem 0; }
.security-chart-scroll { overflow-x: auto; }
.security-tip-source { color: #627180; font-size: 0.8rem; }
.security-tip-source { max-width: 28rem; white-space: normal; }
.security-tip-table { border-collapse: collapse; font-size: 0.85rem; margin: 0.5rem 0; }
.security-tip-table th, .security-tip-table td { padding: 0.15rem 0.5rem; text-align: right; }
.security-tip-table th:first-child, .security-tip-table td:first-child { text-align: left; padding-left: 0; }
#observablehq-main table th { white-space: normal; vertical-align: bottom; }
@media (max-width: 640px) {
  .headlines { grid-template-columns: minmax(0, 1fr); }
  .headlines dt { padding-bottom: 0.15rem; }
  .headlines dd { border-top: none; padding-top: 0; }
}
#observablehq-sidebar { width: calc(var(--sidebar-width, 272px) + var(--observablehq-sidebar-padding-left)); left: calc(-1 * var(--sidebar-width, 272px)); }
#sidebar-resize { display: none; position: fixed; top: 0; bottom: 0; width: 7px; margin-left: -3px; cursor: col-resize; z-index: 4; touch-action: none; }
#sidebar-resize:hover, #sidebar-resize:focus-visible, #sidebar-resize[data-dragging] { background: var(--theme-foreground-faint); outline: none; }
@media (min-width: calc(912px + 6rem)) {
  #observablehq-sidebar-toggle:checked ~ #observablehq-center, #observablehq-sidebar-toggle:indeterminate ~ #observablehq-center { --observablehq-inset-left: calc(var(--sidebar-width, 272px) + 1rem); }
  #observablehq-sidebar-toggle:checked ~ #sidebar-resize, #observablehq-sidebar-toggle:indeterminate ~ #sidebar-resize { display: block; }
}
</style><style>${overviewStyles}</style>
<script>if (new URLSearchParams(location.search).has("print")) document.documentElement.dataset.reportPrint = "";</script>
<script type="module">
for (const link of document.querySelectorAll("[data-report-pdf]")) {
  const dashboard = document.querySelector(".report-actions a");
  const outputRoot = new URL("../", dashboard.href);
  link.href = new URL("reports/" + link.dataset.reportPdf + ".pdf", outputRoot).href;
  link.download = link.dataset.reportPdf.replace("/", "-") + ".pdf";
}
const fullReport = document.querySelector('[data-report-pdf$="/report"]');
if (fullReport) {
  const link = fullReport.cloneNode(true);
  link.className = "sidebar-report-download";
  document.querySelector("#observablehq-sidebar").append(link);
}
const root = document.documentElement;
const sidebar = document.getElementById("observablehq-sidebar");
const toggle = document.getElementById("observablehq-sidebar-toggle");
const handle = Object.assign(document.createElement("div"), {id: "sidebar-resize", tabIndex: 0, title: "Drag to resize, double-click to reset"});
handle.setAttribute("role", "separator");
handle.setAttribute("aria-orientation", "vertical");
handle.setAttribute("aria-label", "Resize sidebar");
sidebar.after(handle);
const current = () => parseFloat(getComputedStyle(root).getPropertyValue("--sidebar-width")) || 272;
const place = () => { handle.style.left = sidebar.getBoundingClientRect().right + "px"; };
const apply = width => {
  const clamped = Math.round(Math.min(Math.max(width, 160), innerWidth / 2));
  root.style.setProperty("--sidebar-width", clamped + "px");
  handle.setAttribute("aria-valuenow", clamped);
  try { localStorage.setItem("sidebar-width", clamped); } catch {}
  place();
};
try { const saved = Number(localStorage.getItem("sidebar-width")); if (saved) root.style.setProperty("--sidebar-width", saved + "px"); } catch {}
handle.addEventListener("pointerdown", event => {
  const offset = sidebar.getBoundingClientRect().right - current();
  handle.setPointerCapture(event.pointerId);
  handle.dataset.dragging = "";
  const move = moved => apply(moved.clientX - offset);
  handle.addEventListener("pointermove", move);
  handle.addEventListener("pointerup", () => { handle.removeEventListener("pointermove", move); delete handle.dataset.dragging; }, {once: true});
});
handle.addEventListener("dblclick", () => { root.style.removeProperty("--sidebar-width"); try { localStorage.removeItem("sidebar-width"); } catch {} place(); });
handle.addEventListener("keydown", event => {
  const step = {ArrowLeft: -16, ArrowRight: 16}[event.key];
  if (step) { event.preventDefault(); apply(current() + step); }
});
addEventListener("resize", place);
toggle.addEventListener("change", () => requestAnimationFrame(place));
place();
</script>`,
  footer: "code-diligence · Evidence from repository history and available analysis tools."
};
