# Spotify Charts CSV input

Coloca aqui los exports reales de Spotify Charts o de una fuente equivalente.

Formatos aceptados:

- CSV con columnas propias de Spotify Charts, por ejemplo `rank`, `uri`, `artist_names`, `track_name`, `streams`.
- CSV con columnas normalizadas: `snapshot_date`, `country_code`, `rank`, `track_id`, `track_name`, `artist_credit`, `streams`, `genre`, `release_date`.

Si el archivo no trae `country_code` o `snapshot_date`, incluyelos en el nombre:

```text
regional-AR-daily-2026-01-01.csv
regional-DE-weekly-2026-01-08.csv
```

El pipeline extrae el ID desde valores como:

```text
spotify:track:TRACK_ID
https://open.spotify.com/track/TRACK_ID
```

Si no hay ID, usa `SPOTIFY_CLIENT_ID` y `SPOTIFY_CLIENT_SECRET` para buscar el track en Spotify.
