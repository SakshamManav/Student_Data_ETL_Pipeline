"""Generate dirty sample student data for the ETL pipeline.

Creates ~300 records with a fixed seed and injects realistic data
quality issues (missing values, duplicates, out-of-range, inconsistent
labels/casing/whitespace, mixed types). Includes the exact examples
from slide 7: S101, S102, S103.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.config import DATA_RAW_DIR, RANDOM_SEED, RAW_DATA_FILE, SAMPLE_RECORD_COUNT


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
    "Isha", "Ananya", "Diya", "Aadhya", "Myra", "Sara", "Riya", "Priya",
    "Rahul", "Karan", "Neha", "Pooja", "Amit", "Sneha", "Vikram", "Meera",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair",
    "Iyer", "Das", "Joshi", "Mehta", "Khan", "Roy", "Chopra", "Bose",
]
DEPARTMENTS_CLEAN = ["Computer", "Commerce", "Science", "Arts", "Management"]
DEPT_VARIANTS = {
    "Computer": ["Computer", "COMPUTER", " Computer ", "comp sci", "CS"],
    "Commerce": ["Commerce", "COMMERCE", " commerce", "BCom"],
    "Science": ["Science", "SCIENCE", " Science ", "Sci", "BSc"],
    "Arts": ["Arts", "ARTS", " arts ", "Humanities"],
    "Management": ["Management", "MANAGEMENT", " Mgmt ", "BBA"],
}
GENDER_VARIANTS = ["Male", "male", "M", "Female", "female", "F", "Other"]


def _random_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _messy_name(rng: random.Random, name: str) -> str:
    choice = rng.random()
    if choice < 0.2:
        return name.lower()
    if choice < 0.35:
        return name.upper()
    if choice < 0.5:
        return f"  {name}  "
    if choice < 0.6:
        return f" {name.lower()} "
    return name


def _grade_from_marks(marks: Any) -> Any:
    try:
        if pd.isna(marks):
            return np.nan
        m = float(marks)
    except (TypeError, ValueError):
        return np.nan
    if m < 0 or m > 100:
        return "Invalid"
    if m >= 90:
        return "A"
    if m >= 75:
        return "B"
    if m >= 60:
        return "C"
    if m >= 40:
        return "D"
    return "F"


def generate_records(count: int = SAMPLE_RECORD_COUNT, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate a DataFrame of dirty student records."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    records: List[Dict[str, Any]] = []

    # Slide 7 exact examples
    records.append(
        {
            "Student ID": "S101",
            "Name": "Aarav Sharma",
            "Age": 20,
            "Gender": "Male",
            "Department": "Computer",
            "Attendance": 92.0,
            "Marks": 85.0,
            "Grade": "B",
        }
    )
    records.append(
        {
            "Student ID": "S102",
            "Name": "Diya Patel",
            "Age": 19,
            "Gender": "Female",
            "Department": "Commerce",
            "Attendance": np.nan,  # missing attendance
            "Marks": 78.0,
            "Grade": "B",
        }
    )
    records.append(
        {
            "Student ID": "S103",
            "Name": "Rahul Verma",
            "Age": 21,
            "Gender": "Male",
            "Department": "Science",
            "Attendance": 88.0,
            "Marks": 105.0,  # invalid marks
            "Grade": "Invalid",
        }
    )

    next_id = 104
    while len(records) < count:
        sid = f"S{next_id}"
        next_id += 1
        dept = rng.choice(DEPARTMENTS_CLEAN)
        dept_val = rng.choice(DEPT_VARIANTS[dept])
        name = _messy_name(rng, _random_name(rng))
        gender = rng.choice(GENDER_VARIANTS)
        age = int(np_rng.integers(17, 26))
        attendance = float(np_rng.integers(40, 101))
        marks = float(np_rng.integers(20, 101))

        # Inject issues with controlled probabilities
        roll = rng.random()
        if roll < 0.06:
            attendance = np.nan  # missing attendance
        elif roll < 0.09:
            marks = np.nan  # missing marks
        elif roll < 0.12:
            marks = float(rng.choice([105, 110, -5, -10]))  # out-of-range marks
        elif roll < 0.15:
            attendance = float(rng.choice([105, 120, -5]))  # out-of-range attendance
        elif roll < 0.17:
            age = str(age)  # age as text

        grade = _grade_from_marks(marks)
        records.append(
            {
                "Student ID": sid,
                "Name": name,
                "Age": age,
                "Gender": gender,
                "Department": dept_val,
                "Attendance": attendance,
                "Marks": marks,
                "Grade": grade,
            }
        )

    df = pd.DataFrame(records)

    # Add deliberate duplicates (exact and conflicting)
    # Exact duplicate of S101
    s101_row = df[df["Student ID"] == "S101"].iloc[0].to_dict()
    df = pd.concat([df, pd.DataFrame([s101_row])], ignore_index=True)

    # Conflicting duplicate of S103 (different marks/attendance)
    conflict_s103 = s101_row.copy()
    conflict_s103.update(
        {
            "Student ID": "S103",
            "Name": " rahul verma ",
            "Attendance": 70.0,
            "Marks": 65.0,
            "Grade": "C",
        }
    )
    df = pd.concat([df, pd.DataFrame([conflict_s103])], ignore_index=True)

    # A few more random duplicates/conflicts
    extra_dups: List[Dict[str, Any]] = []
    sample_ids = df["Student ID"].dropna().unique().tolist()
    for sid in rng.sample(sample_ids, k=min(6, len(sample_ids))):
        base = df[df["Student ID"] == sid].iloc[0].to_dict()
        if rng.random() < 0.5:
            extra_dups.append(base.copy())  # exact
        else:
            variant = base.copy()
            variant["Marks"] = float(rng.randint(30, 95))
            variant["Attendance"] = float(rng.randint(50, 100))
            variant["Name"] = str(variant["Name"]).lower()
            extra_dups.append(variant)  # conflicting
    if extra_dups:
        df = pd.concat([df, pd.DataFrame(extra_dups)], ignore_index=True)

    # Shuffle but keep deterministic
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


def main() -> None:
    """Generate and save the raw sample dataset."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_records()
    df.to_csv(RAW_DATA_FILE, index=False)
    print(f"Generated {len(df)} records -> {RAW_DATA_FILE}")


if __name__ == "__main__":
    main()
