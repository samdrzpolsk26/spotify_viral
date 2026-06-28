from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from music_intel.etl.pipeline import run_pipeline  # noqa: E402
from music_intel.etl.transform import split_artist_credit  # noqa: E402


def main() -> None:
    main_artists, featured_artists = split_artist_credit(
        "Luna Vale & Rio Nexo feat. Kai North, Mika Sol"
    )
    assert main_artists == ["Luna Vale", "Rio Nexo"]
    assert featured_artists == ["Kai North", "Mika Sol"]

    tables = run_pipeline(source="sample", persist=False)
    assert len(tables["dim_country"]) == 20
    assert len(tables["fact_chart_position"]) == 35_000
    assert "Neon Tide" in set(tables["fact_viral_signal"]["track_name"])

    print("Smoke test passed.")
    print(f"Countries: {len(tables['dim_country']):,}")
    print(f"Chart rows: {len(tables['fact_chart_position']):,}")
    print(f"Viral signals: {len(tables['fact_viral_signal']):,}")


if __name__ == "__main__":
    main()
