from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from music_intel.etl.pipeline import run_pipeline  # noqa: E402


if __name__ == "__main__":
    tables = run_pipeline(source="sample", persist=True)
    print("Demo pipeline completed.")
    print(f"fact_chart_position rows: {len(tables['fact_chart_position']):,}")
    print(f"fact_viral_signal rows: {len(tables['fact_viral_signal']):,}")
