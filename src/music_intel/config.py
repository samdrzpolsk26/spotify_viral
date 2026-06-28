from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - depends on local environment

    def load_dotenv() -> bool:
        return False

from music_intel.paths import CONFIG_DIR


@dataclass(frozen=True)
class Settings:
    spotify_client_id: str | None
    spotify_client_secret: str | None
    spotify_market_source: str
    database_url: str
    raw_spotify_charts_dir: str
    spotify_audio_features_enabled: bool


def load_settings() -> Settings:
    if not load_dotenv():
        _load_dotenv_fallback(Path(".env"))

    return Settings(
        spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID") or None,
        spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET") or None,
        spotify_market_source=os.getenv("SPOTIFY_MARKET_SOURCE", "sample"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/warehouse/music_market.db"),
        raw_spotify_charts_dir=os.getenv("RAW_SPOTIFY_CHARTS_DIR", "data/raw/spotify_charts"),
        spotify_audio_features_enabled=_parse_bool(
            os.getenv("SPOTIFY_AUDIO_FEATURES_ENABLED", "false")
        ),
    )


def load_countries() -> pd.DataFrame:
    path = CONFIG_DIR / "countries.yml"
    if yaml is not None:
        with open(path, "r", encoding="utf-8") as file:
            payload = yaml.safe_load(file)
    else:
        payload = _load_simple_country_yaml(path)

    countries = pd.DataFrame(payload["countries"])
    countries["abs_latitude"] = countries["latitude"].abs()
    return countries


def _load_simple_country_yaml(path) -> dict[str, list[dict[str, object]]]:
    countries: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line == "countries:":
            continue

        if line.startswith("- "):
            if current is not None:
                countries.append(current)
            current = {}
            remainder = line[2:].strip()
            if remainder:
                key, value = remainder.split(":", maxsplit=1)
                current[key.strip()] = _parse_scalar(value)
            continue

        if current is not None and ":" in line:
            key, value = line.split(":", maxsplit=1)
            current[key.strip()] = _parse_scalar(value)

    if current is not None:
        countries.append(current)

    return {"countries": countries}


def _parse_scalar(value: str) -> object:
    value = value.strip().strip('"').strip("'")
    if not value:
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _load_dotenv_fallback(path: Path) -> bool:
    if not path.exists():
        return False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

    return True
