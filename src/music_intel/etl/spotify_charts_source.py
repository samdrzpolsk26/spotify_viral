from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import datetime
import random
from music_intel.config import Settings, load_countries, load_settings
from music_intel.paths import PROJECT_ROOT, RAW_DIR

from .spotify_client import SpotifyAPIClient, SpotifyAPIError

GENRE_FEATURE_BASE = {
    "reggaeton": {
        "danceability": 0.84,
        "energy": 0.78,
        "valence": 0.72,
        "acousticness": 0.18,
        "liveness": 0.16,
        "tempo": 94,
    },
    "afrobeats": {
        "danceability": 0.79,
        "energy": 0.73,
        "valence": 0.70,
        "acousticness": 0.22,
        "liveness": 0.18,
        "tempo": 104,
    },
    "dance_pop": {
        "danceability": 0.76,
        "energy": 0.80,
        "valence": 0.66,
        "acousticness": 0.16,
        "liveness": 0.17,
        "tempo": 122,
    },
    "hip_hop": {
        "danceability": 0.74,
        "energy": 0.68,
        "valence": 0.56,
        "acousticness": 0.20,
        "liveness": 0.19,
        "tempo": 88,
    },
    "indie_pop": {
        "danceability": 0.62,
        "energy": 0.58,
        "valence": 0.50,
        "acousticness": 0.38,
        "liveness": 0.15,
        "tempo": 116,
    },
    "latin_pop": {
        "danceability": 0.78,
        "energy": 0.72,
        "valence": 0.75,
        "acousticness": 0.25,
        "liveness": 0.18,
        "tempo": 100,
    },
    "k_pop": {
        "danceability": 0.73,
        "energy": 0.83,
        "valence": 0.68,
        "acousticness": 0.12,
        "liveness": 0.20,
        "tempo": 128,
    },
    "sad_pop": {
        "danceability": 0.52,
        "energy": 0.44,
        "valence": 0.30,
        "acousticness": 0.54,
        "liveness": 0.13,
        "tempo": 78,
    },
    "rock": {
        "danceability": 0.56,
        "energy": 0.84,
        "valence": 0.48,
        "acousticness": 0.10,
        "liveness": 0.26,
        "tempo": 132,
    },
}



SPOTIFY_ID_RE = re.compile(r"([A-Za-z0-9]{22})")
DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")

COLUMN_ALIASES = {
    "rank": {"rank", "position", "chart_position", "current_rank"},
    "track_id": {"track_id", "spotify_id", "id"},
    "uri": {"uri", "track_uri", "spotify_uri", "url", "track_url"},
    "track_name": {"track_name", "song", "title", "track", "name"},
    "artist_credit": {"artist_credit", "artist_names", "artist", "artists", "artist_name"},
    "streams": {"streams", "stream_count", "plays"},
    "country_code": {"country_code", "market", "country", "country_iso2"},
    "snapshot_date": {"snapshot_date", "date", "chart_date", "week", "chart_week"},
    "genre": {"genre", "primary_genre"},
    "release_date": {"release_date", "released_at"},
}


def load_spotify_csv_dataset(settings: Settings | None = None) -> dict[str, pd.DataFrame]:
    settings = load_settings() if settings is None else settings
    countries = load_countries()
    raw_dir = _resolve_raw_dir(settings.raw_spotify_charts_dir)
    raw_charts = load_spotify_chart_csvs(raw_dir=raw_dir, countries=countries)

    use_client = bool(settings.spotify_client_id and settings.spotify_client_secret)
    if use_client:
        client = SpotifyAPIClient.from_settings(settings)
        raw_charts, tracks, audio_features = enrich_with_spotify(
            raw_charts=raw_charts,
            client=client,
            audio_features_enabled=settings.spotify_audio_features_enabled,
        )
    else:
        tracks = build_track_dimension_from_raw(raw_charts)
        audio_features = build_proxy_audio_features(tracks)

    return {
        "countries": countries,
        "tracks": tracks,
        "audio_features": audio_features,
        "raw_chart_entries": raw_charts,
    }


