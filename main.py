"""CLI entry point for the Student Data ETL Pipeline.

Usage:
    python main.py --input data/raw/students_raw.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict

from src.analyze import analyze_data
from src.config import (
    ANALYSIS_REPORT_FILE,
    CLEAN_AUDIT_DATA_FILE,
    CLEAN_DATA_FILE,
    DATA_PROCESSED_DIR,
    LOG_FILE,
    LOGS_DIR,
    OUTPUTS_CHARTS_DIR,
    QUALITY_REPORT_FILE,
    RAW_DATA_FILE,
    REJECTED_DATA_FILE,
    SQLITE_AUDIT_TABLE,
    SQLITE_DB_FILE,
    SQLITE_TABLE,
)
from src.extract import extract_data
from src.load import load_data
from src.profile import profile_data
from src.report import generate_analysis_report, generate_quality_report
from src.transform import transform_data


def setup_logging(log_path: Path) -> None:
    """Configure logging to console and a log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(log_path, encoding="utf-8")]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def run_pipeline(input_path: Path) -> Dict[str, Any]:
    """Run the full ETL pipeline in order and return stage outputs.

    Stages: Input -> Profile -> Clean & Validate -> Transform -> Load -> Analyze -> Report.
    The pipeline is idempotent: running it twice with the same input produces the same outputs.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting ETL pipeline with input: %s", input_path)

    # Ensure output directories exist
    for directory in [DATA_PROCESSED_DIR, OUTPUTS_CHARTS_DIR, QUALITY_REPORT_FILE.parent, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    # Extract
    raw_df = extract_data(input_path)

    # Profile (before cleaning)
    raw_profile = profile_data(raw_df)
    logger.info(
        "Profile: %d rows, %d nulls, %d duplicate IDs, %d exact duplicate rows",
        raw_profile["row_count"],
        raw_profile["total_nulls"],
        raw_profile["duplicate_student_ids"],
        raw_profile["exact_duplicate_rows"],
    )

    # Transform (clean & validate, derived fields)
    clean_df, rejected_df = transform_data(raw_df)
    logger.info("Transform complete: %d cleaned rows, %d rejected rows", len(clean_df), len(rejected_df))

    # Load (CSV + SQLite) with verification
    verified_rows, verified_cols = load_data(
        clean_df,
        rejected_df,
        CLEAN_DATA_FILE,
        CLEAN_AUDIT_DATA_FILE,
        REJECTED_DATA_FILE,
        SQLITE_DB_FILE,
        SQLITE_TABLE,
        SQLITE_AUDIT_TABLE,
    )
    logger.info("Load verified: %d rows, %d columns in SQLite", verified_rows, verified_cols)

    # Analyze
    analysis_results = analyze_data(clean_df, raw_profile, OUTPUTS_CHARTS_DIR)
    logger.info("Analysis complete: charts saved to %s", OUTPUTS_CHARTS_DIR)

    # Report
    generate_quality_report(raw_profile, clean_df, rejected_df, QUALITY_REPORT_FILE)
    generate_analysis_report(analysis_results, ANALYSIS_REPORT_FILE)
    logger.info("Reports generated: %s, %s", QUALITY_REPORT_FILE, ANALYSIS_REPORT_FILE)

    logger.info("ETL pipeline finished successfully.")

    return {
        "raw_df": raw_df,
        "raw_profile": raw_profile,
        "clean_df": clean_df,
        "rejected_df": rejected_df,
        "analysis_results": analysis_results,
        "verified_rows": verified_rows,
        "verified_cols": verified_cols,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Student Data ETL Pipeline")
    parser.add_argument(
        "--input",
        type=str,
        default=str(RAW_DATA_FILE),
        help="Path to input CSV or Excel file (default: data/raw/students_raw.csv)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(LOG_FILE)
    try:
        run_pipeline(Path(args.input))
    except Exception:
        logging.getLogger(__name__).exception("Pipeline failed")
        sys.exit(1)
