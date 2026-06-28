from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from music_intel.config import load_countries


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

REGION_GENRE_BONUS = {
    "Latin America": {"reggaeton": 2.4, "latin_pop": 2.0, "afrobeats": 0.7},
    "North America": {"hip_hop": 1.8, "dance_pop": 1.2, "indie_pop": 0.9},
    "Southern Europe": {"latin_pop": 1.2, "dance_pop": 1.0, "reggaeton": 0.8},
    "Western Europe": {"dance_pop": 1.4, "indie_pop": 1.0, "sad_pop": 0.8},
    "Central Europe": {"dance_pop": 1.1, "rock": 1.0, "sad_pop": 1.0},
    "Nordic Europe": {"sad_pop": 1.8, "indie_pop": 1.3, "dance_pop": 0.8},
    "East Asia": {"k_pop": 2.2, "dance_pop": 1.2, "sad_pop": 0.7},
    "South Asia": {"dance_pop": 1.1, "hip_hop": 0.8, "latin_pop": 0.6},
    "Southeast Asia": {"dance_pop": 1.5, "k_pop": 1.2, "sad_pop": 0.6},
    "West Africa": {"afrobeats": 2.5, "hip_hop": 1.1, "dance_pop": 0.7},
    "Southern Africa": {"afrobeats": 1.4, "dance_pop": 1.0, "hip_hop": 0.8},
    "Oceania": {"dance_pop": 1.2, "indie_pop": 1.1, "hip_hop": 0.8},
}

ARTISTS = [
    "Luna Vale",
    "Kai North",
    "Mar Azul",
    "Rio Nexo",
    "The Glass Hours",
    "Sora Unit",
    "Nova Barrio",
    "Mika Sol",
    "Atlas Crew",
    "Nia Kross",
    "Oro Club",
    "Vera Static",
    "Seoul Drift",
    "Tari Wave",
    "Polar Room",
    "Melo Sur",
    "Rina Coast",
    "Cairo Line",
    "Echo Plaza",
    "Indigo Frame",
]

ADJECTIVES = [
    "Neon",
    "Velvet",
    "Midnight",
    "Golden",
    "Electric",
    "Solar",
    "Crystal",
    "Silent",
    "Urban",
    "Parallel",
    "Magnetic",
    "Ocean",
    "Northern",
    "Plastic",
    "Burning",
]

NOUNS = [
    "Tide",
    "Signal",
    "Ritual",
    "Summer",
    "Voltage",
    "Mirage",
    "Pulse",
    "Window",
    "Gravity",
    "Garden",
    "Letters",
    "Radio",
    "District",
    "Echo",
    "Bloom",
]


