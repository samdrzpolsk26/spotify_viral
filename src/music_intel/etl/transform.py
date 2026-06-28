from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


RAW_CHART_COLUMNS = {
    "snapshot_date",
    "country_code",
    "rank",
    "track_id",
    "track_name",
    "artist_credit",
    "genre",
    "release_date",
    "streams",
}


def normalize_chart_data(
    raw_charts: pd.DataFrame,
    countries: pd.DataFrame,
    audio_features: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    validate_raw_chart_schema(raw_charts)

    chart = raw_charts.copy()
    chart["snapshot_date"] = pd.to_datetime(chart["snapshot_date"]).dt.date.astype(str)
    chart["release_date"] = pd.to_datetime(chart["release_date"]).dt.date.astype(str)
    chart["rank_position"] = chart["rank"].astype(int)
    chart["streams"] = chart["streams"].astype(int)

    dim_country = countries.rename(columns={"code": "country_code", "name": "country_name"})[
        [
            "country_code",
            "country_name",
            "region",
            "continent",
            "avg_annual_temp_c",
            "latitude",
            "longitude",
            "abs_latitude",
        ]
    ].drop_duplicates()

    dim_track = (
        chart[["track_id", "track_name", "genre", "release_date"]]
        .drop_duplicates("track_id")
        .sort_values("track_id")
        .reset_index(drop=True)
    )

    artist_rows = []
    bridge_rows = []
    artist_seen: set[str] = set()

    for track in chart[["track_id", "artist_credit"]].drop_duplicates("track_id").itertuples(
        index=False
    ):
        main_artists, featured_artists = split_artist_credit(track.artist_credit)
        for order, artist_name in enumerate(main_artists, start=1):
            artist_id = make_artist_id(artist_name)
            if artist_id not in artist_seen:
                artist_rows.append({"artist_id": artist_id, "artist_name": artist_name})
                artist_seen.add(artist_id)
            bridge_rows.append(
                {
                    "track_id": track.track_id,
                    "artist_id": artist_id,
                    "artist_role": "main",
                    "artist_order": order,
                }
            )

        for order, artist_name in enumerate(featured_artists, start=1):
            artist_id = make_artist_id(artist_name)
            if artist_id not in artist_seen:
                artist_rows.append({"artist_id": artist_id, "artist_name": artist_name})
                artist_seen.add(artist_id)
            bridge_rows.append(
                {
                    "track_id": track.track_id,
                    "artist_id": artist_id,
                    "artist_role": "featured",
                    "artist_order": order,
                }
            )

    dim_artist = pd.DataFrame(artist_rows).sort_values("artist_name").reset_index(drop=True)
    bridge_track_artist = (
        pd.DataFrame(bridge_rows)
        .drop_duplicates(["track_id", "artist_id", "artist_role"])
        .sort_values(["track_id", "artist_role", "artist_order"])
        .reset_index(drop=True)
    )

    fact_chart_position = chart[
        ["snapshot_date", "country_code", "track_id", "rank_position", "streams"]
    ].sort_values(["snapshot_date", "country_code", "rank_position"])

    if audio_features is None:
        fact_audio_features = pd.DataFrame(
            columns=[
                "track_id",
                "danceability",
                "energy",
                "valence",
                "acousticness",
                "liveness",
                "tempo",
            ]
        )
    else:
        fact_audio_features = audio_features.drop_duplicates("track_id").sort_values("track_id")

    return {
        "dim_country": dim_country.reset_index(drop=True),
        "dim_track": dim_track.reset_index(drop=True),
        "dim_artist": dim_artist.reset_index(drop=True),
        "bridge_track_artist": bridge_track_artist.reset_index(drop=True),
        "fact_chart_position": fact_chart_position.reset_index(drop=True),
        "fact_audio_features": fact_audio_features.reset_index(drop=True),
    }


def validate_raw_chart_schema(raw_charts: pd.DataFrame) -> None:
    missing = RAW_CHART_COLUMNS.difference(raw_charts.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"raw chart data is missing required columns: {missing_list}")


def split_artist_credit(artist_credit: str) -> tuple[list[str], list[str]]:
    credit = re.sub(r"\s+(ft\.|feat\.|featuring)\s+", " feat. ", artist_credit, flags=re.I)
    parts = credit.split(" feat. ", maxsplit=1)
    main_artists = _split_artist_list(parts[0])
    featured_artists = _split_artist_list(parts[1]) if len(parts) == 2 else []
    return main_artists, featured_artists


def make_artist_id(artist_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", artist_name.lower()).strip("_")
    return f"artist_{slug}"


def _split_artist_list(value: str) -> list[str]:
    return [artist.strip() for artist in re.split(r"\s*&\s*|\s*,\s*", value) if artist.strip()]


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    output = df.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[list(columns)]
