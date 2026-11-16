"""Transformation module: clean, validate, and enrich student data."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .config import (
    AGE_MAX,
    AGE_MIN,
    ATTENDANCE_BANDS,
    ATTENDANCE_MAX,
    ATTENDANCE_MIN,
    DEPARTMENT_MAP,
    GENDER_MAP,
    GRADE_BANDS,
    MARKS_MAX,
    MARKS_MIN,
    PERFORMANCE_MAP,
)

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> str:
    """Return a stripped, lowercased string for mapping lookups."""
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def _title_case_name(value: Any) -> Any:
    """Standardize name casing and whitespace."""
    if pd.isna(value):
        return np.nan
    cleaned = " ".join(str(value).strip().split())
    return cleaned.title() if cleaned else np.nan


def _parse_attendance(value: Any) -> Any:
    """Parse attendance values such as '92%' into numeric percentages."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip().replace("%", "").strip()
    if not text:
        return np.nan
    try:
        return float(text)
    except (TypeError, ValueError):
        return np.nan


def _parse_age(value: Any) -> Any:
    """Extract the leading integer from an age value such as '19 yrs'."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return np.nan if np.isnan(value) else int(value)
    match = re.match(r"\s*(-?\d+)", str(value))
    if match is None:
        return np.nan
    return int(match.group(1))


def _standardize_grade(value: Any) -> Any:
    """Standardize grade labels to uppercase."""
    if pd.isna(value):
        return np.nan
    cleaned = str(value).strip().upper()
    return cleaned if cleaned else np.nan


def _map_category(value: Any, mapping: Dict[str, str]) -> Any:
    """Map a categorical value to its canonical form using a lookup dict."""
    if pd.isna(value):
        return np.nan
    key = _normalize_text(value)
    return mapping.get(key, str(value).strip())


def _assign_grade(percentage: Any) -> Any:
    """Assign a letter grade based on percentage and configured bands."""
    if pd.isna(percentage):
        return np.nan
    pct = float(percentage)
    for threshold, grade in GRADE_BANDS:
        if pct >= threshold:
            return grade
    return "F"


def _assign_attendance_band(attendance: Any) -> Any:
    """Assign an attendance band label."""
    if pd.isna(attendance):
        return np.nan
    att = float(attendance)
    for threshold, label in ATTENDANCE_BANDS:
        if att >= threshold:
            return label
    return "Low"


def _resolve_duplicate_ids(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Drop exact duplicates and resolve conflicting duplicate Student IDs.

    Keeps the first occurrence for conflicting IDs and logs the rest as rejected.
    """
    rejected_parts: List[pd.DataFrame] = []

    # Exact duplicate rows (all columns identical)
    exact_dups = df[df.duplicated(keep="first")].copy()
    if not exact_dups.empty:
        exact_dups["rejection_reason"] = "exact_duplicate_row"
        exact_dups["action"] = "row_removed"
        rejected_parts.append(exact_dups)
        df = df.drop_duplicates(keep="first")

    # Conflicting duplicate IDs (same ID, different content); blank IDs are ignored
    if "Student ID" in df.columns:
        id_text = df["Student ID"].astype("string").str.strip()
        valid_id_mask = id_text.notna() & id_text.ne("")
        conflict_mask = valid_id_mask & df.duplicated(subset=["Student ID"], keep="first")
        conflicts = df[conflict_mask].copy()
        if not conflicts.empty:
            conflicts["rejection_reason"] = "conflicting_duplicate_student_id"
            conflicts["action"] = "row_removed"
            rejected_parts.append(conflicts)
            df = df[~conflict_mask].copy()

    rejected_df = (
        pd.concat(rejected_parts, ignore_index=True) if rejected_parts else pd.DataFrame()
    )
    return df.reset_index(drop=True), rejected_df


