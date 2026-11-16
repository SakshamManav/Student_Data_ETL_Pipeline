"""Profiling module: compute data quality metrics before cleaning."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .config import ATTENDANCE_MAX, ATTENDANCE_MIN, MARKS_MAX, MARKS_MIN


def _safe_numeric(series: pd.Series) -> pd.Series:
    """Coerce a series to numeric for range checks, ignoring non-numeric values."""
    return pd.to_numeric(series, errors="coerce")


def profile_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a data quality profile for a DataFrame.

    Args:
        df: Input DataFrame (typically raw data).

    Returns:
        Dictionary containing row count, null counts, duplicate counts,
        out-of-range counts, and categorical unique values.
    """
    profile: Dict[str, Any] = {}
    profile["row_count"] = int(len(df))
    profile["column_count"] = int(len(df.columns))
    profile["columns"] = list(df.columns)

    null_counts = df.isna().sum()
    profile["null_counts"] = {col: int(count) for col, count in null_counts.items()}
    profile["total_nulls"] = int(null_counts.sum())

    if "Student ID" in df.columns:
        profile["duplicate_student_ids"] = int(df["Student ID"].duplicated().sum())
    else:
        profile["duplicate_student_ids"] = 0
    profile["exact_duplicate_rows"] = int(df.duplicated().sum())

    # Out-of-range counts (based on coercible numeric values)
    out_of_range: Dict[str, int] = {}
    if "Marks" in df.columns:
        marks = _safe_numeric(df["Marks"])
        out_of_range["Marks"] = int(((marks < MARKS_MIN) | (marks > MARKS_MAX)).sum(skipna=True))
    if "Attendance" in df.columns:
        att = _safe_numeric(df["Attendance"])
        out_of_range["Attendance"] = int(
            ((att < ATTENDANCE_MIN) | (att > ATTENDANCE_MAX)).sum(skipna=True)
        )
    if "Age" in df.columns:
        age = _safe_numeric(df["Age"])
        # Plausible age range mirrored from config via transform; profile just reports extremes
        out_of_range["Age_non_numeric"] = int(
            df["Age"].notna().sum() - age.notna().sum()
        ) if df["Age"].dtype == object else 0
    profile["out_of_range_counts"] = out_of_range

    categorical_cols = ["Department", "Gender", "Grade"]
    unique_values: Dict[str, List[str]] = {}
    for col in categorical_cols:
        if col in df.columns:
            vals = df[col].dropna().astype(str).unique().tolist()
            unique_values[col] = sorted(vals)
    profile["unique_categorical_values"] = unique_values

    return profile
