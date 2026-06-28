from music_intel.etl.pipeline import run_pipeline


def test_demo_pipeline_detects_cross_continent_signal() -> None:
    tables = run_pipeline(source="sample", persist=False)
    signals = tables["fact_viral_signal"]

    assert not signals.empty
    assert "Neon Tide" in set(signals["track_name"])
    assert signals["continents_count"].max() >= 3
