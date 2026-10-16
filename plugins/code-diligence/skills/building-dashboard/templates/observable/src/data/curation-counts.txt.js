import {readFileSync} from "node:fs";
import {parse} from "yaml";
import {join} from "node:path";

const target = process.env.DILIGENCE_TARGET ?? null;
const directory = process.env.DILIGENCE_CURATION_DIR;
const count = filename => directory
  ? (parse(readFileSync(join(directory, filename), "utf8")).needs_review ?? []).length
  : null;

process.stdout.write(JSON.stringify({
  target,
  identity_needs_review: count("identity-merges.yaml"),
  fte_needs_review: count("fte-classification.yaml"),
  repo_needs_review: count("repo-classification.yaml")
}));
