CREATE OR REPLACE VIEW mart_country_acoustic_profile AS
SELECT
    c.country_code,
    c.country_name,
    c.region,
    c.continent,
    c.avg_annual_temp_c,
    c.latitude,
    c.longitude,
    c.abs_latitude,
    COUNT(*) AS track_observations,
    SUM(af.danceability / cp.rank_position) / SUM(1.0 / cp.rank_position) AS danceability,
    SUM(af.energy / cp.rank_position) / SUM(1.0 / cp.rank_position) AS energy,
    SUM(af.valence / cp.rank_position) / SUM(1.0 / cp.rank_position) AS valence,
    SUM(af.acousticness / cp.rank_position) / SUM(1.0 / cp.rank_position) AS acousticness,
    SUM(af.liveness / cp.rank_position) / SUM(1.0 / cp.rank_position) AS liveness,
    SUM(af.tempo / cp.rank_position) / SUM(1.0 / cp.rank_position) AS tempo
FROM fact_chart_position cp
JOIN dim_country c ON c.country_code = cp.country_code
JOIN fact_audio_features af ON af.track_id = cp.track_id
GROUP BY
    c.country_code,
    c.country_name,
    c.region,
    c.continent,
    c.avg_annual_temp_c,
    c.latitude,
    c.longitude,
    c.abs_latitude;

CREATE OR REPLACE VIEW mart_track_momentum AS
WITH daily_track AS (
    SELECT
        cp.snapshot_date,
        cp.track_id,
        t.track_name,
        COUNT(DISTINCT cp.country_code) AS countries_on_chart,
        COUNT(DISTINCT c.continent) AS continents_on_chart,
        MIN(cp.rank_position) AS best_rank,
        SUM(cp.streams) AS streams
    FROM fact_chart_position cp
    JOIN dim_track t ON t.track_id = cp.track_id
    JOIN dim_country c ON c.country_code = cp.country_code
    WHERE cp.rank_position <= 50
    GROUP BY cp.snapshot_date, cp.track_id, t.track_name
)
SELECT
    snapshot_date,
    track_id,
    track_name,
    countries_on_chart,
    continents_on_chart,
    best_rank,
    streams,
    countries_on_chart - LAG(countries_on_chart) OVER (
        PARTITION BY track_id ORDER BY snapshot_date
    ) AS country_delta
FROM daily_track;

CREATE OR REPLACE VIEW mart_viral_candidates AS
SELECT
    track_id,
    track_name,
    signal_start,
    signal_end,
    countries_count,
    continents_count,
    best_rank,
    total_streams,
    evidence_countries
FROM fact_viral_signal
ORDER BY signal_start DESC, continents_count DESC, countries_count DESC;
