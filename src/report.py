"""Report module: generate markdown data quality and analysis reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd


def _df_to_markdown(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    """Convert a DataFrame to a simple markdown table without extra deps."""
    if df.empty:
        return "_No data available._"
    display_df = df.copy()
    for col in display_df.select_dtypes(include=["float", "float64"]).columns:
        display_df[col] = display_df[col].map(lambda x: f"{x:{floatfmt}}" if pd.notna(x) else "")
    headers = [str(c) for c in display_df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display_df.iterrows():
        vals = [str(v) if pd.notna(v) else "" for v in row.tolist()]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def generate_quality_report(
    raw_profile: Dict[str, Any],
    clean_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Generate a data quality report in Markdown.

    Args:
        raw_profile: Profile metrics from raw data.
        clean_df: Cleaned DataFrame.
        rejected_df: Rejected records DataFrame.
        output_path: Path to write the report.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    null_counts = raw_profile.get("null_counts", {})
    out_of_range = raw_profile.get("out_of_range_counts", {})
    unique_cats = raw_profile.get("unique_categorical_values", {})

    rejection_counts = (
        rejected_df["rejection_reason"].value_counts().to_dict()
        if not rejected_df.empty and "rejection_reason" in rejected_df.columns
        else {}
    )
    flag_counts = (
        clean_df["data_quality_flag"].value_counts().to_dict()
        if "data_quality_flag" in clean_df.columns
        else {}
    )

    lines = [
        "# Data Quality Report",
        "",
        "## 1. Before Cleaning (Raw Data Profile)",
        f"- **Rows read:** {raw_profile.get('row_count', 0)}",
        f"- **Columns:** {raw_profile.get('column_count', 0)}",
        f"- **Total null values:** {raw_profile.get('total_nulls', 0)}",
        f"- **Duplicate Student IDs:** {raw_profile.get('duplicate_student_ids', 0)}",
        f"- **Exact duplicate rows:** {raw_profile.get('exact_duplicate_rows', 0)}",
        "",
        "### Null counts per column",
    ]
    for col, count in null_counts.items():
        lines.append(f"- {col}: {count}")

    lines += ["", "### Out-of-range / invalid type counts (detected in raw data)"]
    if out_of_range:
        for col, count in out_of_range.items():
            lines.append(f"- {col}: {count}")
    else:
        lines.append("- None detected")

    lines += ["", "### Unique categorical values (raw)"]
    if unique_cats:
        for col, vals in unique_cats.items():
            preview = ", ".join(vals[:20])
            suffix = " ..." if len(vals) > 20 else ""
            lines.append(f"- **{col}:** {preview}{suffix}")
    else:
        lines.append("- Not available")

    lines += [
        "",
        "## 2. After Cleaning",
        f"- **Cleaned rows:** {len(clean_df)}",
        f"- **Cleaned columns:** {len(clean_df.columns)}",
        f"- **Rejected records:** {len(rejected_df)}",
        "",
        "### Cleaned data quality flags",
    ]
    if flag_counts:
        for flag, count in sorted(flag_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- `{flag}`: {count}")
    else:
        lines.append("- No flags recorded")

    lines += ["", "## 3. What Was Fixed"]
    lines.append("- Trimmed whitespace and standardized name casing (title case).")
    lines.append("- Mapped department and gender variants to canonical values using config dictionaries.")
    lines.append("- Converted Age, Attendance, and Marks to numeric types.")
    lines.append("- Dropped exact duplicate rows; for conflicting duplicate Student IDs kept the first occurrence.")
    lines.append("- Flagged out-of-range Marks (0-100), Attendance (0-100), and Age (plausible range) as NaN instead of silently correcting them.")
    lines.append("- Filled missing Attendance with the department median (robust, department-specific).")
    lines.append("- Left missing/invalid Marks as NaN and flagged them (marks are not invented).")
    lines.append("- Added derived fields: Percentage, Grade_Computed, Performance_Category, Attendance_Band, and data_quality_flag.")

    lines += ["", "## 4. What Was Rejected", "Records were written to `data/processed/rejected_records.csv` so nothing disappears silently."]
    if rejection_counts:
        lines.append("")
        lines.append("### Rejection reasons")
        for reason, count in sorted(rejection_counts.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("")
        lines.append("- No records rejected.")

    lines += [
        "",
        "## 5. Notes",
        "- Marks are not imputed because they represent actual academic performance; inventing them would distort analysis.",
        "- Attendance is imputed with the department median to preserve reasonable distributions while handling missing entries.",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_analysis_report(
    analysis_results: Dict[str, Any],
    output_path: Path,
) -> None:
    """Generate an analysis summary report in Markdown.

    Args:
        analysis_results: Dictionary produced by the analyze module.
        output_path: Path to write the report.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    avg_marks = analysis_results.get("avg_marks_by_department", pd.Series(dtype=float))
    corr = analysis_results.get("attendance_marks_correlation", float("nan"))
    corr_n = analysis_results.get("correlation_sample_size", 0)
    grade_dist = analysis_results.get("grade_distribution", pd.Series(dtype=int))
    dept_comp = analysis_results.get("department_comparison", pd.DataFrame())
    top_perf = analysis_results.get("top_performers", pd.DataFrame())
    bottom_perf = analysis_results.get("bottom_performers", pd.DataFrame())
    low_att = analysis_results.get("low_attendance_count", 0)
    low_att_thr = analysis_results.get("low_attendance_threshold", 75.0)

    lines = ["# Analysis Summary", "", "## Key Findings"]

    # Average marks by department
    if not avg_marks.empty:
        best_dept = str(avg_marks.idxmax())
        best_avg = float(avg_marks.max())
        worst_dept = str(avg_marks.idxmin())
        worst_avg = float(avg_marks.min())
        lines.append(
            f"- **Average marks by department:** highest is **{best_dept}** ({best_avg:.2f}), "
            f"lowest is **{worst_dept}** ({worst_avg:.2f})."
        )
    else:
        lines.append("- **Average marks by department:** not available.")

    # Correlation
    if pd.notna(corr):
        strength = "weak"
        if abs(corr) >= 0.7:
            strength = "strong"
        elif abs(corr) >= 0.4:
            strength = "moderate"
        direction = "positive" if corr >= 0 else "negative"
        lines.append(
            f"- **Attendance vs marks correlation:** {corr:.3f} ({strength} {direction}) "
            f"based on {corr_n} students with both values present."
        )
    else:
        lines.append("- **Attendance vs marks correlation:** not available (insufficient data).")

    # Grade distribution
    if not grade_dist.empty:
        total = int(grade_dist.sum())
        top_grade = str(grade_dist.idxmax())
        top_grade_count = int(grade_dist.max())
        lines.append(
            f"- **Grade distribution:** most common grade is **{top_grade}** "
            f"({top_grade_count} of {total} students)."
        )
    else:
        lines.append("- **Grade distribution:** not available.")

    # Low attendance
    lines.append(
        f"- **Low attendance:** {low_att} students have attendance below {low_att_thr:.0f}%."
    )

    lines += ["", "## Average Marks by Department"]
    if not avg_marks.empty:
        avg_df = avg_marks.reset_index()
        avg_df.columns = ["Department", "Average Marks"]
        lines.append(_df_to_markdown(avg_df))
    else:
        lines.append("_No data available._")

    lines += ["", "## Department Comparison"]
    if not dept_comp.empty:
        comp_df = dept_comp.reset_index()
        lines.append(_df_to_markdown(comp_df))
    else:
        lines.append("_No data available._")

    lines += ["", "## Grade Distribution"]
    if not grade_dist.empty:
        gd_df = grade_dist.reset_index()
        gd_df.columns = ["Grade", "Count"]
        lines.append(_df_to_markdown(gd_df, floatfmt=".0f"))
    else:
        lines.append("_No data available._")

    lines += ["", "## Top Performers (by Marks)"]
    if not top_perf.empty:
        lines.append(_df_to_markdown(top_perf.reset_index(drop=True)))
    else:
        lines.append("_No data available._")

    lines += ["", "## Bottom Performers (by Marks)"]
    if not bottom_perf.empty:
        lines.append(_df_to_markdown(bottom_perf.reset_index(drop=True)))
    else:
        lines.append("_No data available._")

    lines += [
        "",
        "## Charts",
        "Generated charts are saved in `outputs/charts/`:",
        "- `data_quality_issues.png`",
        "- `grade_distribution.png`",
        "- `avg_marks_by_department.png`",
        "- `attendance_vs_marks.png`",
        "- `marks_distribution.png`",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
