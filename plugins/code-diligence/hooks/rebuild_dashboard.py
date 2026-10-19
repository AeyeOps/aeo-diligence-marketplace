"""Rebuild the active target with its configured output and privacy settings."""
import os
from pathlib import Path

from code_diligence.dashboard.render import render_dashboard
from code_diligence.settings.loader import load_target_settings, settings_beside


def main() -> None:
    warehouse_value = os.environ.get("DILIGENCE_WAREHOUSE_PATH")
    if not warehouse_value:
        return
    warehouse = Path(warehouse_value).expanduser().resolve()
    settings_path = settings_beside(warehouse)
    settings = load_target_settings(settings_path)
    if Path(settings.storage.warehouse_path).expanduser().resolve() != warehouse:
        raise RuntimeError(f"{settings_path} names a different warehouse; rebuild with the dashboard skill")
    render_dashboard(
        warehouse_path=warehouse,
        output_path=Path(settings.dashboard.output_path),
        target_id=settings.target_id,
        curation_dir=Path(settings.storage.curation_dir),
        allow_working_pattern_card=settings.heuristics.allow_working_pattern_card,
    )


if __name__ == "__main__":
    main()
