"""Build an isolated Observable project from a target warehouse."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import duckdb

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = PLUGIN_ROOT / "skills" / "aeo-diligence-dashboard" / "templates" / "observable"


def render_dashboard(
    *,
    warehouse_path: Path,
    output_path: Path,
    target_id: str | None = None,
    curation_dir: Path | None = None,
    allow_working_pattern_card: bool = False,
) -> None:
    """Build all target routes without modifying templates or the input warehouse."""
    warehouse_path = warehouse_path.expanduser().resolve(strict=True)
    output_path = output_path.expanduser().resolve()
    if warehouse_path.is_relative_to(output_path) or TEMPLATE_DIR.resolve().is_relative_to(output_path):
        raise ValueError("dashboard output must not contain the warehouse or plugin template")
    with duckdb.connect(str(warehouse_path), read_only=True) as conn:
        targets = [row[0] for row in conn.execute("SELECT target_id FROM targets ORDER BY target_id").fetchall()]
    if target_id is not None and target_id not in targets:
        raise ValueError(f"target {target_id!r} is not in the warehouse")
    if not (TEMPLATE_DIR / "node_modules").exists():
        subprocess.run(["npm", "ci", "--silent"], cwd=TEMPLATE_DIR, check=True)
    with tempfile.TemporaryDirectory(prefix="code-diligence-render-") as temp:
        project = Path(temp) / "observable"
        shutil.copytree(TEMPLATE_DIR, project, ignore=shutil.ignore_patterns("node_modules", "dist", ".observablehq"))
        (project / "node_modules").symlink_to(TEMPLATE_DIR / "node_modules", target_is_directory=True)
        data_dir = project / "src" / "data"
        shutil.copyfile(warehouse_path, data_dir / "warehouse.duckdb")
        (data_dir / "config.json").write_text(json.dumps({
            "allow_working_pattern_card": allow_working_pattern_card,
            "targets": targets,
        }))
        env = os.environ.copy()
        env.pop("DILIGENCE_TARGET", None)
        env.pop("DILIGENCE_CURATION_DIR", None)
        if target_id is not None:
            env["DILIGENCE_TARGET"] = target_id
        elif len(targets) == 1:
            env["DILIGENCE_TARGET"] = targets[0]
        if curation_dir is not None:
            env["DILIGENCE_CURATION_DIR"] = str(curation_dir.expanduser().resolve())
        subprocess.run(["npm", "run", "build", "--silent"], cwd=project, check=True, env=env)
        if output_path.exists():
            shutil.rmtree(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(project / "dist", output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-id")
    parser.add_argument("--curation-dir", type=Path)
    parser.add_argument("--allow-working-pattern", action="store_true")
    args = parser.parse_args()
    render_dashboard(
        warehouse_path=args.warehouse, output_path=args.output,
        target_id=args.target_id, curation_dir=args.curation_dir,
        allow_working_pattern_card=args.allow_working_pattern,
    )


if __name__ == "__main__":
    main()
