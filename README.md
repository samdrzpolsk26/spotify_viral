# Music Market Intelligence

Proyecto profesional de analisis de datos para detectar tendencias musicales globales antes de que lleguen al ranking global principal.

## Objetivo

Construir una plataforma analitica que responda una pregunta de negocio real:

> Podemos detectar canciones con potencial global observando como entran en charts de varios paises, regiones y continentes?

El proyecto combina ingenieria de datos, SQL, analisis estadistico, deteccion de anomalias y visualizacion ejecutiva.

## Arquitectura

```text
Spotify Charts / fuentes musicales
        |
        v
ETL Python: extraccion, limpieza, normalizacion
        |
        v
PostgreSQL / SQLite demo
        |
        v
Analisis estadistico + deteccion viral
        |
        v
Dashboard Streamlit
```

## Capas del proyecto

### 1. Datos y ETL

- Extrae charts por pais y fecha.
- Normaliza canciones, artistas, colaboraciones, paises y posiciones.
- Carga tablas procesadas en CSV y una base SQLite local para demo.
- Incluye un cliente preparado para Spotify API, pero el proyecto corre sin credenciales usando datos sinteticos reproducibles.

### 2. Analisis avanzado

- Perfil acustico promedio por pais.
- Correlacion entre variables geograficas/climaticas y atributos musicales.
- Clustering de paises segun su gusto musical.
- Deteccion de senales virales: canciones que aparecen en al menos 3 paises de 3 continentes distintos dentro de una ventana de 72 horas.

### 3. Visualizacion

- Mapa mundial de huella acustica por mercado.
- Radar chart por pais.
- Ranking de canciones emergentes.
- Lineas temporales de expansion geografica.
- Vista de clusters de mercados.

## Inicio rapido

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\run_demo_pipeline.py
streamlit run dashboard\app.py
```

## Credenciales Spotify

No son necesarias para correr la demo.

Para conectar una app real, crea un archivo `.env` basado en `.env.example`:

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_MARKET_SOURCE=spotify_csv
RAW_SPOTIFY_CHARTS_DIR=data/raw/spotify_charts
SPOTIFY_AUDIO_FEATURES_ENABLED=false
```

Nota importante: desde el 27 de noviembre de 2024, Spotify restringe endpoints como `audio_features` para apps nuevas o en modo desarrollo. Por eso el proyecto esta disenado con un proveedor flexible de features:

- Spotify API, si tu app tiene acceso.
- Datasets alternativos.
- Features precalculadas.
- Extraccion propia de audio en una fase futura.

## Estructura

```text
config/                 Paises, regiones y variables geograficas
dashboard/              App Streamlit
data/raw/               Datos crudos
data/processed/         Tablas normalizadas generadas por el ETL
data/warehouse/         SQLite demo
scripts/                Entrypoints ejecutables
sql/                    Modelo relacional y vistas analiticas
src/music_intel/        Paquete Python del proyecto
tests/                  Pruebas unitarias
```

## Tablas principales

- `dim_country`
- `dim_artist`
- `dim_track`
- `bridge_track_artist`
- `fact_chart_position`
- `fact_audio_features`
- `fact_viral_signal`

## Siguiente paso recomendado

Cuando tengas credenciales o una fuente real de charts, implementa un extractor concreto y conserva el mismo contrato de salida: una tabla raw con `snapshot_date`, `country_code`, `rank`, `track_id`, `track_name`, `artist_credit`, `streams` y `genre`.

## Modo produccion con credenciales

Las credenciales de Spotify permiten autenticar contra el Web API y enriquecer tracks con metadata. El Top 50 por pais debe venir de Spotify Charts exportado a CSV o de una fuente equivalente, porque el Web API no expone un endpoint oficial de charts regionales.

### 1. Crea `.env`

```powershell
Copy-Item .env.example .env
```

Edita `.env` y agrega:

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_MARKET_SOURCE=spotify_csv
RAW_SPOTIFY_CHARTS_DIR=data/raw/spotify_charts
SPOTIFY_AUDIO_FEATURES_ENABLED=false
```

Usa `SPOTIFY_AUDIO_FEATURES_ENABLED=true` solo si tu app tiene acceso aprobado al endpoint restringido de audio features.

### 2. Agrega charts reales

Guarda CSVs en:

```text
data/raw/spotify_charts/
```

El parser acepta columnas comunes como `rank`, `uri`, `artist_names`, `track_name`, `streams`, o el contrato normalizado:

```text
snapshot_date,country_code,rank,track_id,track_name,artist_credit,streams,genre,release_date
```

Si el CSV no trae pais o fecha, ponlos en el nombre:

```text
regional-AR-daily-2026-01-01.csv
regional-DE-daily-2026-01-01.csv
```

### 3. Valida credenciales

```powershell
python scripts\validate_spotify_credentials.py
```

### 4. Ejecuta produccion

```powershell
python scripts\run_production_pipeline.py
streamlit run dashboard\app.py
```

El pipeline genera las mismas tablas finales que la demo, por lo que el dashboard y SQL no cambian.
