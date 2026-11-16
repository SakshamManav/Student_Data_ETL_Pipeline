"""Analysis module: compute statistics and generate charts from cleaned data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import LOW_ATTENDANCE_THRESHOLD

logger = logging.getLogger(__name__)


def _style_axes(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    """Apply consistent, readable styling to chart axes."""
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.4)


def analyze_data(
    clean_df: pd.DataFrame,
    raw_profile: Dict[str, Any],
    charts_dir: Path,
) -> Dict[str, Any]:
    """Compute analysis metrics and save charts.

    Args:
        clean_df: Cleaned student DataFrame.
        raw_profile: Profile dictionary from the raw (pre-clean) data.
        charts_dir: Directory to save chart PNG files.

    Returns:
        Dictionary of computed analysis results for reporting.
    """
    charts_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Any] = {}

    # Metrics
    avg_marks_dept = (
        clean_df.groupby("Department")["Marks"].mean().sort_values(ascending=False)
        if "Department" in clean_df.columns and "Marks" in clean_df.columns
        else pd.Series(dtype=float)
    )
    results["avg_marks_by_department"] = avg_marks_dept

    valid_corr_df = clean_df[["Attendance", "Marks"]].dropna()
    if len(valid_corr_df) >= 2:
        correlation = float(valid_corr_df["Attendance"].corr(valid_corr_df["Marks"]))
    else:
        correlation = float("nan")
    results["attendance_marks_correlation"] = correlation
    results["correlation_sample_size"] = int(len(valid_corr_df))

    grade_counts = (
        clean_df["Grade_Computed"].value_counts().sort_index()
        if "Grade_Computed" in clean_df.columns
        else pd.Series(dtype=int)
    )
    results["grade_distribution"] = grade_counts

    dept_comparison = (
        clean_df.groupby("Department")
        .agg(
            Students=("Student ID", "count"),
            Avg_Marks=("Marks", "mean"),
            Avg_Attendance=("Attendance", "mean"),
        )
        .sort_values("Avg_Marks", ascending=False)
        if "Department" in clean_df.columns
        else pd.DataFrame()
    )
    results["department_comparison"] = dept_comparison

    marks_for_ranking = clean_df.dropna(subset=["Marks"]).copy()
    top_performers = marks_for_ranking.nlargest(5, "Marks")[
        ["Student ID", "Name", "Department", "Marks", "Attendance"]
    ]
    bottom_performers = marks_for_ranking.nsmallest(5, "Marks")[
        ["Student ID", "Name", "Department", "Marks", "Attendance"]
    ]
    results["top_performers"] = top_performers
    results["bottom_performers"] = bottom_performers

    low_attendance_count = int(
        (clean_df["Attendance"] < LOW_ATTENDANCE_THRESHOLD).sum()
        if "Attendance" in clean_df.columns
        else 0
    )
    results["low_attendance_count"] = low_attendance_count
    results["low_attendance_threshold"] = LOW_ATTENDANCE_THRESHOLD

    # Chart 1: Data quality issues found (from raw profile)
    issues = {
        "Missing Values": int(raw_profile.get("total_nulls", 0)),
        "Duplicate IDs": int(raw_profile.get("duplicate_student_ids", 0)),
        "Exact Duplicates": int(raw_profile.get("exact_duplicate_rows", 0)),
        "Out-of-range Marks": int(raw_profile.get("out_of_range_counts", {}).get("Marks", 0)),
        "Out-of-range Attendance": int(
            raw_profile.get("out_of_range_counts", {}).get("Attendance", 0)
        ),
    }
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(list(issues.keys()), list(issues.values()), color="#4C72B0")
    ax.bar_label(bars, padding=3)
    _style_axes(ax, "Data Quality Issues Found (Raw Data)", "Issue Type", "Count")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(charts_dir / "data_quality_issues.png", dpi=150)
    plt.close(fig)

    # Chart 2: Grade distribution
    fig, ax = plt.subplots(figsize=(7, 5))
    grade_order = [g for g in ["A", "B", "C", "D", "F"] if g in grade_counts.index]
    grade_plot = grade_counts.reindex(grade_order).fillna(0)
    colors = {"A": "#2ecc71", "B": "#3498db", "C": "#f1c40f", "D": "#e67e22", "F": "#e74c3c"}
    bar_colors = [colors.get(g, "#95a5a6") for g in grade_plot.index]
    bars = ax.bar(grade_plot.index.astype(str), grade_plot.values, color=bar_colors)
    ax.bar_label(bars, padding=3)
    _style_axes(ax, "Grade Distribution (Cleaned Data)", "Grade", "Number of Students")
    fig.tight_layout()
    fig.savefig(charts_dir / "grade_distribution.png", dpi=150)
    plt.close(fig)

    # Chart 3: Average marks by department
    fig, ax = plt.subplots(figsize=(8, 5))
    if not avg_marks_dept.empty:
        bars = ax.bar(avg_marks_dept.index.astype(str), avg_marks_dept.values, color="#55A868")
        ax.bar_label(bars, fmt="%.1f", padding=3)
    _style_axes(ax, "Average Marks by Department", "Department", "Average Marks")
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(charts_dir / "avg_marks_by_department.png", dpi=150)
    plt.close(fig)

    # Chart 4: Attendance vs marks scatter with trendline
    fig, ax = plt.subplots(figsize=(7, 5))
    if not valid_corr_df.empty:
        ax.scatter(
            valid_corr_df["Attendance"],
            valid_corr_df["Marks"],
            alpha=0.6,
            edgecolors="w",
            linewidths=0.3,
            color="#4C72B0",
            label="Students",
        )
        if len(valid_corr_df) >= 2:
            x = valid_corr_df["Attendance"].to_numpy()
            y = valid_corr_df["Marks"].to_numpy()
            slope, intercept = np.polyfit(x, y, 1)
            x_line = np.linspace(x.min(), x.max(), 100)
            y_line = slope * x_line + intercept
            ax.plot(x_line, y_line, color="#C44E52", linewidth=2, label="Trendline")
        ax.legend()
    _style_axes(ax, "Attendance vs Marks", "Attendance (%)", "Marks")
    fig.tight_layout()
    fig.savefig(charts_dir / "attendance_vs_marks.png", dpi=150)
    plt.close(fig)

    # Chart 5: Marks distribution histogram
    fig, ax = plt.subplots(figsize=(7, 5))
    marks_data = clean_df["Marks"].dropna()
    if not marks_data.empty:
        ax.hist(marks_data, bins=10, color="#8172B3", edgecolor="white", alpha=0.85)
    _style_axes(ax, "Marks Distribution", "Marks", "Number of Students")
    fig.tight_layout()
    fig.savefig(charts_dir / "marks_distribution.png", dpi=150)
    plt.close(fig)

    logger.info("Saved charts to %s", charts_dir)
    return results
