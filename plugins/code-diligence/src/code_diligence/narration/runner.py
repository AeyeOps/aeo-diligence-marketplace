"""Run the diligence-narrator agent for each (axis, section_key) of a target."""
import os
import subprocess
from pathlib import Path
from typing import Literal

from .taxonomy import TAXONOMY


Tier = Literal["quick", "full"]


def run_narrator_for_target(
    *, warehouse_path: Path, target_id: str, tier: Tier,
) -> None:
    for section in TAXONOMY:
        _invoke_narrator_agent(
            warehouse_path=warehouse_path,
            target_id=target_id,
            axis=section.axis,
            section_key=section.section_key,
            tier=tier,
        )


def _invoke_narrator_agent(
    *, warehouse_path: Path, target_id: str, axis: str, section_key: str, tier: Tier,
) -> None:
    env = os.environ.copy()
    env["DILIGENCE_WAREHOUSE_PATH"] = str(warehouse_path)
    prompt = (
        f"target_id={target_id}\n"
        f"axis={axis}\n"
        f"section_key={section_key}\n"
        f"tier={tier}\n\n"
        f"Generate the narrative for this card and persist it via write_narrative."
    )
    subprocess.run(
        ["claude", "--agent", "diligence-narrator", "-p", prompt],
        env=env, check=True, capture_output=True, text=True, timeout=120,
    )
