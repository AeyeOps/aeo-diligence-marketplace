// src/data/curation-counts.txt.js
// Reads the three curation YAML files for the active target and emits a summary.
import { readFileSync, existsSync } from "node:fs";
import { parse as parseYAML } from "yaml";
import { join } from "node:path";

const target = process.env.DILIGENCE_TARGET ?? "unknown";
const curationDir = process.env.DILIGENCE_CURATION_DIR ?? "";

function countNeedsReview(filename) {
  const path = join(curationDir, filename);
  if (!existsSync(path)) return 0;
  const data = parseYAML(readFileSync(path, "utf8"));
  return (data?.needs_review ?? []).length;
}

process.stdout.write(JSON.stringify({
  target,
  identity_needs_review: countNeedsReview("identity-merges.yaml"),
  fte_needs_review: countNeedsReview("fte-classification.yaml"),
  repo_needs_review: countNeedsReview("repo-classification.yaml"),
}));
