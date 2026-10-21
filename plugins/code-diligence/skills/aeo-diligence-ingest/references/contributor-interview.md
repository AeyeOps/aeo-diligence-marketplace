# Contributor classification interview

Repository history establishes which identities appear. The user establishes who they represent and how they should be classified for this assessment.

## Present the assessed list

After collection, query every distinct author identity for the target, including identities already labeled by a heuristic. Present a compact table with display name, exact email or login, known aliases, repositories, commit count, and current classification with its source. Group aliases only when the user has already confirmed they are one person; show other possible matches as suggestions.

Ask the user to classify the list as Employee, Contractor, Bot/automation, or Unknown, and to resolve proposed aliases. Carry forward explicit answers from this conversation or the target's saved interview decisions. A generated `source: analyst` label alone does not prove the user supplied it. On refresh, ask only about new, unresolved, or contradicted identities.

For automation identities, ask whose work they deliver and whether the account is dedicated to one person or shared. A bot marker establishes an account naming convention, not independent human contribution. The user's answer determines the target's treatment. Do not assign a shared account to one person, invent employment status, or redistribute its commits from activity patterns. If the existing identity-level curation cannot express the requested treatment, state that specific limit before changing the data model or source-writing code.

Offer evidence-based suggestions clearly as suggestions. Domains, cadence, tenure, repository breadth, and confidence scores do not replace the user's answers. Wait for answers to unresolved classification questions; continue independent analysis while waiting. An explicit Unknown answer is a valid result.

## Save and apply the answers

Keep `heuristics.fte_inference: false` in this target's `diligence.local.md`. Before a refresh, move any unconfirmed heuristic entries from `confirmed` to `needs_review` in `fte-classification.yaml` so they remain available as suggestions.

Store the user's labels in the existing `fte-classification.yaml` under `storage.curation_dir`, using `source: analyst` and the existing values `fte`, `contractor`, `bot`, or `unknown`. Store confirmed alias relationships in the same target's `identity-merges.yaml`. Preserve other saved decisions. Target names, account mappings, and employment decisions stay in the consuming repository, outside the reusable skill.

Apply those files through the runtime's existing `code_diligence.curation.apply.apply_identity` and `apply_fte` functions after the CLI has closed its connection. Query the canonical identity and classification totals through the warehouse MCP to confirm the answers took effect. Then regenerate affected People narratives and rebuild the dashboard. A classification-only correction uses the current assessment; it does not require fetching repositories or rerunning analyzers.
