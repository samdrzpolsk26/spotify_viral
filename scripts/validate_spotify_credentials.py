from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from music_intel.config import load_settings  # noqa: E402
from music_intel.etl.spotify_client import SpotifyAPIClient, SpotifyAPIError  # noqa: E402


def main() -> None:
    settings = load_settings()
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise SystemExit(
            "Missing Spotify credentials. Create a .env file with SPOTIFY_CLIENT_ID and "
            "SPOTIFY_CLIENT_SECRET."
        )

    client = SpotifyAPIClient.from_settings(settings)
    try:
        client.authenticate()
        payload = client.search_track("Neon Lights", market="US", limit=1)
    except SpotifyAPIError as exc:
        raise SystemExit(f"Spotify credential validation failed: {exc}") from exc

    item_count = len(payload.get("tracks", {}).get("items", []))
    print("Spotify credentials are valid.")
    print(f"Search endpoint returned {item_count} track(s).")


if __name__ == "__main__":
    main()
