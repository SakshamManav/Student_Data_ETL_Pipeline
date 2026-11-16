"""Configuration for the Student Data ETL Pipeline.

Centralizes paths, schema, validation rules, and mappings so no magic
numbers or hardcoded paths are scattered across modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

# Base paths
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
OUTPUTS_CHARTS_DIR: Path = BASE_DIR / "outputs" / "charts"
OUTPUTS_REPORTS_DIR: Path = BASE_DIR / "outputs" / "reports"
LOGS_DIR: Path = BASE_DIR / "logs"

RAW_DATA_FILE: Path = DATA_RAW_DIR / "students_raw.csv"
CLEAN_DATA_FILE: Path = DATA_PROCESSED_DIR / "students_clean.csv"
CLEAN_AUDIT_DATA_FILE: Path = DATA_PROCESSED_DIR / "students_clean_audit.csv"
REJECTED_DATA_FILE: Path = DATA_PROCESSED_DIR / "rejected_records.csv"
SQLITE_DB_FILE: Path = DATA_PROCESSED_DIR / "students.db"
SQLITE_TABLE: str = "students"
SQLITE_AUDIT_TABLE: str = "students_audit"

LOG_FILE: Path = LOGS_DIR / "pipeline.log"
QUALITY_REPORT_FILE: Path = OUTPUTS_REPORTS_DIR / "data_quality_report.md"
ANALYSIS_REPORT_FILE: Path = OUTPUTS_REPORTS_DIR / "analysis_summary.md"

# Schema
REQUIRED_COLUMNS: List[str] = [
    "Student ID",
    "Name",
    "Age",
    "Gender",
    "Department",
    "Attendance",
    "Marks",
    "Grade",
]

# Validation ranges
MARKS_MIN: float = 0.0
MARKS_MAX: float = 100.0
ATTENDANCE_MIN: float = 0.0
ATTENDANCE_MAX: float = 100.0
AGE_MIN: int = 15
AGE_MAX: int = 60

# Canonical categorical values and variant mappings
DEPARTMENT_MAP: Dict[str, str] = {
    "computer": "Computer",
    "comp sci": "Computer",
    "cs": "Computer",
    "computer science": "Computer",
    "commerce": "Commerce",
    "com": "Commerce",
    "bcom": "Commerce",
    "science": "Science",
    "sci": "Science",
    "bsc": "Science",
    "arts": "Arts",
    "humanities": "Arts",
    "management": "Management",
    "mgmt": "Management",
    "bba": "Management",
}

GENDER_MAP: Dict[str, str] = {
    "m": "Male",
    "male": "Male",
    "f": "Female",
    "female": "Female",
    "o": "Other",
    "other": "Other",
}

VALID_DEPARTMENTS: List[str] = ["Computer", "Commerce", "Science", "Arts", "Management"]
VALID_GENDERS: List[str] = ["Male", "Female", "Other"]

# Grade bands: (min_percentage_inclusive, grade)
GRADE_BANDS: List[Tuple[float, str]] = [
    (90.0, "A"),
    (75.0, "B"),
    (60.0, "C"),
    (40.0, "D"),
    (0.0, "F"),
]

# Performance categories by grade
PERFORMANCE_MAP: Dict[str, str] = {
    "A": "Excellent",
    "B": "Good",
    "C": "Average",
    "D": "Below Average",
    "F": "Poor",
}

# Attendance bands: (min_inclusive, label)
ATTENDANCE_BANDS: List[Tuple[float, str]] = [
    (90.0, "High"),
    (75.0, "Regular"),
    (60.0, "Moderate"),
    (0.0, "Low"),
]

LOW_ATTENDANCE_THRESHOLD: float = 75.0

# Sample data generation
SAMPLE_RECORD_COUNT: int = 300
RANDOM_SEED: int = 42
