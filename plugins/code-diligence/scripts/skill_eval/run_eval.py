#!/usr/bin/env python3
"""Non-interactive skill-description trigger eval for code-diligence.

Loads the 6 diligence skill descriptions and a test bank (cases.yaml), then
asks `claude -p` to act as a description-only router: for each test prompt,
which skill (if any) would it pick. `--disable-slash-commands` prevents the
host's installed skills from leaking into the routing decision; the only
descriptions the judge sees are the ones in our system prompt.

Output:
  - Per-case predicted vs expected (printed + JSON in results.json)
  - Confusion matrix
  - Precision / recall per skill
  - Markdown summary (results.md)

The eval is non-interactive: one `claude -p` invocation per run, no
human in loop. Designed to be cheap (Haiku, single batched call) and
reproducible (tools and MCP are disabled for the judge).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent.parent
SKILLS_DIR = PLUGIN_ROOT / "skills"
CASES_PATH = HERE / "cases.yaml"
RESULTS_JSON = HERE / "results.json"
RESULTS_MD = HERE / "results.md"

DEFAULT_MODEL = "haiku"


def load_skill_descriptions() -> dict[str, str]:
    """Parse each skills/<name>/SKILL.md frontmatter; return {name: description}."""
    descriptions = {}
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        parts = skill_md.read_text(encoding="utf-8").split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f"No frontmatter in {skill_md}")
        metadata = yaml.safe_load(parts[1])
        descriptions[metadata["name"]] = metadata["description"]
    return descriptions


def load_cases() -> list[dict]:
    return yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def build_judge_prompt(skills: dict[str, str], cases: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the judge call."""
    skill_block = "\n".join(
        f"{i+1}. {name} — {desc}" for i, (name, desc) in enumerate(skills.items())
    )
    system = (
        "You are a skill router. You will receive a list of available skills "
        "(name + description) and a batch of user messages. For each user message, "
        "decide which single skill (if any) is the best match based ONLY on the "
        "descriptions provided — do not infer from prior knowledge.\n\n"
        f"Available skills:\n{skill_block}\n\n"
        'For EACH test prompt, output exactly one JSON line of the form:\n'
        '  {"id": "<prompt-id>", "best_skill": "<skill-name>" | null, "confidence": 0-100}\n\n'
        "Rules:\n"
        "- Output JSON Lines (one object per line). No prose, no markdown fences.\n"
        '- `best_skill` must be a skill name from the list above, or the literal null.\n'
        "- Use null when no skill clearly applies.\n"
        "- `confidence` is your subjective certainty (0=guess, 100=obvious match)."
    )
    user_lines = [f"id={c['id']}: {c['prompt']}" for c in cases]
    user = "Classify each of the following test prompts:\n\n" + "\n".join(user_lines)
    return system, user


