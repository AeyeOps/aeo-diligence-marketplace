// observablehq.config.js
export default {
  root: "src",
  title: "code-diligence",
  pages: [
    { name: "Portfolio", path: "/" },
    { name: "About", path: "/about" },
  ],
  theme: ["air", "near-midnight"],
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>">',
  footer: "code-diligence — generated dashboard. See methodology in About.",
};
