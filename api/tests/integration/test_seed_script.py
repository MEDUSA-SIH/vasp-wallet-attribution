"""Seed script test."""

from __future__ import annotations

import subprocess
import sys


def test_seed_demo_runs_clean() -> None:
    """Run the seed script as a subprocess; it must exit 0."""
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.seed_demo_data"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    # The seed log line includes case / address / tx counts.
    assert "seed_demo_data.loaded" in proc.stdout