def load_spotify_chart_csvs(raw_dir: Path, countries: pd.DataFrame) -> pd.DataFrame:
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw charts directory does not exist: {raw_dir}. "
            "Add Spotify Charts CSV exports there before running source='spotify_csv'."
        )

    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir}.")

    frames = [_normalize_chart_csv(path, countries) for path in files]
    output = pd.concat(frames, ignore_index=True)
    output = output.drop_duplicates(["snapshot_date", "country_code", "rank", "track_id"])
    output = output.sort_values(["snapshot_date", "country_code", "rank"]).reset_index(drop=True)
    return output


def enrich_with_spotify(
    raw_charts: pd.DataFrame,
    client: SpotifyAPIClient,
    audio_features_enabled: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    chart = raw_charts.copy()
    spotify_ids = {
        track_id
        for track_id in chart["track_id"].dropna().astype(str).unique()
        if _looks_like_spotify_track_id(track_id)
    }

    missing_id_rows = chart[~chart["track_id"].astype(str).map(_looks_like_spotify_track_id)]
    discovered_ids = _search_missing_track_ids(missing_id_rows, client)
    if discovered_ids:
        chart["track_id"] = chart.apply(
            lambda row: discovered_ids.get(
                _track_lookup_key(row["track_name"], row["artist_credit"], row["country_code"]),
                row["track_id"],
            ),
            axis=1,
        )
        spotify_ids.update(discovered_ids.values())

    metadata = _fetch_track_metadata(client, sorted(spotify_ids))
    chart = _apply_metadata_to_chart(chart, metadata)
    tracks = build_track_dimension_from_raw(chart)

    if audio_features_enabled:
        audio_features = _fetch_audio_features(client, tracks["track_id"].tolist())
        if audio_features.empty:
            audio_features = build_proxy_audio_features(tracks)
    else:
        audio_features = build_proxy_audio_features(tracks)

    return chart, tracks, audio_features


def build_track_dimension_from_raw(raw_charts: pd.DataFrame) -> pd.DataFrame:
    return (
        raw_charts[["track_id", "track_name", "artist_credit", "genre", "release_date"]]
        .sort_values("release_date")
        .drop_duplicates("track_id", keep="last")
        .reset_index(drop=True)
    )


def build_proxy_audio_features(tracks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in tracks.itertuples(index=False):
        genre_key = _map_genre_to_feature_key(str(row.genre))
        base = GENRE_FEATURE_BASE[genre_key]
        noise = _stable_noise(str(row.track_id), len(base))
        rows.append(
            {
                "track_id": row.track_id,
                "danceability": _clip01(base["danceability"] + noise[0] * 0.04),
                "energy": _clip01(base["energy"] + noise[1] * 0.05),
                "valence": _clip01(base["valence"] + noise[2] * 0.06),
                "acousticness": _clip01(base["acousticness"] + noise[3] * 0.05),
                "liveness": _clip01(base["liveness"] + noise[4] * 0.03),
                "tempo": round(float(max(55, base["tempo"] + noise[5] * 5)), 2),
                "feature_source": "genre_proxy",
            }
        )
    return pd.DataFrame(rows)


def _normalize_chart_csv(path: Path, countries: pd.DataFrame) -> pd.DataFrame:
    frame = _read_csv_with_flexible_header(path)
    frame = frame.rename(columns={column: _normalize_column_name(column) for column in frame.columns})
    mapped = _map_columns(frame)

    country_code = _derive_country_code(path, countries)
    snapshot_date = _derive_snapshot_date(path)

    output = pd.DataFrame()
    if "rank" in mapped:
        output["rank"] = pd.to_numeric(mapped["rank"], errors="coerce").fillna(0).astype(int)
    else:
        output["rank"] = pd.Series(range(1, len(frame) + 1))
    output["track_name"] = _series_or_default(mapped, "track_name", "", len(frame)).astype(str).str.strip()
    output["artist_credit"] = _series_or_default(
        mapped, "artist_credit", "Unknown Artist", len(frame)
    ).astype(str)
    output["streams"] = (
        _series_or_default(mapped, "streams", 0, len(frame)).astype(str).str.replace(",", "", regex=False)
    )
    output["streams"] = pd.to_numeric(output["streams"], errors="coerce").fillna(0).astype(int)

    country_series = _series_or_default(mapped, "country_code", country_code, len(frame))
    output["country_code"] = country_series.astype(str).map(
        lambda value: _normalize_country_code(value, countries, country_code)
    )

    date_series = _series_or_default(mapped, "snapshot_date", snapshot_date, len(frame))
    output["snapshot_date"] = pd.to_datetime(date_series, errors="coerce").dt.date.astype(str)
    output.loc[output["snapshot_date"] == "NaT", "snapshot_date"] = snapshot_date

    output["genre"] = _series_or_default(mapped, "genre", "unknown", len(frame)).astype(str).str.strip()
    output["release_date"] = _series_or_default(
        mapped, "release_date", output["snapshot_date"], len(frame)
    )
    output["release_date"] = pd.to_datetime(output["release_date"], errors="coerce").dt.date.astype(str)
    output.loc[output["release_date"] == "NaT", "release_date"] = output["snapshot_date"]

    if "track_id" in mapped:
        track_id_source = mapped["track_id"].astype(str)
    elif "uri" in mapped:
        track_id_source = mapped["uri"].astype(str)
    else:
        track_id_source = pd.Series([""] * len(output))

    output["track_id"] = [
        _extract_track_id(value)
        or _fallback_track_id(track_name, artist_credit)
        for value, track_name, artist_credit in zip(
            track_id_source,
            output["track_name"],
            output["artist_credit"],
        )
    ]

    output = output[output["track_name"].str.len() > 0]
    return output[
        [
            "snapshot_date",
            "country_code",
            "rank",
            "track_id",
            "track_name",
            "artist_credit",
            "genre",
            "release_date",
            "streams",
        ]
    ]


def _read_csv_with_flexible_header(path: Path) -> pd.DataFrame:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = 0
    for index, line in enumerate(lines[:20]):
        normalized = _normalize_column_name(line)
        if ("rank" in normalized or "position" in normalized) and (
            "track" in normalized or "song" in normalized or "uri" in normalized
        ):
            header_index = index
            break
    return pd.read_csv(path, skiprows=header_index)


def _map_columns(frame: pd.DataFrame) -> dict[str, pd.Series]:
    mapped = {}
    for canonical_name, aliases in COLUMN_ALIASES.items():
        for column in frame.columns:
            if column in aliases:
                mapped[canonical_name] = frame[column]
                break
    return mapped


def _series_or_default(
    mapped: dict[str, pd.Series],
    key: str,
    default: Any,
    row_count: int,
) -> pd.Series:
    if key in mapped:
        return mapped[key]
    if isinstance(default, pd.Series):
        return default
    if isinstance(default, range | list | tuple | np.ndarray):
        return pd.Series(default)
    return pd.Series([default] * row_count)


def _derive_country_code(path: Path, countries: pd.DataFrame) -> str:
    filename = path.stem.upper()
    available_codes = set(countries["code"].astype(str).str.upper())
    for token in re.split(r"[^A-Z0-9]+", filename):
        if token in available_codes:
            return token
    raise ValueError(
        f"Could not derive country code from {path.name}. Include a country_code column "
        "or name files like regional-AR-daily-2026-01-01.csv."
    )


def _derive_snapshot_date(path: Path) -> str:
    match = DATE_RE.search(path.stem)
    if not match:
        raise ValueError(
            f"Could not derive chart date from {path.name}. Include a snapshot_date column "
            "or put YYYY-MM-DD in the filename."
        )
    return match.group(1)


def _normalize_country_code(value: str, countries: pd.DataFrame, fallback: str) -> str:
    clean = value.strip()
    if not clean:
        return fallback
    if len(clean) == 2:
        return clean.upper()

    country_lookup = {
        str(row.country_name).lower(): row.country_code
        for row in countries.rename(columns={"code": "country_code", "name": "country_name"}).itertuples()
    }
    return country_lookup.get(clean.lower(), fallback)


def _extract_track_id(value: str) -> str | None:
    if not value or value.lower() == "nan":
        return None
    match = SPOTIFY_ID_RE.search(value)
    return match.group(1) if match else None


def _fallback_track_id(track_name: str, artist_credit: str) -> str:
    digest = hashlib.sha1(f"{track_name}|{artist_credit}".encode("utf-8")).hexdigest()[:16]
    return f"local_{digest}"


def _search_missing_track_ids(
    missing_rows: pd.DataFrame,
    client: SpotifyAPIClient,
) -> dict[tuple[str, str, str], str]:
    discovered = {}
    unique_rows = missing_rows[["track_name", "artist_credit", "country_code"]].drop_duplicates()

    for row in unique_rows.itertuples(index=False):
        query = f'track:"{row.track_name}" artist:"{_primary_artist(row.artist_credit)}"'
        try:
            payload = client.search_track(query=query, market=row.country_code, limit=1)
        except SpotifyAPIError:
            continue

        items = payload.get("tracks", {}).get("items", [])
        if items:
            discovered[_track_lookup_key(row.track_name, row.artist_credit, row.country_code)] = items[0][
                "id"
            ]

    return discovered


def _fetch_track_metadata(client: SpotifyAPIClient, track_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not track_ids:
        return {}

    metadata: dict[str, dict[str, Any]] = {}
    try:
        tracks = client.get_tracks(track_ids)
    except SpotifyAPIError:
        return metadata

    artist_ids = sorted(
        {
            artist["id"]
            for track in tracks
            for artist in track.get("artists", [])
            if artist.get("id")
        }
    )
    artist_genres = _fetch_artist_genres(client, artist_ids)

    for track in tracks:
        artists = track.get("artists", [])
        genres = [
            genre
            for artist in artists
            for genre in artist_genres.get(artist.get("id", ""), [])
            if genre
        ]
        metadata[track["id"]] = {
            "track_name": track.get("name") or track["id"],
            "artist_credit": ", ".join(artist.get("name", "") for artist in artists if artist.get("name")),
            "genre": genres[0] if genres else "unknown",
            "release_date": track.get("album", {}).get("release_date") or "1900-01-01",
        }
    return metadata


def _fetch_artist_genres(client: SpotifyAPIClient, artist_ids: list[str]) -> dict[str, list[str]]:
    if not artist_ids:
        return {}
    try:
        artists = client.get_artists(artist_ids)
    except SpotifyAPIError:
        return {}
    return {artist["id"]: artist.get("genres", []) for artist in artists}


def _apply_metadata_to_chart(
    chart: pd.DataFrame,
    metadata: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    if not metadata:
        return chart

    output = chart.copy()
    for column in ["track_name", "artist_credit", "genre", "release_date"]:
        output[column] = output.apply(
            lambda row: metadata.get(row["track_id"], {}).get(column, row[column]),
            axis=1,
        )
    output["release_date"] = pd.to_datetime(output["release_date"], errors="coerce").dt.date.astype(str)
    output.loc[output["release_date"] == "NaT", "release_date"] = output["snapshot_date"]
    return output


def _fetch_audio_features(client: SpotifyAPIClient, track_ids: list[str]) -> pd.DataFrame:
    spotify_ids = [track_id for track_id in track_ids if _looks_like_spotify_track_id(track_id)]
    if not spotify_ids:
        return pd.DataFrame()

    try:
        features = client.get_many_audio_features(spotify_ids)
    except SpotifyAPIError:
        return pd.DataFrame()

    columns = ["track_id", "danceability", "energy", "valence", "acousticness", "liveness", "tempo"]
    rows = [
        {
            "track_id": row["id"],
            "danceability": row.get("danceability"),
            "energy": row.get("energy"),
            "valence": row.get("valence"),
            "acousticness": row.get("acousticness"),
            "liveness": row.get("liveness"),
            "tempo": row.get("tempo"),
            "feature_source": "spotify_audio_features",
        }
        for row in features
    ]
    return pd.DataFrame(rows, columns=columns + ["feature_source"])


def _track_lookup_key(track_name: str, artist_credit: str, country_code: str) -> tuple[str, str, str]:
    return (track_name.strip().lower(), artist_credit.strip().lower(), country_code.strip().upper())


def _primary_artist(artist_credit: str) -> str:
    return re.split(r"\s+feat\.\s+|,|&", artist_credit, maxsplit=1, flags=re.I)[0].strip()


def _looks_like_spotify_track_id(value: str) -> bool:
    return bool(SPOTIFY_ID_RE.fullmatch(str(value)))


def _normalize_column_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _map_genre_to_feature_key(genre: str) -> str:
    genre = genre.lower()
    if "reggaeton" in genre:
        return "reggaeton"
    if "afro" in genre:
        return "afrobeats"
    if "k-pop" in genre or "k pop" in genre:
        return "k_pop"
    if "hip hop" in genre or "rap" in genre:
        return "hip_hop"
    if "rock" in genre:
        return "rock"
    if "latin" in genre:
        return "latin_pop"
    if "indie" in genre:
        return "indie_pop"
    if "sad" in genre or "bedroom" in genre or "singer-songwriter" in genre:
        return "sad_pop"
    if "dance" in genre or "edm" in genre or "house" in genre:
        return "dance_pop"
    return "dance_pop"


def _stable_noise(seed_text: str, size: int) -> np.ndarray:
    seed = int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest()[:8], 16)
    return np.random.default_rng(seed).normal(0, 1, size=size)


def _clip01(value: float) -> float:
    return round(float(np.clip(value, 0.0, 1.0)), 4)


def _resolve_raw_dir(raw_dir: str) -> Path:
    path = Path(raw_dir)
    if path.is_absolute():
        return path
    if raw_dir.startswith("data/"):
        return PROJECT_ROOT / path
    return RAW_DIR / path


def load_spotify_api_dataset(settings: Settings | None = None) -> dict[str, pd.DataFrame]:
    settings = load_settings() if settings is None else settings
    countries = load_countries()

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        raise ValueError("Missing Spotify credentials. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env.")

    client = SpotifyAPIClient.from_settings(settings)
    client.authenticate()

    raw_rows = []
    # Use today's date as snapshot_date
    snapshot_date = datetime.date.today().isoformat()

    for row in countries.itertuples():
        country_code = str(row.code).upper()
        # Querying year:2025-2026 to get latest/popular tracks
        query = "year:2025-2026"
        try:
            payload = client.search_track(query=query, market=country_code, limit=50)
            items = payload.get("tracks", {}).get("items", [])
        except SpotifyAPIError as e:
            print(f"Failed to fetch tracks for country {country_code}: {e}")
            continue

        artist_ids = []
        for track in items:
            if track.get("artists"):
                artist_ids.append(track["artists"][0]["id"])

        artist_genres = _fetch_artist_genres(client, list(set(artist_ids)))

        for rank, track in enumerate(items, start=1):
            track_id = track.get("id")
            track_name = track.get("name")
            artists = track.get("artists", [])
            artist_credit = ", ".join(a.get("name", "") for a in artists if a.get("name"))

            genre = "unknown"
            if artists:
                first_artist_id = artists[0].get("id")
                genres = artist_genres.get(first_artist_id, [])
                if genres:
                    genre = genres[0]

            release_date = track.get("album", {}).get("release_date") or snapshot_date
            if len(release_date) == 4:
                release_date = f"{release_date}-01-01"
            elif len(release_date) == 7:
                release_date = f"{release_date}-01"

            # Simulate stream counts based on search rank
            streams = (50 - rank + 1) * 14000 + random.randint(1000, 5000)

            raw_rows.append({
                "snapshot_date": snapshot_date,
                "country_code": country_code,
                "rank": rank,
                "track_id": track_id,
                "track_name": track_name,
                "artist_credit": artist_credit,
                "genre": genre,
                "release_date": release_date,
                "streams": streams
            })

    if not raw_rows:
        raise RuntimeError("No chart data could be fetched from Spotify API.")

    raw_charts = pd.DataFrame(raw_rows)
    tracks = build_track_dimension_from_raw(raw_charts)

    if settings.spotify_audio_features_enabled:
        audio_features = _fetch_audio_features(client, tracks["track_id"].tolist())
        if audio_features.empty:
            audio_features = build_proxy_audio_features(tracks)
    else:
        audio_features = build_proxy_audio_features(tracks)

    return {
        "countries": countries,
        "tracks": tracks,
        "audio_features": audio_features,
        "raw_chart_entries": raw_charts,
    }

