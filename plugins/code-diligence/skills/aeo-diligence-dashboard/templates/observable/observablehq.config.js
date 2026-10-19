import {readFileSync} from "node:fs";

const {targets} = JSON.parse(readFileSync(new URL("./src/data/config.json", import.meta.url), "utf8"));
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
        {name: "Overview", path: `/targets/${target}`},
        ...sections.map(section => ({name: section[0].toUpperCase() + section.slice(1), path: `/targets/${target}/${section}`}))
      ]
    })),
    {name: "Compare targets", path: "/compare"},
    {name: "Methodology", path: "/about"}
  ],
  dynamicPaths: targets.flatMap(target => [
    `/targets/${target}`,
    ...sections.map(section => `/targets/${target}/${section}`)
  ]),
  theme: "air",
  head: `<style>
:root { --serif: var(--sans-serif); }
#observablehq-main h1 { font-size: 2rem; margin-bottom: 0.25rem; }
#observablehq-main h2 { font-size: 1.35rem; margin-top: 2.25rem; }
.subtitle { color: var(--theme-foreground-muted); margin: 0 0 1.5rem; }
.finding { font-size: 1.05rem; line-height: 1.55; max-width: 72ch; margin: 0.5rem 0 1rem; }
.caption { color: var(--theme-foreground-muted); font-size: 0.85rem; max-width: 72ch; margin: 0.5rem 0 0; }
.wrap { white-space: normal; overflow-wrap: anywhere; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1.5rem 2rem; max-width: 1040px; }
.summary-area h3 { font-size: 1.05rem; margin: 0; }
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
</style>
<script type="module">
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
