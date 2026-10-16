# git-fame

Casper da Costa-Luis's per-author attribution tool. Canonical source for `ownership_share`.

## Warehouse mapping

| git-fame output | Warehouse table | Notes |
|---|---|---|
| `loc`, `coms`, `fils` per author | `ownership_share (repo_id, author_email, owned_loc, owned_files, source='git-fame')` | Canonical for People `knowledge_concentration` and `hero_dependency_register` |

## Invocation (`src/code_diligence/tools/git_fame.py`)

The wrapper shells out to:

    git-fame --format=json --show=name,email <repo>

The JSON payload contains `columns` and `data`; `Author` is `Name <email>`, with `loc`, `coms`, and `fils` numeric columns. The parser uses those named columns and rejects an unexpected format. Timeout: 300 seconds. Failures are recorded by the ingest isolation boundary.

## Why canonical

- **Email-keyed.** Joins cleanly against `authors` and `identity_map` without name fuzzing.
- **Surviving authorship.** `loc` is computed from `git blame` at HEAD, not from a historical commit count. A 2014 commit later refactored does not count toward 2024 ownership.

## Persistence shape

`persist_git_fame` deletes prior `ownership_share` rows for `(repo_id, source='git-fame')` and re-inserts. The wrapper persists `owned_loc` and `owned_files` per author; the `coms` (commit count) column is parsed into the `GitFameRecord` dataclass but is not written to the warehouse — `commits_fact` covers per-commit detail.

## Quirks

- **Email normalization.** `parse_git_fame_json` lower-cases emails and strips whitespace so two casings of the same address collapse to one row.
- **No generated-code filter.** git-fame respects `.gitattributes` for binary detection but has no built-in way to skip generated source. Filter at the dashboard layer via `repo_classification`.

## Cross-check

git-truck supplies a separate name-based, change-count ownership estimate. Use git-fame for surviving LOC ownership; see `references/cross-check-policy.md`.
