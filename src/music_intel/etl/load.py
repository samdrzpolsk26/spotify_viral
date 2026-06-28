from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from music_intel.paths import PROCESSED_DIR, WAREHOUSE_DIR


def write_processed_tables(
    tables: dict[str, pd.DataFrame],
    output_dir: Path = PROCESSED_DIR,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths = []

    for table_name, dataframe in tables.items():
        output_path = output_dir / f"{table_name}.csv"
        dataframe.to_csv(output_path, index=False)
        written_paths.append(output_path)

    return written_paths


def load_sqlite(
    tables: dict[str, pd.DataFrame],
    db_path: Path = WAREHOUSE_DIR / "music_market.db",
) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        for table_name, dataframe in tables.items():
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False)

    return db_path
