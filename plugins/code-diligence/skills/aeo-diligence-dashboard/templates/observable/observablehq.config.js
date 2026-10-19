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
  theme: ["air", "near-midnight"],
  head: `<style>
:root { --serif: var(--sans-serif); }
#observablehq-main h1 { font-size: 2rem; margin-bottom: 0.25rem; }
#observablehq-main h2 { font-size: 1.35rem; margin-top: 2.25rem; }
.subtitle { color: var(--theme-foreground-muted); margin: 0 0 1.5rem; }
.finding { font-size: 1.05rem; line-height: 1.55; max-width: 72ch; margin: 0.5rem 0 1rem; }
.caption { color: var(--theme-foreground-muted); font-size: 0.85rem; max-width: 72ch; margin: 0.5rem 0 0; }
.wrap { white-space: normal; overflow-wrap: anywhere; }
.headlines { display: grid; grid-template-columns: minmax(9rem, 14rem) minmax(0, 72ch); gap: 0 1.5rem; margin: 0; }
.headlines dt, .headlines dd { padding: 0.65rem 0; border-top: 1px solid var(--theme-foreground-faintest); }
.headlines dt { font-weight: 600; }
.headlines dd { margin: 0; line-height: 1.5; }
@media (max-width: 640px) {
  .headlines { grid-template-columns: minmax(0, 1fr); }
  .headlines dt { padding-bottom: 0.15rem; }
  .headlines dd { border-top: none; padding-top: 0; }
}
</style>`,
  footer: "code-diligence · Evidence from repository history and available analysis tools."
};
