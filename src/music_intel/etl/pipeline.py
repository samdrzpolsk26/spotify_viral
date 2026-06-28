from __future__ import annotations

import argparse

import pandas as pd

from music_intel.analysis.cultural_correlation import (
    build_country_acoustic_profile,
    calculate_climate_correlations,
    cluster_countries,
)
from music_intel.analysis.viral_detection import detect_viral_songs
from music_intel.etl.load import load_sqlite, write_processed_tables
from music_intel.etl.spotify_charts_source import load_spotify_csv_dataset, load_spotify_api_dataset
from music_intel.etl.transform import normalize_chart_data



def run_pipeline(source: str = "spotify_api", seed: int = 42, persist: bool = True) -> dict[str, pd.DataFrame]:
    if source == "spotify_api":
        raw = load_spotify_api_dataset()
    elif source == "spotify_csv":
        raw = load_spotify_csv_dataset()
    else:
        raise ValueError(f"Unsupported source: {source}")

    tables = normalize_chart_data(
        raw_charts=raw["raw_chart_entries"],
        countries=raw["countries"],
        audio_features=raw["audio_features"],
    )

    tables["fact_viral_signal"] = detect_viral_songs(
        fact_chart_position=tables["fact_chart_position"],
        dim_country=tables["dim_country"],
        dim_track=tables["dim_track"],
    )

    country_profile = build_country_acoustic_profile(
        fact_chart_position=tables["fact_chart_position"],
        fact_audio_features=tables["fact_audio_features"],
        dim_country=tables["dim_country"],
    )
    tables["mart_country_acoustic_profile"] = cluster_countries(country_profile)
    tables["mart_climate_correlations"] = calculate_climate_correlations(country_profile)

    if persist:
        write_processed_tables(tables)
        load_sqlite(tables)

    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Music Market Intelligence ETL.")
    parser.add_argument("--source", default="spotify_api", choices=["spotify_api", "spotify_csv"])
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args()

    tables = run_pipeline(source=args.source, seed=args.seed, persist=True)
    print("Pipeline completed.")
    print(f"Tables generated: {', '.join(sorted(tables))}")
    print(f"Chart rows: {len(tables['fact_chart_position']):,}")
    print(f"Viral signals: {len(tables['fact_viral_signal']):,}")


if __name__ == "__main__":
    main()
