"""Build the Observable dashboard from a warehouse."""
import json
import os
import shutil
import subprocess
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = PLUGIN_ROOT / "skills" / "building-dashboard" / "templates" / "observable"


def render_dashboard(
    *,
    warehouse_path: Path,
    output_path: Path,
    target_id: str | None = None,
    curation_dir: Path | None = None,
    allow_working_pattern_card: bool = False,
) -> None:
    """Copy warehouse into Observable project, run build, copy dist to output_path."""
    if not (TEMPLATE_DIR / "node_modules").exists():
        subprocess.run(["npm", "install", "--silent"], cwd=TEMPLATE_DIR, check=True)

    data_dir = TEMPLATE_DIR / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target_warehouse = data_dir / "warehouse.duckdb"
    shutil.copy(warehouse_path, target_warehouse)
    (data_dir / "config.json").write_text(
        json.dumps({"allow_working_pattern_card": bool(allow_working_pattern_card)})
    )

    env = {**os.environ}
    if target_id is not None:
        env["DILIGENCE_TARGET"] = target_id
    if curation_dir is not None:
        env["DILIGENCE_CURATION_DIR"] = str(curation_dir)

    subprocess.run(["npm", "run", "build", "--silent"], cwd=TEMPLATE_DIR, check=True, env=env)

    dist = TEMPLATE_DIR / "dist"
    if output_path.exists():
        shutil.rmtree(output_path)
    shutil.copytree(dist, output_path)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--warehouse", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--target-id", type=str, default=None)
    p.add_argument("--curation-dir", type=Path, default=None)
    p.add_argument("--allow-working-pattern", action="store_true", default=False)
    args = p.parse_args()
    render_dashboard(
        warehouse_path=args.warehouse,
        output_path=args.output,
        target_id=args.target_id,
        curation_dir=args.curation_dir,
        allow_working_pattern_card=args.allow_working_pattern,
    )
