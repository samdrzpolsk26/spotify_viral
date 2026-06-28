from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    requests = None

from music_intel.config import Settings, load_settings


class SpotifyAPIError(RuntimeError):
    pass


class SpotifyEndpointUnavailable(RuntimeError):
    pass


@dataclass
class SpotifyAPIClient:
    client_id: str
    client_secret: str
    access_token: str | None = None
    expires_at: float = 0.0
    base_url: str = "https://api.spotify.com/v1"
    auth_url: str = "https://accounts.spotify.com/api/token"
    max_retries: int = 3

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "SpotifyAPIClient":
        settings = load_settings() if settings is None else settings
        if not settings.spotify_client_id or not settings.spotify_client_secret:
            raise SpotifyAPIError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET.")
        return cls(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
        )

    def authenticate(self) -> None:
        if requests is None:
            raise SpotifyAPIError("The requests package is required for Spotify API calls.")

        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        auth_header = base64.b64encode(credentials).decode("utf-8")
        response = requests.post(
            self.auth_url,
            headers={"Authorization": f"Basic {auth_header}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise SpotifyAPIError(f"Spotify auth failed: {response.status_code} {response.text}")

        payload = response.json()
        self.access_token = payload["access_token"]
        self.expires_at = time.time() + int(payload.get("expires_in", 3600)) - 60

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if requests is None:
            raise SpotifyAPIError("The requests package is required for Spotify API calls.")

        if not self.access_token or time.time() >= self.expires_at:
            self.authenticate()

        response = None
        for attempt in range(self.max_retries):
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
                **kwargs,
            )

            if response.status_code != 429:
                break

            retry_after = int(response.headers.get("Retry-After", "2"))
            time.sleep(retry_after + attempt)

        if response is None:
            raise SpotifyAPIError("Spotify request failed before a response was created.")

        if response.status_code >= 400:
            raise SpotifyAPIError(f"Spotify request failed: {response.status_code} {response.text}")
        return response.json()

    def search_track(self, query: str, market: str, limit: int = 5) -> dict[str, Any]:
        return self.request(
            "GET",
            "/search",
            params={"q": query, "type": "track", "market": market, "limit": limit},
        )

    def get_track(self, track_id: str, market: str | None = None) -> dict[str, Any]:
        params = {"market": market} if market else None
        return self.request("GET", f"/tracks/{track_id}", params=params)

    def get_tracks(self, track_ids: list[str], market: str | None = None) -> list[dict[str, Any]]:
        tracks = []
        for chunk in _chunks(track_ids, 50):
            params: dict[str, Any] = {"ids": ",".join(chunk)}
            if market:
                params["market"] = market
            payload = self.request("GET", "/tracks", params=params)
            tracks.extend([track for track in payload.get("tracks", []) if track])
        return tracks

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        return self.request("GET", f"/artists/{artist_id}")

    def get_artists(self, artist_ids: list[str]) -> list[dict[str, Any]]:
        artists = []
        for chunk in _chunks(artist_ids, 50):
            payload = self.request("GET", "/artists", params={"ids": ",".join(chunk)})
            artists.extend([artist for artist in payload.get("artists", []) if artist])
        return artists

    def get_audio_features(self, track_id: str) -> dict[str, Any]:
        """Requires an app with access to Spotify's restricted audio features endpoint."""
        return self.request("GET", f"/audio-features/{track_id}")

    def get_many_audio_features(self, track_ids: list[str]) -> list[dict[str, Any]]:
        """Requires an app with access to Spotify's restricted audio features endpoint."""
        features = []
        for chunk in _chunks(track_ids, 100):
            payload = self.request("GET", "/audio-features", params={"ids": ",".join(chunk)})
            features.extend([feature for feature in payload.get("audio_features", []) if feature])
        return features


def explain_spotify_data_limitations() -> str:
    return (
        "Spotify Web API does not expose a simple official Top 50 charts endpoint, and "
        "new/development apps may not access audio_features. Keep the ETL contract stable "
        "and plug in an approved Spotify app, Spotify Charts export, or another music data source."
    )


def _chunks(values: list[str], chunk_size: int):
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]
