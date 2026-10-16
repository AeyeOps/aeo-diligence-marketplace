"""Report target refresh times from warehouse records."""
from pathlib import Path

import duckdb

from code_diligence.settings.loader import load_target_settings


def main() -> None:
    settings_paths = sorted((Path.home() / ".claude").glob("code-diligence-*.local.md"))
    if not settings_paths:
        return
    print("## code-diligence targets")
    for path in settings_paths:
        settings = load_target_settings(path)
        warehouse = Path(settings.storage.warehouse_path).expanduser()
        if not warehouse.exists():
            print(f"- {settings.target_name}: not yet ingested")
            continue
        with duckdb.connect(str(warehouse), read_only=True) as conn:
            row = conn.execute("SELECT last_refreshed_at FROM targets WHERE target_id = ?", [settings.target_id]).fetchone()
        refreshed = row[0] if row else None
        print(f"- {settings.target_name}: last completed refresh {refreshed or 'not recorded'}")


if __name__ == "__main__":
    main()
