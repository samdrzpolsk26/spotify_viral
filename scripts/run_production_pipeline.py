from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from music_intel.config import load_settings  # noqa: E402
from music_intel.etl.pipeline import run_pipeline  # noqa: E402


def main() -> None:
    settings = load_settings()
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise SystemExit(
            "Missing Spotify credentials. Create a .env file with SPOTIFY_CLIENT_ID and "
            "SPOTIFY_CLIENT_SECRET."
        )

    tables = run_pipeline(source="spotify_csv", persist=True)
    print("Production pipeline completed.")
    print(f"Chart rows: {len(tables['fact_chart_position']):,}")
    print(f"Tracks: {len(tables['dim_track']):,}")
    print(f"Artists: {len(tables['dim_artist']):,}")
    print(f"Viral signals: {len(tables['fact_viral_signal']):,}")


if __name__ == "__main__":
    main()
