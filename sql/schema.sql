CREATE TABLE dim_country (
    country_code TEXT PRIMARY KEY,
    country_name TEXT NOT NULL,
    region TEXT NOT NULL,
    continent TEXT NOT NULL,
    avg_annual_temp_c NUMERIC(5, 2),
    latitude NUMERIC(8, 4),
    longitude NUMERIC(8, 4),
    abs_latitude NUMERIC(8, 4)
);

CREATE TABLE dim_artist (
    artist_id TEXT PRIMARY KEY,
    artist_name TEXT NOT NULL
);

CREATE TABLE dim_track (
    track_id TEXT PRIMARY KEY,
    track_name TEXT NOT NULL,
    genre TEXT,
    release_date DATE
);

CREATE TABLE bridge_track_artist (
    track_id TEXT NOT NULL REFERENCES dim_track(track_id),
    artist_id TEXT NOT NULL REFERENCES dim_artist(artist_id),
    artist_role TEXT NOT NULL CHECK (artist_role IN ('main', 'featured')),
    artist_order INTEGER NOT NULL,
    PRIMARY KEY (track_id, artist_id, artist_role)
);

CREATE TABLE fact_audio_features (
    track_id TEXT PRIMARY KEY REFERENCES dim_track(track_id),
    danceability NUMERIC(6, 4),
    energy NUMERIC(6, 4),
    valence NUMERIC(6, 4),
    acousticness NUMERIC(6, 4),
    liveness NUMERIC(6, 4),
    tempo NUMERIC(7, 2)
);

CREATE TABLE fact_chart_position (
    snapshot_date DATE NOT NULL,
    country_code TEXT NOT NULL REFERENCES dim_country(country_code),
    track_id TEXT NOT NULL REFERENCES dim_track(track_id),
    rank_position INTEGER NOT NULL CHECK (rank_position >= 1),
    streams INTEGER,
    PRIMARY KEY (snapshot_date, country_code, track_id)
);

CREATE TABLE fact_viral_signal (
    track_id TEXT NOT NULL REFERENCES dim_track(track_id),
    track_name TEXT NOT NULL,
    signal_start DATE NOT NULL,
    signal_end DATE NOT NULL,
    countries_count INTEGER NOT NULL,
    continents_count INTEGER NOT NULL,
    evidence_countries TEXT NOT NULL,
    best_rank INTEGER,
    total_streams INTEGER,
    signal_type TEXT NOT NULL,
    PRIMARY KEY (track_id, signal_start, signal_type)
);

CREATE INDEX idx_chart_country_date ON fact_chart_position(country_code, snapshot_date);
CREATE INDEX idx_chart_track_date ON fact_chart_position(track_id, snapshot_date);
CREATE INDEX idx_chart_rank ON fact_chart_position(rank_position);
CREATE INDEX idx_viral_signal_start ON fact_viral_signal(signal_start);
