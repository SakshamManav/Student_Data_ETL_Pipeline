"""Streamlit UI for Student Data ETL Pipeline.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from main import run_pipeline, setup_logging
from src.config import (
    ANALYSIS_REPORT_FILE,
    CLEAN_DATA_FILE,
    LOG_FILE,
    OUTPUTS_CHARTS_DIR,
    QUALITY_REPORT_FILE,
    RAW_DATA_FILE,
    REJECTED_DATA_FILE,
)
from src.extract import extract_data
from src.profile import profile_data

st.set_page_config(page_title="Student ETL Pipeline", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px; }
    .hero {
        padding: 2.2rem 1.5rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        color: #58a6ff;
        line-height: 1.1;
        margin-bottom: 0.4rem;
    }
    .hero-subtitle {
        font-size: 1.15rem;
        color: #c9d1d9;
        font-weight: 500;
        margin-bottom: 0.8rem;
    }
    .hero-badges span {
        display: inline-block;
        margin: 0.2rem 0.3rem;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        border: 1px solid #30363d;
        background: #21262d;
        color: #e6edf3;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .section-card {
        padding: 1rem 1.2rem;
        border: 1px solid #30363d;
        border-radius: 12px;
        background: #161b22;
        margin-bottom: 0.5rem;
    }
    .step-header { font-size: 1.5rem; font-weight: 800; margin: 0.2rem 0 0.6rem 0; }
    .section-label { font-size: 1.1rem; font-weight: 700; margin-bottom: 0.25rem; }
    .accent-blue { color: #58a6ff !important; font-weight: 700; }
    .accent-green { color: #3fb950 !important; font-weight: 700; }
    .accent-orange { color: #f2cc60 !important; font-weight: 700; }
    .accent-purple { color: #bc8cff !important; font-weight: 700; }
    .accent-red { color: #ff7b72 !important; font-weight: 700; }
    .muted { color: #8b949e; }
    .footer {
        text-align: center;
        color: #8b949e;
        font-size: 0.9rem;
        padding: 1.5rem 0 0.5rem 0;
        border-top: 1px solid #30363d;
        margin-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">Student ETL Pipeline</div>
        <div class="hero-subtitle">Data Cleaning & Analysis Dashboard</div>
        <div class="hero-badges">
            <span>1. Upload</span>
            <span>2. Check Issues</span>
            <span>3. Run Pipeline</span>
            <span>4. View Results</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

setup_logging(LOG_FILE)


def _save_uploaded_file(uploaded_file) -> Path:
    suffix = Path(uploaded_file.name).suffix.lower() or ".csv"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return Path(tmp.name)


def _prepare_input(uploaded_file, use_sample: bool) -> Path | None:
    if uploaded_file is not None:
        return _save_uploaded_file(uploaded_file)
    if use_sample and RAW_DATA_FILE.exists():
        return RAW_DATA_FILE
    return None


# Sidebar - Input panel
st.sidebar.markdown('<div class="section-label accent-blue">Input Panel</div>', unsafe_allow_html=True)
st.sidebar.caption("Upload your student data file to begin.")
uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
use_sample = st.sidebar.checkbox("Use sample data (from project)", value=False)
if uploaded_file is not None:
    use_sample = False
input_path = _prepare_input(uploaded_file, use_sample)

st.sidebar.markdown("---")
st.sidebar.markdown('<span class="muted">Required columns:</span>', unsafe_allow_html=True)
st.sidebar.code("Student ID, Name, Age, Gender,\nDepartment, Attendance, Marks, Grade", language="text")

if "pipeline_result" not in st.session_state:
    st.session_state["pipeline_result"] = None
if "input_label" not in st.session_state:
    st.session_state["input_label"] = None
if "view_section" not in st.session_state:
    st.session_state["view_section"] = "cleaned"
if "input_sig" not in st.session_state:
    st.session_state["input_sig"] = None

if input_path is None:
    st.session_state["pipeline_result"] = None
    st.session_state["input_label"] = None
    st.session_state["input_sig"] = None
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.info("Upload a CSV/Excel file or select sample data from the sidebar to start.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="footer">Student ETL Pipeline • Python, Pandas, Matplotlib, SQLite</div>', unsafe_allow_html=True)
    st.stop()

if uploaded_file is not None:
    input_sig = ("upload", uploaded_file.name, uploaded_file.size)
    input_label = uploaded_file.name
else:
    input_sig = ("sample", str(input_path))
    input_label = "data/raw/students_raw.csv"

if st.session_state["input_sig"] != input_sig:
    st.session_state["pipeline_result"] = None
    st.session_state["input_label"] = None
    st.session_state["view_section"] = "cleaned"
    st.session_state["input_sig"] = input_sig

st.sidebar.markdown(f'<span class="muted">Selected:</span> <span class="accent-green">{input_label}</span>', unsafe_allow_html=True)

# Extract and profile raw data
try:
    raw_df = extract_data(input_path)
    raw_profile = profile_data(raw_df)
except Exception as exc:
    st.error(f"Could not read/profile input: {exc}")
    st.stop()

# Step 2: Before pipeline
st.markdown('<div class="step-header accent-blue">Step 2: Raw Data Overview</div>', unsafe_allow_html=True)
st.caption("Profile of the uploaded data before cleaning.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total rows", raw_profile["row_count"])
c2.metric("Missing values", raw_profile["total_nulls"])
c3.metric("Duplicate IDs", raw_profile["duplicate_student_ids"])
c4.metric("Exact duplicates", raw_profile["exact_duplicate_rows"])

out_range = raw_profile.get("out_of_range_counts", {})
o1, o2, o3 = st.columns(3)
o1.metric("Out-of-range Marks", out_range.get("Marks", 0))
o2.metric("Out-of-range Attendance", out_range.get("Attendance", 0))
o3.metric("Non-numeric Age", out_range.get("Age_non_numeric", 0))

null_df = pd.DataFrame(
    {"Column": list(raw_profile["null_counts"].keys()), "Missing": list(raw_profile["null_counts"].values())}
)
missing_only = null_df[null_df["Missing"] > 0].sort_values("Missing", ascending=False)

st.markdown('<div class="section-label accent-orange">Missing values by column</div>', unsafe_allow_html=True)
mcol1, mcol2 = st.columns([2, 1])
with mcol1:
    if not missing_only.empty:
        st.bar_chart(missing_only.set_index("Column")["Missing"])
    else:
        st.success("No missing values found.")
with mcol2:
    st.dataframe(null_df, use_container_width=True, hide_index=True, height=280)

with st.expander("Preview raw data (first 50 rows)", expanded=False):
    st.dataframe(raw_df.head(50), use_container_width=True)

st.divider()

# Step 3: Run pipeline
st.markdown('<div class="step-header accent-orange">Step 3: Run Pipeline</div>', unsafe_allow_html=True)
st.caption("Clean, validate, transform, load, analyze, and generate reports.")
run_col, info_col = st.columns([1, 2])
with run_col:
    start_clicked = st.button("Start Pipeline", type="primary", use_container_width=True)
with info_col:
    if st.session_state.get("pipeline_result") is not None:
        st.markdown('<span class="accent-green">Pipeline already run.</span> Click to run again with current input.', unsafe_allow_html=True)

if start_clicked:
    with st.spinner("Running pipeline..."):
        try:
            result = run_pipeline(input_path)
            st.session_state["pipeline_result"] = result
            st.session_state["input_label"] = input_label
            st.success("Pipeline completed successfully.")
        except Exception as exc:
            st.session_state["pipeline_result"] = None
            st.error(f"Pipeline failed: {exc}")

result = st.session_state.get("pipeline_result")
if result is None:
    st.warning("Pipeline not run yet. Click **Start Pipeline** to generate cleaned results.")
    st.markdown('<div class="footer">Student ETL Pipeline • Python, Pandas, Matplotlib, SQLite</div>', unsafe_allow_html=True)
    st.stop()

clean_df = result["clean_df"]
rejected_df = result["rejected_df"]
raw_profile_res = result["raw_profile"]

st.divider()

# Step 4: Results
st.markdown('<div class="step-header accent-green">Step 4: Cleaning Results</div>', unsafe_allow_html=True)
st.caption("Comparison of data before and after the pipeline.")
a1, a2, a3, a4 = st.columns(4)
a1.metric("Rows before", raw_profile_res["row_count"])
a2.metric("Cleaned rows", len(clean_df), delta=len(clean_df) - raw_profile_res["row_count"])
a3.metric("Rejected rows", len(rejected_df))
a4.metric("Missing values now", int(clean_df.isna().sum().sum()), delta=int(clean_df.isna().sum().sum()) - raw_profile_res["total_nulls"])

missing_marks = int(clean_df["Marks"].isna().sum()) if "Marks" in clean_df else 0
attendance_imputed = (
    int(clean_df["data_quality_flag"].astype(str).str.contains("attendance_imputed").sum())
    if "data_quality_flag" in clean_df
    else 0
)
flagged_rows = int((clean_df["data_quality_flag"] != "ok").sum()) if "data_quality_flag" in clean_df else 0

st.markdown('<div class="section-label accent-green">Cleaning actions summary</div>', unsafe_allow_html=True)
s1, s2, s3, s4 = st.columns(4)
s1.metric("Duplicates/invalid rejected", len(rejected_df))
s2.metric("Attendance imputed", attendance_imputed)
s3.metric("Marks left missing (flagged)", missing_marks)
s4.metric("Rows with flags", flagged_rows)

with st.expander("View applied actions", expanded=False):
    summary_df = pd.DataFrame(
        {
            "Action": [
                "Removed duplicates / rejected conflicts & invalid ranges",
                "Standardized names, departments, gender",
                "Imputed missing attendance (department median)",
                "Kept missing/invalid marks as NaN (flagged)",
            ],
            "Status": ["Done", "Done", f"{attendance_imputed} rows", f"{missing_marks} rows"],
        }
    )
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.divider()

# Step 5: Explore
st.markdown('<div class="step-header accent-purple">Step 5: Explore Details</div>', unsafe_allow_html=True)
st.caption("Select a section to view records, charts, or reports.")

btn1, btn2, btn3, btn4 = st.columns(4)
if btn1.button("Show Cleaned Records", use_container_width=True):
    st.session_state["view_section"] = "cleaned"
if btn2.button("Show Rejected Records", use_container_width=True):
    st.session_state["view_section"] = "rejected"
if btn3.button("Show Charts", use_container_width=True):
    st.session_state["view_section"] = "charts"
if btn4.button("Show Reports & Files", use_container_width=True):
    st.session_state["view_section"] = "reports"

view = st.session_state.get("view_section", "cleaned")

if view == "cleaned":
    st.markdown('<div class="section-label accent-green">Cleaned Records</div>', unsafe_allow_html=True)
    st.dataframe(clean_df, use_container_width=True)
    st.download_button("Download cleaned CSV", data=clean_df.to_csv(index=False), file_name="students_clean.csv", mime="text/csv")

elif view == "rejected":
    st.markdown('<div class="section-label accent-red">Rejected Records</div>', unsafe_allow_html=True)
    if rejected_df.empty:
        st.success("No rejected records.")
    else:
        if "rejection_reason" in rejected_df.columns:
            st.markdown('<span class="muted">Rejection reasons:</span>', unsafe_allow_html=True)
            st.dataframe(
                rejected_df["rejection_reason"].value_counts().rename_axis("reason").reset_index(name="count"),
                use_container_width=True,
                hide_index=True,
            )
        st.dataframe(rejected_df, use_container_width=True)
    st.download_button("Download rejected CSV", data=rejected_df.to_csv(index=False), file_name="rejected_records.csv", mime="text/csv")

elif view == "charts":
    st.markdown('<div class="section-label accent-purple">Charts</div>', unsafe_allow_html=True)
    st.caption("Charts are shown one below another for easy viewing.")
    chart_files = [
        ("1. Data quality issues", OUTPUTS_CHARTS_DIR / "data_quality_issues.png"),
        ("2. Grade distribution", OUTPUTS_CHARTS_DIR / "grade_distribution.png"),
        ("3. Average marks by department", OUTPUTS_CHARTS_DIR / "avg_marks_by_department.png"),
        ("4. Attendance vs marks", OUTPUTS_CHARTS_DIR / "attendance_vs_marks.png"),
        ("5. Marks distribution", OUTPUTS_CHARTS_DIR / "marks_distribution.png"),
    ]
    for title, path in chart_files:
        if path.exists():
            st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)
            st.image(str(path), width=700)
            st.write("")

elif view == "reports":
    st.markdown('<div class="section-label accent-blue">Reports & Files</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Output files</div>', unsafe_allow_html=True)
    outputs_df = pd.DataFrame(
        {
            "Output": ["Cleaned CSV", "Rejected CSV", "SQLite DB", "Quality report", "Analysis report", "Charts folder"],
            "Path": [
                str(CLEAN_DATA_FILE),
                str(REJECTED_DATA_FILE),
                "data/processed/students.db (table: students)",
                str(QUALITY_REPORT_FILE),
                str(ANALYSIS_REPORT_FILE),
                str(OUTPUTS_CHARTS_DIR),
            ],
        }
    )
    st.dataframe(outputs_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-label">Data Quality Report</div>', unsafe_allow_html=True)
    if QUALITY_REPORT_FILE.exists():
        with st.expander("Open data quality report", expanded=False):
            st.markdown(QUALITY_REPORT_FILE.read_text(encoding="utf-8"))
    else:
        st.write("Report not found.")

    st.markdown('<div class="section-label">Analysis Summary</div>', unsafe_allow_html=True)
    if ANALYSIS_REPORT_FILE.exists():
        with st.expander("Open analysis summary", expanded=False):
            st.markdown(ANALYSIS_REPORT_FILE.read_text(encoding="utf-8"))
    else:
        st.write("Report not found.")

st.markdown(
    '<div class="footer">Student ETL Pipeline • Built with Python, Pandas, NumPy, Matplotlib & SQLite</div>',
    unsafe_allow_html=True,
)
