"""Load module: persist cleaned data to CSV and SQLite with verification."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def _verify_sqlite_table(
    conn: sqlite3.Connection,
    table_name: str,
    expected_df: pd.DataFrame,
) -> Tuple[int, int]:
    """Read back a SQLite table and verify row/column counts match."""
    read_back = pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)

    if len(read_back) != len(expected_df):
        raise ValueError(
            f"SQLite row count mismatch for '{table_name}': "
            f"expected {len(expected_df)}, got {len(read_back)}"
        )
    if list(read_back.columns) != list(expected_df.columns):
        raise ValueError(
            f"SQLite column mismatch for '{table_name}': "
            f"expected {list(expected_df.columns)}, got {list(read_back.columns)}"
        )

    logger.info(
        "Load verification passed for '%s': %d rows, %d columns",
        table_name,
        len(read_back),
        len(read_back.columns),
    )
    return len(read_back), len(read_back.columns)


def load_data(
    df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    clean_csv_path: Path,
    clean_audit_csv_path: Path,
    rejected_csv_path: Path,
    db_path: Path,
    table_name: str,
    audit_table_name: str,
) -> Tuple[int, int]:
    """Save cleaned and audit data to CSV/SQLite, and save rejected records to CSV.

    The cleaned outputs omit the ``data_quality_flag`` column, while the audit
    outputs keep it for traceability.

    Args:
        df: Cleaned DataFrame (with ``data_quality_flag`` when available).
        rejected_df: Rejected/invalid records DataFrame.
        clean_csv_path: Output path for cleaned CSV (no audit flag).
        clean_audit_csv_path: Output path for cleaned CSV including audit flags.
        rejected_csv_path: Output path for rejected records CSV.
        db_path: Path to SQLite database file.
        table_name: Table name for cleaned data in SQLite.
        audit_table_name: Table name for cleaned data with audit flags in SQLite.

    Returns:
        Tuple of (row_count_read_back, column_count_read_back) for the cleaned
        SQLite table.

    Raises:
        ValueError: If verification fails (row/column mismatch).
    """
    clean_csv_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    audit_df = df.copy()
    clean_df = (
        df.drop(columns=["data_quality_flag"])
        if "data_quality_flag" in df.columns
        else df.copy()
    )

    clean_df.to_csv(clean_csv_path, index=False)
    audit_df.to_csv(clean_audit_csv_path, index=False)
    rejected_df.to_csv(rejected_csv_path, index=False)
    logger.info("Saved cleaned data to %s (%d rows)", clean_csv_path, len(clean_df))
    logger.info("Saved cleaned audit data to %s (%d rows)", clean_audit_csv_path, len(audit_df))
    logger.info("Saved rejected records to %s (%d rows)", rejected_csv_path, len(rejected_df))

    with sqlite3.connect(db_path) as conn:
        clean_df.to_sql(table_name, conn, if_exists="replace", index=False)
        audit_df.to_sql(audit_table_name, conn, if_exists="replace", index=False)
        logger.info("Loaded cleaned data into SQLite %s (table: %s)", db_path, table_name)
        logger.info("Loaded cleaned audit data into SQLite %s (table: %s)", db_path, audit_table_name)

        verified_rows, verified_cols = _verify_sqlite_table(conn, table_name, clean_df)
        _verify_sqlite_table(conn, audit_table_name, audit_df)

    return verified_rows, verified_cols
