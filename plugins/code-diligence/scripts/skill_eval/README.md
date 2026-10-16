# Skill-description trigger eval

Non-interactive harness that tests whether each diligence skill's
frontmatter `description:` triggers correctly for representative user
messages. Useful when adding a new skill, renaming a sibling, or
suspecting a description has drifted.

## How it works

1. Reads `description:` from each `skills/*/SKILL.md` frontmatter.
2. Reads test cases from `cases.yaml` — each has `prompt`, `expected`
   (the skill that should fire, or `null`), and an optional `rationale`.
3. Builds one system prompt listing the 6 skill descriptions plus a
   "you are a skill router" instruction.
4. Sends a single `claude -p --disable-slash-commands` call with all
   test prompts in the user message. The judge model returns one JSON
   line per prompt with `best_skill` + `confidence`.
5. Compares predictions to `expected`, writes `results.json` and
   `results.md`. Misses are printed to stdout.

`--disable-slash-commands` prevents skills installed in the host's
Claude Code session from leaking into the routing decision — the judge
sees only the 6 descriptions from our system prompt.

## Run

```sh
# Run from the plugin root using its project dependencies
uv run python scripts/skill_eval/run_eval.py

# Dump the prompt that would be sent, without calling the API
uv run python scripts/skill_eval/run_eval.py --dump-prompt

# Use a stronger judge model
uv run python scripts/skill_eval/run_eval.py --model claude-sonnet-4-6
```

Run results describe one routing sample; they are not a deterministic skill acceptance test.

## Adding a case

Append to `cases.yaml`:

```yaml
  - id: <short-kebab-id>
    prompt: "<one-line user message>"
    expected: <skill-name | null>
    rationale: "<optional: which sibling could confuse and why>"
```

Negative cases (`expected: null`) probe over-triggering — the harness
counts them in precision but not recall.

## Files

- [`run_eval.py`](run_eval.py) — harness
- [`cases.yaml`](cases.yaml) — test bank
- `results.json` / `results.md` — gitignored, regenerated each run
