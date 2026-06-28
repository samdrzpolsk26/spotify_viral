from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    KMeans = None
    StandardScaler = None


AUDIO_FEATURES = ["danceability", "energy", "valence", "acousticness", "liveness", "tempo"]


def build_country_acoustic_profile(
    fact_chart_position: pd.DataFrame,
    fact_audio_features: pd.DataFrame,
    dim_country: pd.DataFrame,
) -> pd.DataFrame:
    if fact_chart_position.empty or fact_audio_features.empty:
        return pd.DataFrame()

    chart = fact_chart_position.merge(fact_audio_features, on="track_id", how="inner")
    chart["chart_weight"] = 1.0 / chart["rank_position"].astype(float)

    rows = []
    for country_code, group in chart.groupby("country_code"):
        weight = group["chart_weight"]
        total_weight = float(weight.sum())
        row = {"country_code": country_code, "track_observations": int(len(group))}
        for feature in AUDIO_FEATURES:
            row[feature] = float((group[feature] * weight).sum() / total_weight)
        rows.append(row)

    profile = pd.DataFrame(rows)
    return profile.merge(dim_country, on="country_code", how="left")


def calculate_climate_correlations(country_profile: pd.DataFrame) -> pd.DataFrame:
    if country_profile.empty:
        return pd.DataFrame(columns=["climate_variable", "audio_feature", "correlation"])

    rows = []
    climate_variables = ["avg_annual_temp_c", "abs_latitude"]
    for climate_variable in climate_variables:
        for audio_feature in AUDIO_FEATURES:
            valid = country_profile[[climate_variable, audio_feature]].dropna()
            if len(valid) < 3 or valid[climate_variable].nunique() < 2:
                correlation = np.nan
            else:
                correlation = float(valid[climate_variable].corr(valid[audio_feature]))
            rows.append(
                {
                    "climate_variable": climate_variable,
                    "audio_feature": audio_feature,
                    "correlation": correlation,
                }
            )

    return pd.DataFrame(rows).sort_values("correlation", ascending=False, na_position="last")


def cluster_countries(country_profile: pd.DataFrame, n_clusters: int = 4) -> pd.DataFrame:
    if country_profile.empty:
        return country_profile

    output = country_profile.copy()
    feature_matrix = output[AUDIO_FEATURES].dropna()
    if len(feature_matrix) < n_clusters:
        output["cluster"] = 0
        return output

    if KMeans is None or StandardScaler is None:
        output.loc[feature_matrix.index, "cluster"] = _fallback_cluster_labels(
            feature_matrix,
            n_clusters=n_clusters,
        )
        output["cluster"] = output["cluster"].fillna(-1).astype(int)
        return output

    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_matrix)
    model = KMeans(n_clusters=n_clusters, n_init=20, random_state=42)
    labels = model.fit_predict(scaled)
    output.loc[feature_matrix.index, "cluster"] = labels
    output["cluster"] = output["cluster"].fillna(-1).astype(int)
    return output


def _fallback_cluster_labels(feature_matrix: pd.DataFrame, n_clusters: int) -> pd.Series:
    standardized = (feature_matrix - feature_matrix.mean()) / feature_matrix.std(ddof=0)
    score = (
        standardized["valence"].fillna(0)
        + standardized["energy"].fillna(0)
        + standardized["danceability"].fillna(0)
        - standardized["acousticness"].fillna(0)
    )
    labels = pd.qcut(score.rank(method="first"), q=n_clusters, labels=False, duplicates="drop")
    return labels.astype(int)
