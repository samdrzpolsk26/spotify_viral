from __future__ import annotations

import pandas as pd


VIRAL_SIGNAL_COLUMNS = [
    "track_id",
    "track_name",
    "signal_start",
    "signal_end",
    "countries_count",
    "continents_count",
    "evidence_countries",
    "best_rank",
    "total_streams",
    "signal_type",
]


def detect_viral_songs(
    fact_chart_position: pd.DataFrame,
    dim_country: pd.DataFrame,
    dim_track: pd.DataFrame,
    window_hours: int = 72,
    min_countries: int = 3,
    min_continents: int = 3,
    max_rank: int = 50,
) -> pd.DataFrame:
    if fact_chart_position.empty:
        return pd.DataFrame(columns=VIRAL_SIGNAL_COLUMNS)

    chart = fact_chart_position.copy()
    chart["snapshot_date"] = pd.to_datetime(chart["snapshot_date"])
    chart = chart[chart["rank_position"] <= max_rank]
    chart = chart.merge(
        dim_country[["country_code", "country_name", "continent"]],
        on="country_code",
        how="left",
    )

    first_entries = (
        chart.sort_values("snapshot_date")
        .groupby(["track_id", "country_code", "country_name", "continent"], as_index=False)
        .agg(
            first_seen=("snapshot_date", "min"),
            best_rank=("rank_position", "min"),
            total_streams=("streams", "sum"),
        )
    )

    signals = []
    window = pd.Timedelta(hours=window_hours)

    for track_id, track_entries in first_entries.groupby("track_id"):
        track_entries = track_entries.sort_values("first_seen").reset_index(drop=True)

        for idx, entry in track_entries.iterrows():
            start = entry["first_seen"]
            in_window = track_entries[
                (track_entries["first_seen"] >= start)
                & (track_entries["first_seen"] <= start + window)
            ]
            countries_count = int(in_window["country_code"].nunique())
            continents_count = int(in_window["continent"].nunique())

            if countries_count >= min_countries and continents_count >= min_continents:
                track_name = _lookup_track_name(dim_track, track_id)
                signals.append(
                    {
                        "track_id": track_id,
                        "track_name": track_name,
                        "signal_start": start.date().isoformat(),
                        "signal_end": in_window["first_seen"].max().date().isoformat(),
                        "countries_count": countries_count,
                        "continents_count": continents_count,
                        "evidence_countries": ", ".join(sorted(in_window["country_name"].dropna())),
                        "best_rank": int(in_window["best_rank"].min()),
                        "total_streams": int(in_window["total_streams"].sum()),
                        "signal_type": "cross_continent_breakout",
                    }
                )
                break

    if not signals:
        return pd.DataFrame(columns=VIRAL_SIGNAL_COLUMNS)

    return (
        pd.DataFrame(signals)
        .sort_values(["signal_start", "continents_count", "countries_count"], ascending=[True, False, False])
        .reset_index(drop=True)
    )


def _lookup_track_name(dim_track: pd.DataFrame, track_id: str) -> str:
    match = dim_track.loc[dim_track["track_id"] == track_id, "track_name"]
    return str(match.iloc[0]) if not match.empty else track_id
