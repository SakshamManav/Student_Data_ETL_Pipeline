"""Extraction module: read raw student data from CSV or Excel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import pandas as pd

from .config import REQUIRED_COLUMNS

logger = logging.getLogger(__name__)


def extract_data(input_path: Union[str, Path]) -> pd.DataFrame:
    """Read CSV or Excel input, validate required columns, and return a DataFrame.

    Args:
        input_path: Path to the input .csv, .xlsx, or .xls file.

    Returns:
        Raw pandas DataFrame.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If file extension is unsupported or required columns are missing.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. Expected .csv, .xlsx, or .xls."
        )

    logger.info("Read %d rows and %d columns from %s", len(df), len(df.columns), path)

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns: {missing_cols}. Found columns: {list(df.columns)}"
        )

    return df
