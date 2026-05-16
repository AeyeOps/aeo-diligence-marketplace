# git-fame

Casper da Costa-Luis's per-author attribution tool. Canonical source for `ownership_share`.

## Warehouse mapping

| git-fame output | Warehouse table | Notes |
|---|---|---|
| `loc`, `coms`, `fils` per author | `ownership_share (repo_id, author_email, owned_loc, owned_files, source='git-fame')` | Canonical for People `knowledge_concentration` and `hero_dependency_register` |

## Invocation (`src/code_diligence/tools/git_fame.py`)

The wrapper shells out to:

    git fame --json --silent-progress -e --bytype --git-dir <repo>/.git <repo>

- `--json` emits the `{columns: [...], data: [[...]]}` payload that `parse_git_fame_json` consumes.
- `--silent-progress` suppresses the TTY progress bar so stdout stays parseable.
- `-e` keys rows by email rather than display name (this is what makes git-fame the canonical, email-keyed source).
- `--bytype` adds per-file-type breakdown; `parse_git_fame_json` only reads the aggregate columns, but the flag does not break parsing.
- Timeout: 300s. Non-zero exit raises `GitFameError`; `isolated()` records a `tool_failures` row of class `runtime`.

## Why canonical

- **Email-keyed.** Joins cleanly against `authors` and `identity_map` without name fuzzing.
- **Surviving authorship.** `loc` is computed from `git blame` at HEAD, not from a historical commit count. A 2014 commit later refactored does not count toward 2024 ownership.

## Persistence shape

`persist_git_fame` deletes prior `ownership_share` rows for `(repo_id, source='git-fame')` and re-inserts. The wrapper persists `owned_loc` and `owned_files` per author; the `coms` (commit count) column is parsed into the `GitFameRecord` dataclass but is not written to the warehouse — `commits_fact` covers per-commit detail.

## Quirks

- **Email normalization.** `parse_git_fame_json` lower-cases emails and strips whitespace so two casings of the same address collapse to one row.
- **Column-index defensiveness.** The parser uses `cols.index(...)` with positional fallbacks so a column reorder in a future git-fame release degrades to wrong values rather than a crash — watch the Health tab if values look off after a git-fame upgrade.
- **No generated-code filter.** git-fame respects `.gitattributes` for binary detection but has no built-in way to skip generated source. Filter at the dashboard layer via `repo_classification`.

## Cross-check

Disagreements with git-truck (byte-size-proxied, name-based) surface as Health-tab rows. Always trust git-fame as the answer; see `references/cross-check-policy.md`.