def call_judge(system: str, user: str, model: str) -> str:
    """Invoke `claude -p` with our judge system prompt; return stdout."""
    proc = subprocess.run(
        [
            "claude",
            "-p",
            "--disable-slash-commands",
            "--tools",
            "",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers": {}}',
            "--no-session-persistence",
            "--model",
            model,
            "--system-prompt",
            system,
            user,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"claude -p failed: {proc.stderr}\n")
        raise SystemExit(proc.returncode)
    return proc.stdout


def parse_judge_output(stdout: str) -> dict[str, dict]:
    """Pull out {id: {best_skill, confidence}} from JSON-lines output."""
    out: dict[str, dict] = {}
    for line in stdout.splitlines():
        s = line.strip()
        if not (s.startswith("{") and s.endswith("}")):
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if "id" in obj and "best_skill" in obj:
            if obj["id"] in out:
                raise ValueError(f"Duplicate judge result: {obj['id']}")
            out[obj["id"]] = obj
    return out


def score(cases: list[dict], preds: dict[str, dict]) -> dict:
    """Compute per-case correctness, per-skill precision/recall, totals."""
    expected_ids = {case["id"] for case in cases}
    if set(preds) != expected_ids:
        raise ValueError(f"Judge output IDs do not match the cases: missing={sorted(expected_ids - set(preds))}, unexpected={sorted(set(preds) - expected_ids)}")
    valid_skills = set(load_skill_descriptions())
    for prediction in preds.values():
        if prediction["best_skill"] is not None and prediction["best_skill"] not in valid_skills:
            raise ValueError(f"Unknown skill in judge output: {prediction['best_skill']}")
    per_skill_tp: dict[str, int] = defaultdict(int)
    per_skill_fp: dict[str, int] = defaultdict(int)
    per_skill_fn: dict[str, int] = defaultdict(int)
    details: list[dict] = []
    correct = 0
    for c in cases:
        cid, expected = c["id"], c["expected"]
        pred = preds.get(cid, {})
        predicted = pred.get("best_skill")
        ok = predicted == expected
        if ok:
            correct += 1
        details.append(
            {
                "id": cid,
                "prompt": c["prompt"],
                "expected": expected,
                "predicted": predicted,
                "confidence": pred.get("confidence"),
                "ok": ok,
            }
        )
        if expected is not None and predicted == expected:
            per_skill_tp[expected] += 1
        if expected is not None and predicted != expected:
            per_skill_fn[expected] += 1
        if predicted is not None and predicted != expected:
            per_skill_fp[predicted] += 1

    skills = sorted({c["expected"] for c in cases if c["expected"]})
    per_skill = {}
    for sk in skills:
        tp, fp, fn = per_skill_tp[sk], per_skill_fp[sk], per_skill_fn[sk]
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        per_skill[sk] = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall}

    return {
        "total": len(cases),
        "correct": correct,
        "accuracy": correct / len(cases) if cases else 0.0,
        "per_skill": per_skill,
        "details": details,
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Skill-description trigger eval",
        "",
        f"Cases run: **{report['total']}** · Correct: **{report['correct']}** · "
        f"Accuracy: **{report['accuracy']:.0%}**",
        "",
        "## Per-skill precision / recall",
        "",
        "| Skill | TP | FP | FN | Precision | Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for sk, m in report["per_skill"].items():
        p = f"{m['precision']:.0%}" if m["precision"] is not None else "—"
        r = f"{m['recall']:.0%}" if m["recall"] is not None else "—"
        lines.append(f"| `{sk}` | {m['tp']} | {m['fp']} | {m['fn']} | {p} | {r} |")
    lines += ["", "## Misses", ""]
    misses = [d for d in report["details"] if not d["ok"]]
    if not misses:
        lines.append("_None — all cases routed to the expected skill._")
    else:
        lines.append("| Case | Prompt | Expected | Predicted | Conf |")
        lines.append("|---|---|---|---|---:|")
        for d in misses:
            prompt = d["prompt"].replace("|", "\\|")
            exp = f"`{d['expected']}`" if d["expected"] else "_null_"
            pred = f"`{d['predicted']}`" if d["predicted"] else "_null_"
            conf = d["confidence"] if d["confidence"] is not None else "—"
            lines.append(f"| `{d['id']}` | {prompt} | {exp} | {pred} | {conf} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--dump-prompt",
        action="store_true",
        help="Print the system+user prompt and exit (no API call).",
    )
    args = parser.parse_args()

    skills = load_skill_descriptions()
    cases = load_cases()
    system, user = build_judge_prompt(skills, cases)

    if args.dump_prompt:
        print("=== SYSTEM ===\n" + system + "\n\n=== USER ===\n" + user)
        return 0

    print(f"Skills under test: {len(skills)}")
    print(f"Cases: {len(cases)}")
    print(f"Calling {args.model} via `claude -p`…", flush=True)
    stdout = call_judge(system, user, args.model)
    preds = parse_judge_output(stdout)
    report = score(cases, preds)

    RESULTS_JSON.write_text(
        json.dumps({"model": args.model, **report}, indent=2),
        encoding="utf-8",
    )
    write_markdown(report, RESULTS_MD)

    print(f"\nAccuracy: {report['correct']}/{report['total']} = {report['accuracy']:.0%}")
    print(f"JSON:     {RESULTS_JSON}")
    print(f"Markdown: {RESULTS_MD}")
    if report["accuracy"] < 1.0:
        misses = [d for d in report["details"] if not d["ok"]]
        print(f"\n{len(misses)} miss(es):")
        for d in misses:
            print(
                f"  [{d['id']:>16}] expected={d['expected']!r:<35} "
                f"got={d['predicted']!r}  conf={d['confidence']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
