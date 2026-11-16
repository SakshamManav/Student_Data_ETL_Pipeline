"""Load module: persist cleaned data to CSV and SQLite with verification."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def load_data(
    df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    clean_csv_path: Path,
    rejected_csv_path: Path,
    db_path: Path,
    table_name: str,
) -> Tuple[int, int]:
    """Save cleaned data to CSV and SQLite, and save rejected records to CSV.

    Args:
        df: Cleaned DataFrame.
        rejected_df: Rejected/invalid records DataFrame.
        clean_csv_path: Output path for cleaned CSV.
        rejected_csv_path: Output path for rejected records CSV.
        db_path: Path to SQLite database file.
        table_name: Table name to write in the SQLite database.

    Returns:
        Tuple of (row_count_read_back, column_count_read_back) from SQLite verification.

    Raises:
        ValueError: If verification fails (row/column mismatch).
    """
    clean_csv_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(clean_csv_path, index=False)
    rejected_df.to_csv(rejected_csv_path, index=False)
    logger.info("Saved cleaned data to %s (%d rows)", clean_csv_path, len(df))
    logger.info("Saved rejected records to %s (%d rows)", rejected_csv_path, len(rejected_df))

    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        logger.info("Loaded cleaned data into SQLite %s (table: %s)", db_path, table_name)

        # Read back and verify
        read_back = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)

    if len(read_back) != len(df):
        raise ValueError(
            f"SQLite row count mismatch after load: expected {len(df)}, got {len(read_back)}"
        )
    if list(read_back.columns) != list(df.columns):
        raise ValueError(
            "SQLite column mismatch after load: "
            f"expected {list(df.columns)}, got {list(read_back.columns)}"
        )

    logger.info(
        "Load verification passed: %d rows, %d columns", len(read_back), len(read_back.columns)
    )
    return len(read_back), len(read_back.columns)
