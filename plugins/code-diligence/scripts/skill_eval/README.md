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
# Single run (Haiku 4.5 by default — cheap, ~1 API call total)
~/.venvs/agent/bin/python run_eval.py

# Dump the prompt that would be sent, without calling the API
~/.venvs/agent/bin/python run_eval.py --dump-prompt

# Use a stronger judge model
~/.venvs/agent/bin/python run_eval.py --model claude-sonnet-4-6
```

## Stability

Haiku has ~±1-case-per-run noise on this bank. For a defensible result,
run 5 times and report aggregate accuracy:

```sh
for i in 1 2 3 4 5; do ~/.venvs/agent/bin/python run_eval.py | tail -8; done
```

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
- [`cases.yaml`](cases.yaml) — test bank (21 happy-path + 10 adversarial)
- [`review.md`](review.md) — claude-code-guide review that drove the
  adversarial cases and description tightening
- `results.json` / `results.md` — gitignored, regenerated each run

## Track record

Initial happy-path (21 cases): 21/21, avg confidence 96.7%.
After adding 10 adversarial cases: 29/31 baseline.
After three description tightenings (`interpreting-tool-output`,
`understanding-pe-diligence-axes`, `refreshing-target`,
`asking-diligence`, `ingesting-target`): 5/5 perfect runs at 31/31.

See `review.md` for the boundary-risk analysis driving the tightening.
