from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from music_intel.etl.pipeline import run_pipeline  # noqa: E402
from music_intel.paths import PROCESSED_DIR  # noqa: E402


TABLE_NAMES = [
    "dim_country",
    "dim_track",
    "dim_artist",
    "bridge_track_artist",
    "fact_chart_position",
    "fact_audio_features",
    "fact_viral_signal",
    "mart_country_acoustic_profile",
    "mart_climate_correlations",
]

AUDIO_FEATURES = ["danceability", "energy", "valence", "acousticness", "liveness", "tempo"]
RADAR_FEATURES = ["danceability", "energy", "valence", "acousticness", "liveness"]


st.set_page_config(page_title="Music Market Intelligence", layout="wide")


@st.cache_data(show_spinner=False)
def load_tables() -> dict[str, pd.DataFrame]:
    expected_files = [PROCESSED_DIR / f"{name}.csv" for name in TABLE_NAMES]
    if not all(path.exists() for path in expected_files):
        run_pipeline(source="sample", persist=True)

    tables = {name: pd.read_csv(PROCESSED_DIR / f"{name}.csv") for name in TABLE_NAMES}
    tables["fact_chart_position"]["snapshot_date"] = pd.to_datetime(
        tables["fact_chart_position"]["snapshot_date"]
    )
    return tables


tables = load_tables()
countries = tables["dim_country"]
tracks = tables["dim_track"]
chart = tables["fact_chart_position"]
signals = tables["fact_viral_signal"]
profile = tables["mart_country_acoustic_profile"]
correlations = tables["mart_climate_correlations"]

st.title("Music Market Intelligence")

with st.sidebar:
    regions = sorted(profile["region"].dropna().unique())
    selected_regions = st.multiselect("Region", regions, default=regions)
    filtered_profile = profile[profile["region"].isin(selected_regions)]
    country_names = sorted(filtered_profile["country_name"].dropna().unique())
    selected_country = st.selectbox("Market", country_names, index=0 if country_names else None)
    map_metric = st.selectbox("Map metric", AUDIO_FEATURES, index=2)
    min_date = chart["snapshot_date"].min().date()
    max_date = chart["snapshot_date"].max().date()
    selected_dates = st.date_input("Date range", value=(min_date, max_date))

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_date, max_date

country_codes = filtered_profile["country_code"].tolist()
filtered_chart = chart[
    (chart["country_code"].isin(country_codes))
    & (chart["snapshot_date"].dt.date >= start_date)
    & (chart["snapshot_date"].dt.date <= end_date)
]

metric_cols = st.columns(4)
metric_cols[0].metric("Markets", f"{filtered_profile['country_code'].nunique():,}")
metric_cols[1].metric("Tracks", f"{filtered_chart['track_id'].nunique():,}")
metric_cols[2].metric("Chart observations", f"{len(filtered_chart):,}")
metric_cols[3].metric("Viral signals", f"{len(signals):,}")

map_col, radar_col = st.columns([1.45, 1])

with map_col:
    st.subheader("Acoustic Market Map")
    fig_map = px.scatter_geo(
        filtered_profile,
        lat="latitude",
        lon="longitude",
        color=map_metric,
        size="track_observations",
        hover_name="country_name",
        hover_data={
            "region": True,
            "continent": True,
            "latitude": False,
            "longitude": False,
            "track_observations": ":,",
            map_metric: ":.3f",
        },
        projection="natural earth",
        color_continuous_scale="Viridis",
    )
    fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=440)
    st.plotly_chart(fig_map, use_container_width=True)

with radar_col:
    st.subheader("Country Fingerprint")
    selected_row = profile[profile["country_name"] == selected_country]
    if not selected_row.empty:
        values = [float(selected_row.iloc[0][feature]) for feature in RADAR_FEATURES]
        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=values + values[:1],
                theta=RADAR_FEATURES + RADAR_FEATURES[:1],
                fill="toself",
                name=selected_country,
            )
        )
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False,
            margin=dict(l=24, r=24, t=16, b=16),
            height=440,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

signal_col, timeline_col = st.columns([1, 1.25])

with signal_col:
    st.subheader("Breakout Signals")
    signal_view = signals[
        [
            "signal_start",
            "track_name",
            "countries_count",
            "continents_count",
            "best_rank",
            "total_streams",
            "evidence_countries",
        ]
    ].sort_values(["continents_count", "countries_count", "total_streams"], ascending=False)
    st.dataframe(signal_view, use_container_width=True, hide_index=True)

with timeline_col:
    st.subheader("Geographic Spread")
    if signals.empty:
        st.write("No signals detected.")
    else:
        signal_tracks = signals["track_name"].tolist()
        selected_track_name = st.selectbox("Track", signal_tracks)
        selected_track_id = tracks.loc[
            tracks["track_name"] == selected_track_name,
            "track_id",
        ].iloc[0]
        trend = filtered_chart[filtered_chart["track_id"] == selected_track_id].merge(
            countries[["country_code", "country_name", "continent"]],
            on="country_code",
            how="left",
        )
        fig_trend = px.line(
            trend,
            x="snapshot_date",
            y="rank_position",
            color="country_name",
            markers=True,
            hover_data={"continent": True, "streams": ":,"},
        )
        fig_trend.update_yaxes(autorange="reversed", title="Chart rank")
        fig_trend.update_xaxes(title=None)
        fig_trend.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420)
        st.plotly_chart(fig_trend, use_container_width=True)

cluster_col, corr_col = st.columns([1.15, 1])

with cluster_col:
    st.subheader("Market Clusters")
    fig_cluster = px.scatter(
        filtered_profile,
        x="valence",
        y="energy",
        color="cluster",
        size="danceability",
        hover_name="country_name",
        hover_data={"region": True, "avg_annual_temp_c": ":.1f"},
        color_continuous_scale="Turbo",
    )
    fig_cluster.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420)
    st.plotly_chart(fig_cluster, use_container_width=True)

with corr_col:
    st.subheader("Climate Correlations")
    corr_view = correlations.copy()
    corr_view["correlation"] = corr_view["correlation"].round(3)
    st.dataframe(corr_view, use_container_width=True, hide_index=True)