def build_track_catalog(track_count: int = 80, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    genres = list(GENRE_FEATURE_BASE)

    rows: list[dict[str, Any]] = [
        {
            "track_id": "trk_000",
            "track_name": "Neon Tide",
            "artist_credit": "Luna Vale feat. Kai North",
            "genre": "dance_pop",
            "release_date": "2026-01-04",
            "home_region": "Global",
            "base_popularity": 1.2,
        }
    ]

    for idx in range(1, track_count):
        adjective = ADJECTIVES[idx % len(ADJECTIVES)]
        noun = NOUNS[(idx * 3) % len(NOUNS)]
        track_name = f"{adjective} {noun}"
        main_artist = ARTISTS[idx % len(ARTISTS)]
        genre = genres[idx % len(genres)]
        release = date(2025, 10, 1) + timedelta(days=int(rng.integers(0, 120)))

        if rng.random() < 0.28:
            featured_artist = ARTISTS[(idx * 5 + 1) % len(ARTISTS)]
            artist_credit = f"{main_artist} feat. {featured_artist}"
        else:
            artist_credit = main_artist

        rows.append(
            {
                "track_id": f"trk_{idx:03}",
                "track_name": track_name,
                "artist_credit": artist_credit,
                "genre": genre,
                "release_date": release.isoformat(),
                "home_region": _home_region_for_genre(genre),
                "base_popularity": float(rng.normal(0, 0.9)),
            }
        )

    return pd.DataFrame(rows)


def build_audio_features(tracks: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 7)
    rows: list[dict[str, Any]] = []

    for row in tracks.itertuples(index=False):
        base = GENRE_FEATURE_BASE[row.genre]
        features = {
            "track_id": row.track_id,
            "danceability": _clip01(base["danceability"] + rng.normal(0, 0.07)),
            "energy": _clip01(base["energy"] + rng.normal(0, 0.08)),
            "valence": _clip01(base["valence"] + rng.normal(0, 0.10)),
            "acousticness": _clip01(base["acousticness"] + rng.normal(0, 0.08)),
            "liveness": _clip01(base["liveness"] + rng.normal(0, 0.04)),
            "tempo": round(float(max(55, base["tempo"] + rng.normal(0, 8))), 2),
        }
        rows.append(features)

    return pd.DataFrame(rows)


def build_chart_history(
    countries: pd.DataFrame | None = None,
    tracks: pd.DataFrame | None = None,
    audio_features: pd.DataFrame | None = None,
    start_date: str = "2026-01-01",
    periods: int = 35,
    chart_size: int = 50,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 13)
    countries = load_countries() if countries is None else countries.copy()
    tracks = build_track_catalog(seed=seed) if tracks is None else tracks.copy()
    audio_features = (
        build_audio_features(tracks, seed=seed) if audio_features is None else audio_features.copy()
    )
    feature_lookup = audio_features.set_index("track_id").to_dict(orient="index")

    start = datetime.fromisoformat(start_date).date()
    rows: list[dict[str, Any]] = []
    global_noise = rng.normal(0, 0.35, size=(periods, len(tracks)))
    catalog = tracks.reset_index(drop=True)

    for day_idx in range(periods):
        snapshot = start + timedelta(days=day_idx)

        for country in countries.itertuples(index=False):
            scores = []

            for track_idx, track in enumerate(catalog.itertuples(index=False)):
                features = feature_lookup[track.track_id]
                climate_fit = _climate_music_fit(country.avg_annual_temp_c, features)
                regional_bonus = REGION_GENRE_BONUS.get(country.region, {}).get(track.genre, 0.0)
                freshness = max(0.0, 1.0 - day_idx / 50)
                score = (
                    track.base_popularity
                    + regional_bonus
                    + climate_fit
                    + freshness * 0.35
                    + global_noise[day_idx, track_idx]
                )
                score += _viral_boost(track.track_id, country.code, day_idx)
                scores.append(score)

            ranking = np.argsort(scores)[::-1][:chart_size]
            top_scores = np.array(scores)[ranking]
            min_score = float(top_scores.min())

            for rank_idx, track_idx in enumerate(ranking, start=1):
                track = catalog.iloc[int(track_idx)]
                score = float(scores[int(track_idx)] - min_score + 0.5)
                streams = int(max(25_000, 120_000 + score * 180_000 + rng.normal(0, 12_000)))
                rows.append(
                    {
                        "snapshot_date": snapshot.isoformat(),
                        "country_code": country.code,
                        "rank": rank_idx,
                        "track_id": track["track_id"],
                        "track_name": track["track_name"],
                        "artist_credit": track["artist_credit"],
                        "genre": track["genre"],
                        "release_date": track["release_date"],
                        "streams": streams,
                    }
                )

    return pd.DataFrame(rows)


def build_sample_dataset(seed: int = 42) -> dict[str, pd.DataFrame]:
    countries = load_countries()
    tracks = build_track_catalog(seed=seed)
    audio_features = build_audio_features(tracks, seed=seed)
    charts = build_chart_history(
        countries=countries,
        tracks=tracks,
        audio_features=audio_features,
        seed=seed,
    )
    return {
        "countries": countries,
        "tracks": tracks,
        "audio_features": audio_features,
        "raw_chart_entries": charts,
    }


def _clip01(value: float) -> float:
    return round(float(np.clip(value, 0.0, 1.0)), 4)


def _home_region_for_genre(genre: str) -> str:
    mapping = {
        "reggaeton": "Latin America",
        "latin_pop": "Latin America",
        "afrobeats": "West Africa",
        "k_pop": "East Asia",
        "sad_pop": "Nordic Europe",
        "dance_pop": "Global",
        "hip_hop": "North America",
        "indie_pop": "Western Europe",
        "rock": "Central Europe",
    }
    return mapping.get(genre, "Global")


def _climate_music_fit(avg_temp_c: float, features: dict[str, float]) -> float:
    warm_market = (avg_temp_c - 10.0) / 20.0
    cold_market = (10.0 - avg_temp_c) / 20.0
    return (
        warm_market * (features["danceability"] * 0.8 + features["valence"] * 0.7)
        + cold_market * ((1.0 - features["valence"]) * 0.8 + features["acousticness"] * 0.4)
    )


def _viral_boost(track_id: str, country_code: str, day_idx: int) -> float:
    if track_id != "trk_000":
        return 0.0

    launch_schedule = {
        "BR": 3,
        "DE": 4,
        "JP": 4,
        "NG": 5,
        "AU": 5,
        "US": 7,
        "GB": 7,
        "MX": 8,
        "KR": 8,
        "ES": 9,
    }
    launch_day = launch_schedule.get(country_code)
    if launch_day is None or day_idx < launch_day:
        return 0.0

    days_since_launch = day_idx - launch_day
    return max(0.0, 5.5 - days_since_launch * 0.08)