def transform_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Clean, validate, and enrich student data.

    Args:
        df: Raw extracted DataFrame.

    Returns:
        Tuple of (cleaned DataFrame, rejected records DataFrame).
    """
    df = df.copy()
    rejected_records = pd.DataFrame()

    # 1. Strip whitespace and standardize text fields
    if "Name" in df.columns:
        df["Name"] = df["Name"].apply(_title_case_name)
    if "Department" in df.columns:
        df["Department"] = df["Department"].apply(lambda v: _map_category(v, DEPARTMENT_MAP))
    if "Gender" in df.columns:
        df["Gender"] = df["Gender"].apply(lambda v: _map_category(v, GENDER_MAP))
    if "Grade" in df.columns:
        df["Grade"] = df["Grade"].apply(_standardize_grade)

    # 2. Convert types (attendance may contain '%', age may contain text suffixes)
    if "Age" in df.columns:
        df["Age"] = df["Age"].apply(_parse_age)
    if "Attendance" in df.columns:
        df["Attendance"] = df["Attendance"].apply(_parse_attendance)
    if "Marks" in df.columns:
        df["Marks"] = pd.to_numeric(df["Marks"], errors="coerce")

    # 3. Handle duplicates (exact and conflicting IDs)
    df, dup_rejected = _resolve_duplicate_ids(df)
    if not dup_rejected.empty:
        logger.info("Rejected %d duplicate records", len(dup_rejected))
        rejected_records = pd.concat([rejected_records, dup_rejected], ignore_index=True)

    # Capture truly missing/unparseable attendance before range validation.
    if "Attendance" in df.columns:
        attendance_imputable_mask = df["Attendance"].isna().copy()
    else:
        attendance_imputable_mask = pd.Series(False, index=df.index)

    # 4. Validation: flag invalid values as NaN (do not silently fix)
    flags: List[str] = ["ok"] * len(df)

    def _flag(idx: int, reason: str) -> None:
        if flags[idx] == "ok":
            flags[idx] = reason
        elif reason not in flags[idx]:
            flags[idx] = f"{flags[idx]}|{reason}"

    invalid_rows: List[pd.Series] = []

    if "Marks" in df.columns:
        invalid_marks_mask = df["Marks"].notna() & (
            (df["Marks"] < MARKS_MIN) | (df["Marks"] > MARKS_MAX)
        )
        for idx in df.index[invalid_marks_mask]:
            row = df.loc[idx].copy()
            row["rejection_reason"] = "invalid_marks"
            row["action"] = "value_invalidated"
            invalid_rows.append(row)
            df.at[idx, "Marks"] = np.nan
            _flag(int(idx), "invalid_marks")

    if "Attendance" in df.columns:
        invalid_att_mask = df["Attendance"].notna() & (
            (df["Attendance"] < ATTENDANCE_MIN) | (df["Attendance"] > ATTENDANCE_MAX)
        )
        for idx in df.index[invalid_att_mask]:
            row = df.loc[idx].copy()
            row["rejection_reason"] = "invalid_attendance"
            row["action"] = "value_invalidated"
            invalid_rows.append(row)
            df.at[idx, "Attendance"] = np.nan
            _flag(int(idx), "invalid_attendance")

    if "Age" in df.columns:
        invalid_age_mask = df["Age"].notna() & (
            (df["Age"] < AGE_MIN) | (df["Age"] > AGE_MAX)
        )
        for idx in df.index[invalid_age_mask]:
            row = df.loc[idx].copy()
            row["rejection_reason"] = "invalid_age"
            row["action"] = "value_invalidated"
            invalid_rows.append(row)
            df.at[idx, "Age"] = np.nan
            _flag(int(idx), "invalid_age")

    if invalid_rows:
        invalid_df = pd.DataFrame(invalid_rows).reset_index(drop=True)
        rejected_records = pd.concat([rejected_records, invalid_df], ignore_index=True)
        logger.info("Logged %d records with invalid range values", len(invalid_df))

    # 5. Missing values
    # Attendance is filled with department median because attendance patterns are
    # often department-specific and the median is robust to outliers.
    # Marks are left as NaN and flagged (not invented) because marks represent
    # actual academic performance and imputing them would fabricate results.
    if "Attendance" in df.columns:
        missing_att_mask = attendance_imputable_mask & df["Attendance"].isna()
        if missing_att_mask.any():
            if "Department" in df.columns:
                dept_medians = df.groupby("Department")["Attendance"].transform("median")
                overall_median = df["Attendance"].median()
                fill_values = dept_medians.fillna(overall_median)
                if pd.isna(overall_median):
                    fill_values = fill_values.fillna(0.0)
                df.loc[missing_att_mask, "Attendance"] = fill_values[missing_att_mask]
            else:
                overall_median = df["Attendance"].median()
                fill_value = 0.0 if pd.isna(overall_median) else overall_median
                df.loc[missing_att_mask, "Attendance"] = fill_value
            for idx in df.index[missing_att_mask]:
                _flag(int(idx), "attendance_imputed")

    if "Marks" in df.columns:
        missing_marks_mask = df["Marks"].isna()
        for idx in df.index[missing_marks_mask]:
            _flag(int(idx), "missing_marks")

    df["data_quality_flag"] = flags

    # 6. Derived fields
    if "Marks" in df.columns:
        df["Percentage"] = df["Marks"]  # marks are out of 100
        df["Grade_Computed"] = df["Percentage"].apply(_assign_grade)
        df["Performance_Category"] = df["Grade_Computed"].map(PERFORMANCE_MAP)
    else:
        df["Percentage"] = np.nan
        df["Grade_Computed"] = np.nan
        df["Performance_Category"] = np.nan

    if "Attendance" in df.columns:
        df["Attendance_Band"] = df["Attendance"].apply(_assign_attendance_band)
    else:
        df["Attendance_Band"] = np.nan

    # Ensure rejected records file has consistent columns when empty
    if rejected_records.empty:
        rejected_records = pd.DataFrame(
            columns=list(df.columns) + ["rejection_reason", "action"]
        )
    else:
        # Keep a clear, useful subset/order for rejected output
        base_cols = [c for c in df.columns if c in rejected_records.columns or c != "data_quality_flag"]
        if "rejection_reason" not in rejected_records.columns:
            rejected_records["rejection_reason"] = "unknown"
        if "action" not in rejected_records.columns:
            rejected_records["action"] = "unknown"
        # Reindex to include all original-like columns plus reason
        for col in base_cols:
            if col not in rejected_records.columns:
                rejected_records[col] = np.nan
        ordered = [c for c in [
            "Student ID", "Name", "Age", "Gender", "Department", "Attendance", "Marks",
            "Grade", "Percentage", "Grade_Computed", "Performance_Category",
            "Attendance_Band", "rejection_reason", "action",
        ] if c in rejected_records.columns]
        remaining = [c for c in rejected_records.columns if c not in ordered]
        rejected_records = rejected_records[ordered + remaining]

    return df, rejected_records
