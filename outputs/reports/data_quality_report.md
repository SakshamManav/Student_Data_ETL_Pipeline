# Data Quality Report

## 1. Before Cleaning (Raw Data Profile)
- **Rows read:** 991
- **Columns:** 13
- **Total null values:** 490
- **Duplicate Student IDs:** 0
- **Exact duplicate rows:** 0

### Null counts per column
- Student ID: 1
- Name: 10
- Age: 78
- Gender: 20
- Department: 9
- Attendance: 0
- Marks: 81
- Grade: 48
- data_quality_flag: 0
- Percentage: 81
- Grade_Computed: 81
- Performance_Category: 81
- Attendance_Band: 0

### Out-of-range / invalid type counts (detected in raw data)
- Marks: 0
- Attendance: 0
- Age_non_numeric: 0

### Unique categorical values (raw)
- **Department:** Art, Arts, Comm., Commerce, Computer, Management, Science
- **Gender:** Female, Male
- **Grade:** A, B, C, D, F, a, b, c, d, f

## 2. After Cleaning
- **Cleaned rows:** 991
- **Cleaned columns:** 13
- **Rejected records:** 0

### Cleaned data quality flags
- `ok`: 910
- `missing_marks`: 81

## 3. What Was Fixed
- Trimmed whitespace and standardized name casing (title case).
- Mapped department and gender variants to canonical values using config dictionaries.
- Converted Age, Attendance, and Marks to numeric types.
- Dropped exact duplicate rows; for conflicting duplicate Student IDs kept the first occurrence.
- Flagged out-of-range Marks (0-100), Attendance (0-100), and Age (plausible range) as NaN instead of silently correcting them.
- Filled missing Attendance with the department median (robust, department-specific).
- Left missing/invalid Marks as NaN and flagged them (marks are not invented).
- Added derived fields: Percentage, Grade_Computed, Performance_Category, Attendance_Band, and data_quality_flag.

## 4. What Was Rejected
Records were written to `data/processed/rejected_records.csv` so nothing disappears silently.

- No records rejected.

## 5. Notes
- Marks are not imputed because they represent actual academic performance; inventing them would distort analysis.
- Attendance is imputed with the department median to preserve reasonable distributions while handling missing entries.
