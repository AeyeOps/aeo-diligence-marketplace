"""Report the session target's refresh time from its warehouse record."""
import os
from pathlib import Path

import duckdb

from code_diligence.settings.loader import load_target_settings, settings_beside


def main() -> None:
    warehouse_value = os.environ.get("DILIGENCE_WAREHOUSE_PATH")
    if not warehouse_value:
        return
    warehouse = Path(warehouse_value).expanduser()
    settings = load_target_settings(settings_beside(warehouse))
    print("## code-diligence target")
    if not warehouse.exists():
        print(f"- {settings.target_name}: not yet ingested")
        return
    with duckdb.connect(str(warehouse), read_only=True) as conn:
        row = conn.execute("SELECT last_refreshed_at FROM targets WHERE target_id = ?", [settings.target_id]).fetchone()
    refreshed = row[0] if row else None
    print(f"- {settings.target_name}: last completed refresh {refreshed or 'not recorded'}")


if __name__ == "__main__":
    main()
