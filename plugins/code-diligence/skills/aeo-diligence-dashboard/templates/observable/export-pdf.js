import {createReadStream} from "node:fs";
import {mkdir, readFile, stat} from "node:fs/promises";
import {createServer} from "node:http";
import {extname, resolve, sep} from "node:path";
import {pipeline} from "node:stream/promises";
import {chromium} from "playwright";

const root = resolve("dist");
const {targets} = JSON.parse(await readFile("src/data/config.json", "utf8"));
const stylesheet = await readFile("report.css", "utf8");
const overviewStyles = await readFile("overview.css", "utf8");
const sections = [
  ["overview", "Dashboard"], ["people", "People"], ["product", "Product"],
  ["process", "Process"], ["repos", "Repositories"], ["curation", "Curation"],
  ["health", "Evidence health"], ["about", "Methodology"],
];
const assessmentTools = [
  ["Git", "Development activity, contributor history and patterns of code change."],
  ["git-fame", "Code ownership concentration used to assess key-person dependency."],
  ["git-truck", "Concentration of file changes by contributor, alongside code ownership."],
  ["code-maat", "Change hotspots and files that may need coordinated maintenance."],
  ["git-of-theseus", "The age profile of the current codebase."],
  ["Hercules", "Code retention and replacement trends across the development history."],
  ["Repowise", "Code health findings that point to potential maintenance costs."],
  ["GitHub", "Review speed, CI reliability, release activity and issue handling."],
  ["AWS Inspector", "Security findings and changes within the selected assessment scope."],
  ["Observable Framework", "An interactive view of the evidence behind the assessment."],
];
const types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".wasm": "application/wasm"};
const escape = value => String(value).replace(/[&<>"']/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[char]);
const route = (target, section) => section === "about" ? "/about.html"
  : section === "overview" ? `/targets/${target}.html` : `/targets/${target}/${section}.html`;

const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
  const file = resolve(root, `.${pathname}`);
  if (!file.startsWith(root + sep)) {
    response.writeHead(403).end();
    return;
  }
  try {
    const info = await stat(file);
    if (!info.isFile()) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, {"Content-Type": types[extname(file)] ?? "application/octet-stream"});
    await pipeline(createReadStream(file), response);
  } catch (error) {
    if (error.code === "ENOENT") response.writeHead(404).end();
    else response.destroy(error);
  }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
try {
  browser = await chromium.launch({executablePath: process.env.DILIGENCE_CHROMIUM_PATH});
  const page = await browser.newPage({viewport: {width: 800, height: 1000}, colorScheme: "light"});
  const pdf = await browser.newPage({viewport: {width: 800, height: 1000}, colorScheme: "light"});
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error));
  for (const target of targets) {
    const captured = [];
    for (const [id, label] of sections) {
      pageErrors.length = 0;
      const path = route(target, id);
      await page.setViewportSize({width: id === "overview" ? 1440 : 800, height: 1000});
      await page.goto(`${origin}${path}${id === "overview" ? "" : "?print"}`, {waitUntil: "networkidle"});
      if (id === "overview") {
        await page.addStyleTag({content: "#observablehq-main { width: 1040px !important; max-width: 1040px !important; padding: 0 !important; box-sizing: content-box; }"});
        await page.waitForFunction(() => {
          const chart = document.querySelector(".board-security svg");
          return Boolean(document.querySelector(".board-security .dashboard-empty"))
            || chart?.getAttribute("width") === "1040";
        });
      }
      await page.waitForFunction(() => !document.querySelector("observablehq-loading"));
      await page.evaluate(() => document.fonts.ready);
      if (pageErrors.length) throw pageErrors[0];
      const errors = await page.locator(".observablehq--error").allTextContents();
      if (errors.length) throw new Error(`${path}: ${errors.join("\n")}`);
      const content = await page.evaluate(({id, label, path}) => {
        const source = document.querySelector("#observablehq-main");
        const title = source.querySelector("h1").textContent.trim();
        const description = id === "overview" ? source.querySelector(".target-description").textContent.trim() : null;
        const refreshDate = id === "overview" ? source.querySelector(".target-refresh-date").textContent.trim() : null;
        const copy = source.cloneNode(true);
        if (id === "overview") copy.querySelector(".dashboard-metadata").remove();
        const originals = [...source.querySelectorAll("form")];
        for (const [index, form] of [...copy.querySelectorAll("form")].entries()) {
          const table = form.querySelector("table");
          if (!table) {
            form.remove();
            continue;
          }
          const cells = [...originals[index].querySelectorAll("thead th")].slice(1);
          const total = cells.reduce((sum, cell) => sum + cell.getBoundingClientRect().width, 0);
          const columns = document.createElement("colgroup");
          for (const cell of cells) {
            const col = document.createElement("col");
            col.style.width = `${100 * cell.getBoundingClientRect().width / total}%`;
            columns.append(col);
          }
          for (const row of table.rows) row.cells[0]?.remove();
          table.prepend(columns);
          const body = table.tBodies[0];
          if (body.rows.length > 3) {
            const tail = document.createElement("tbody");
            tail.className = "table-tail";
            tail.append(...[...body.rows].slice(-3));
            table.insertBefore(tail, body.nextSibling);
          }
          table.className = "report-table";
          table.removeAttribute("style");
          form.replaceWith(table);
        }
        for (const caption of copy.querySelectorAll("p.caption")) {
          const preceding = caption.previousElementSibling;
          const tables = preceding?.querySelectorAll("table");
          if (tables?.length === 1 && !preceding.querySelector("svg")) {
            const table = tables[0];
            const cell = table.createTFoot().insertRow().insertCell();
            cell.colSpan = table.tHead.rows[0].cells.length;
            cell.append(caption);
          }
        }
        copy.querySelectorAll("script, input, button, observablehq-loading").forEach(node => node.remove());
        if (id !== "overview") copy.querySelector("h1").textContent = label;
        for (const chart of copy.querySelectorAll(".security-chart svg")) {
          chart.setAttribute("viewBox", `0 0 ${chart.getAttribute("width")} ${chart.getAttribute("height")}`);
        }
        for (const node of copy.querySelectorAll("[id]")) node.id = `${id}-${node.id}`;
        for (const node of copy.querySelectorAll("*")) {
          for (const attr of [...node.attributes]) {
            if (attr.value.includes("url(#")) node.setAttribute(attr.name, attr.value.replace(/url\(#([^)]*)\)/g, `url(#${id}-$1)`));
          }
        }
        for (const style of copy.querySelectorAll("style")) {
          style.textContent = style.textContent.replace(/url\(#([^)]*)\)/g, `url(#${id}-$1)`);
        }
        for (const link of copy.querySelectorAll("a[href]")) {
          const url = new URL(link.getAttribute("href"), location.href);
          if (url.origin === location.origin) {
            link.dataset.reportPath = url.pathname;
            link.dataset.reportAnchor = url.hash.slice(1);
          }
        }
        return {id, label, path, title, description, refreshDate, html: copy.innerHTML};
      }, {id, label, path});
      captured.push(content);
      console.log(`PDF source: ${target} / ${label}`);
    }
    const title = captured[0].title;
    const {description, refreshDate} = captured[0];
    const directory = resolve(root, "reports", target);
    await mkdir(directory, {recursive: true});
    for (const area of ["report", ...sections.map(([id]) => id).filter(id => id !== "overview")]) {
      const included = area === "report" ? captured : captured.filter(section => section.id === area);
      const label = area === "report" ? "Code diligence" : included[0].label;
      const toc = included.map(section => `<li><a href="#${section.id}">${escape(section.label)}</a></li>`).join("");
      await pdf.setContent(`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${escape(title)} · ${escape(label)}</title><style>${overviewStyles}\n${stylesheet}</style></head><body>
        <header class="report-cover"><p class="report-kicker">CODE DILIGENCE · ${escape(area === "report" ? "ASSESSMENT REPORT" : label)}</p><h1>${escape(title)}</h1><p class="report-deck">${escape(description)}</p><nav aria-label="Contents"><h2>In this report</h2><ol>${toc}</ol></nav><section class="report-cover-note"><h2>What each tool provides</h2><dl>${assessmentTools.map(([name, purpose]) => `<div><dt>${escape(name)}</dt><dd>${escape(purpose)}</dd></div>`).join("")}</dl></section></header>
        ${included.map(section => `<article class="report-section${section.id === "overview" ? " report-overview" : ""}" id="${section.id}">${section.html}</article>`).join("")}
        </body></html>`);
      await pdf.evaluate(paths => {
        for (const link of document.querySelectorAll("a[data-report-path]")) {
          const section = paths.find(section => section.path === link.dataset.reportPath);
          if (section) link.href = `#${section.id}${link.dataset.reportAnchor ? "-" + link.dataset.reportAnchor : ""}`;
          else link.removeAttribute("href");
          delete link.dataset.reportPath;
          delete link.dataset.reportAnchor;
        }
      }, included.map(({path, id}) => ({path, id})));
      await pdf.evaluate(() => document.fonts.ready);
      await pdf.pdf({
        path: resolve(directory, `${area}.pdf`), format: "Letter", printBackground: true,
        preferCSSPageSize: true, tagged: true, outline: true, displayHeaderFooter: true,
        margin: {top: "0.5in", right: "0.5in", bottom: "0.5in", left: "0.5in"},
        headerTemplate: `<div style="font:8px Arial;color:#607080;box-sizing:border-box;width:100%;padding:0 0.5in;display:flex;justify-content:space-between"><span>${escape(title)}</span><span>${escape(label)}</span></div>`,
        footerTemplate: `<div style="font:8px Arial;color:#607080;box-sizing:border-box;width:100%;padding:0 0.5in;display:flex"><span style="width:33.333%">Code diligence</span><span style="width:33.333%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></span><span style="width:33.333%;text-align:right;white-space:nowrap">Data refresh date: ${escape(refreshDate)}</span></div>`,
      });
      console.log(`PDF ready: ${target} / ${area}`);
    }
  }
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
