"""Focused tests for transform module behaviors."""

from __future__ import annotations

import pandas as pd

from src.transform import transform_data


def _base_df(rows):
    return pd.DataFrame(rows)


def test_exact_and_conflicting_duplicates():
    df = _base_df(
        [
            {"Student ID": "S1", "Name": "A", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 80, "Marks": 70, "Grade": "C"},
            {"Student ID": "S1", "Name": "A", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 80, "Marks": 70, "Grade": "C"},
            {"Student ID": "S1", "Name": "A Different", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 75, "Marks": 60, "Grade": "C"},
        ]
    )
    clean, rejected = transform_data(df)
    assert len(clean) == 1
    assert clean.iloc[0]["Student ID"] == "S1"
    reasons = set(rejected["rejection_reason"].astype(str))
    assert "exact_duplicate_row" in reasons
    assert "conflicting_duplicate_student_id" in reasons


def test_marks_range_validation_flags_invalid():
    df = _base_df(
        [
            {"Student ID": "S10", "Name": "Test", "Age": 20, "Gender": "F", "Department": "Science", "Attendance": 90, "Marks": 105, "Grade": "X"},
            {"Student ID": "S11", "Name": "Test2", "Age": 20, "Gender": "F", "Department": "Science", "Attendance": 90, "Marks": -5, "Grade": "X"},
        ]
    )
    clean, rejected = transform_data(df)
    assert clean["Marks"].isna().all()
    assert "invalid_marks" in "|".join(clean["data_quality_flag"].tolist())
    assert (rejected["rejection_reason"] == "invalid_marks").sum() >= 2


def test_attendance_range_validation_flags_invalid():
    df = _base_df(
        [
            {"Student ID": "S20", "Name": "Test", "Age": 20, "Gender": "M", "Department": "Arts", "Attendance": 120, "Marks": 70, "Grade": "C"},
        ]
    )
    clean, rejected = transform_data(df)
    assert clean.loc[0, "Attendance"] != 120
    assert "invalid_attendance" in clean.loc[0, "data_quality_flag"]
    assert "invalid_attendance" in rejected["rejection_reason"].values


def test_department_and_gender_normalization():
    df = _base_df(
        [
            {"Student ID": "S30", "Name": "  john DOE ", "Age": 21, "Gender": "male", "Department": " comp sci ", "Attendance": 85, "Marks": 80, "Grade": "B"},
            {"Student ID": "S31", "Name": "JANE", "Age": "22", "Gender": "F", "Department": "BCom", "Attendance": 88, "Marks": 75, "Grade": "B"},
        ]
    )
    clean, _ = transform_data(df)
    assert set(clean["Department"]) == {"Computer", "Commerce"}
    assert set(clean["Gender"]) == {"Male", "Female"}
    assert "John Doe" in clean["Name"].values
    assert clean["Age"].dtype.kind in {"i", "f"}


def test_grade_assignment_from_bands():
    df = _base_df(
        [
            {"Student ID": "S40", "Name": "A", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 90, "Marks": 95, "Grade": ""},
            {"Student ID": "S41", "Name": "B", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 90, "Marks": 80, "Grade": ""},
            {"Student ID": "S42", "Name": "C", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 90, "Marks": 65, "Grade": ""},
            {"Student ID": "S43", "Name": "D", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 90, "Marks": 45, "Grade": ""},
            {"Student ID": "S44", "Name": "F", "Age": 20, "Gender": "M", "Department": "Computer", "Attendance": 90, "Marks": 20, "Grade": ""},
        ]
    )
    clean, _ = transform_data(df)
    grades = dict(zip(clean["Student ID"], clean["Grade_Computed"]))
    assert grades["S40"] == "A"
    assert grades["S41"] == "B"
    assert grades["S42"] == "C"
    assert grades["S43"] == "D"
    assert grades["S44"] == "F"


def test_missing_attendance_imputed_with_department_median():
    df = _base_df(
        [
            {"Student ID": "S50", "Name": "A", "Age": 20, "Gender": "M", "Department": "Science", "Attendance": 80, "Marks": 70, "Grade": "C"},
            {"Student ID": "S51", "Name": "B", "Age": 20, "Gender": "M", "Department": "Science", "Attendance": 100, "Marks": 90, "Grade": "A"},
            {"Student ID": "S52", "Name": "C", "Age": 20, "Gender": "M", "Department": "Science", "Attendance": None, "Marks": 60, "Grade": "C"},
        ]
    )
    clean, _ = transform_data(df)
    filled = clean.loc[clean["Student ID"] == "S52", "Attendance"].iloc[0]
    assert filled == 90.0  # median of 80 and 100
    assert "attendance_imputed" in clean.loc[clean["Student ID"] == "S52", "data_quality_flag"].iloc[0]


def test_missing_marks_left_as_nan_and_flagged():
    df = _base_df(
        [
            {"Student ID": "S60", "Name": "A", "Age": 20, "Gender": "M", "Department": "Arts", "Attendance": 85, "Marks": None, "Grade": ""},
        ]
    )
    clean, _ = transform_data(df)
    assert pd.isna(clean.loc[0, "Marks"])
    assert "missing_marks" in clean.loc[0, "data_quality_flag"]
    assert pd.isna(clean.loc[0, "Grade_Computed"])
