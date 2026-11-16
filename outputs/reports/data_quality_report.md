# Data Quality Report

## 1. Before Cleaning (Raw Data Profile)
- **Rows read:** 1579
- **Columns:** 8
- **Total null values:** 404
- **Missing Student IDs:** 8
- **Duplicate Student IDs:** 76
- **Exact duplicate rows:** 46

### Null counts per column
- Student ID: 8
- Name: 25
- Age: 45
- Gender: 34
- Department: 24
- Attendance: 99
- Marks: 116
- Grade: 53

### Out-of-range / invalid type counts (detected in raw data)
- Marks: 47
- Attendance: 24
- Age_non_numeric: 53

### Unique categorical values (raw)
- **Department:**  Computer , ARTS, Art , Arts, COMMERCE, COMPUTER, CS, Comm., Commerce, Comp Sci, Computer, MANAGEMENT, MGMT, Management, Mgmt, SCIENCE, Sci, Science, Science , arts ...
- **Gender:** F, FEMALE, Female, M, MALE, Male, f, female, m, male
- **Grade:** A, B, C, D, F, a, b, c, d, f

## 2. After Cleaning
- **Rows removed (duplicates):** 76
- **Values invalidated and flagged:** 98
- **Cleaned rows:** 1503
- **Cleaned columns:** 13
- **Reconciliation:** 1579 rows before - 76 rows removed = 1503 cleaned rows

### Cleaned data quality flags
- `ok`: 1209
- `missing_marks`: 105
- `attendance_imputed`: 82
- `invalid_marks|missing_marks`: 40
- `invalid_attendance`: 24
- `invalid_age`: 22
- `attendance_imputed|missing_marks`: 10
- `invalid_age|missing_marks`: 6
- `invalid_age|attendance_imputed`: 2
- `invalid_marks|attendance_imputed|missing_marks`: 2
- `invalid_marks|invalid_age|missing_marks`: 1

## 3. What Was Fixed
- Trimmed whitespace and standardized name casing (title case).
- Standardized grades to uppercase and mapped department/gender variants to canonical values.
- Parsed attendance values such as '92%' and ages such as '19 yrs' into numbers.
- Dropped exact duplicate rows; for conflicting duplicate Student IDs kept the first occurrence (blank IDs ignored).
- Flagged out-of-range Marks (0-100), Attendance (0-100), and Age (plausible range) as NaN instead of silently correcting them.
- Filled only truly missing/unparseable Attendance with the department median (robust, department-specific).
- Left missing/invalid Marks as NaN and flagged them (marks are not invented).
- Added derived fields: Percentage, Grade_Computed, Performance_Category, Attendance_Band, and data_quality_flag.

## 4. What Was Rejected
Entries were written to `data/processed/rejected_records.csv` so nothing disappears silently.
- Rows removed (duplicates): 76
- Values invalidated and flagged: 98

### Rejection reasons
- `exact_duplicate_row`: 46
- `invalid_marks`: 43
- `invalid_age`: 31
- `conflicting_duplicate_student_id`: 30
- `invalid_attendance`: 24

## 5. Notes
- Marks are not imputed because they represent actual academic performance; inventing them would distort analysis.
- Attendance is imputed with the department median to preserve reasonable distributions while handling missing entries.
