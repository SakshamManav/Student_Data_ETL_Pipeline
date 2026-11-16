"""Streamlit UI for Student Data ETL Pipeline.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from main import run_pipeline, setup_logging
from src.config import (
    ANALYSIS_REPORT_FILE,
    BASE_DIR,
    CLEAN_AUDIT_DATA_FILE,
    CLEAN_DATA_FILE,
    LOG_FILE,
    OUTPUTS_CHARTS_DIR,
    QUALITY_REPORT_FILE,
    RAW_DATA_FILE,
    REJECTED_DATA_FILE,
    REQUIRED_COLUMNS,
    SQLITE_AUDIT_TABLE,
    SQLITE_DB_FILE,
    SQLITE_TABLE,
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


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to Excel bytes for download."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return buffer.getvalue()


def _relative_path(path: Path) -> str:
    """Return a project-relative path when possible."""
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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
    st.session_state["view_section"] = "cleaned"
    st.session_state.pop("view_selector", None)
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
    st.session_state.pop("view_selector", None)
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
missing_before = int(
    sum(int(raw_profile["null_counts"].get(col, 0)) for col in REQUIRED_COLUMNS)
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total rows", raw_profile["row_count"])
c2.metric("Missing values (original columns)", missing_before)
c3.metric("Duplicate IDs", raw_profile["duplicate_student_ids"])
c4.metric("Exact duplicates", raw_profile["exact_duplicate_rows"])

out_range = raw_profile.get("out_of_range_counts", {})
o1, o2, o3, o4 = st.columns(4)
o1.metric("Missing Student IDs", raw_profile.get("missing_student_ids", 0))
o2.metric("Out-of-range Marks", out_range.get("Marks", 0))
o3.metric("Out-of-range Attendance", out_range.get("Attendance", 0))
o4.metric("Non-numeric Age", out_range.get("Age_non_numeric", 0))

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

row_removed = (
    int((rejected_df["action"] == "row_removed").sum())
    if "action" in rejected_df.columns
    else 0
)
values_invalidated = (
    int((rejected_df["action"] == "value_invalidated").sum())
    if "action" in rejected_df.columns
    else 0
)
original_cols = [col for col in REQUIRED_COLUMNS if col in clean_df.columns]
missing_before = int(
    sum(int(raw_profile_res["null_counts"].get(col, 0)) for col in REQUIRED_COLUMNS)
)
missing_after = int(clean_df[original_cols].isna().sum().sum())
derived_not_computed = (
    int(clean_df["Grade_Computed"].isna().sum()) if "Grade_Computed" in clean_df else 0
)
rows_before = int(raw_profile_res["row_count"])

a1, a2, a3, a4, a5 = st.columns(5)
a1.metric("Rows before", rows_before)
a2.metric("Rows removed (duplicates)", row_removed)
a3.metric("Values invalidated and flagged", values_invalidated)
a4.metric("Cleaned rows", len(clean_df))
a5.metric(
    "Missing values (original columns)",
    f"{missing_before} -> {missing_after}",
    delta=missing_after - missing_before,
    delta_color="inverse",
)
st.caption(
    f"Derived fields not computed (marks missing): {derived_not_computed} rows"
)
st.markdown(
    f'<span class="muted">Reconciliation:</span> '
    f'<span class="accent-blue">{rows_before}</span> rows before − '
    f'<span class="accent-red">{row_removed}</span> rows removed = '
    f'<span class="accent-green">{len(clean_df)}</span> cleaned rows',
    unsafe_allow_html=True,
)

missing_marks = int(clean_df["Marks"].isna().sum()) if "Marks" in clean_df else 0
attendance_imputed = (
    int(clean_df["data_quality_flag"].astype(str).str.contains("attendance_imputed").sum())
    if "data_quality_flag" in clean_df
    else 0
)

st.markdown('<div class="section-label accent-green">Cleaning actions summary</div>', unsafe_allow_html=True)
s1, s2, s3, s4 = st.columns(4)
s1.metric("Rows removed (duplicates)", row_removed)
s2.metric("Values invalidated and flagged", values_invalidated)
s3.metric("Attendance imputed", attendance_imputed)
s4.metric("Marks left missing (flagged)", missing_marks)

with st.expander("View applied actions", expanded=False):
    summary_df = pd.DataFrame(
        {
            "Action": [
                "Removed duplicate rows",
                "Invalidated and flagged out-of-range values",
                "Standardized names, departments, gender, grades",
                "Parsed attendance '%' values and age text suffixes",
                "Imputed missing/unparseable attendance (department median)",
                "Kept missing/invalid marks as NaN (flagged)",
            ],
            "Status": [
                f"{row_removed} rows",
                f"{values_invalidated} values",
                "Done",
                "Done",
                f"{attendance_imputed} rows",
                f"{missing_marks} rows",
            ],
        }
    )
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.divider()

# Step 5: Explore
st.markdown('<div class="step-header accent-purple">Step 5: Explore Details</div>', unsafe_allow_html=True)
st.caption("Select a section to view records, charts, or reports.")

view = st.session_state.get("view_section", "cleaned")
view_options = {
    "Cleaned Records": "cleaned",
    "Rejected Records": "rejected",
    "Charts": "charts",
    "Reports & Files": "reports",
}
current_label = next(
    (label for label, key in view_options.items() if key == view),
    "Cleaned Records",
)
selected_label = st.segmented_control(
    "View section",
    options=list(view_options.keys()),
    default=current_label,
    key="view_selector",
    label_visibility="collapsed",
)
if selected_label is None:
    selected_label = current_label
view = view_options[selected_label]
st.session_state["view_section"] = view

if view == "cleaned":
    st.markdown('<div class="section-label accent-green">Cleaned Records</div>', unsafe_allow_html=True)
    st.dataframe(clean_df, use_container_width=True)

    clean_download_df = (
        clean_df.drop(columns=["data_quality_flag"])
        if "data_quality_flag" in clean_df.columns
        else clean_df.copy()
    )
    st.caption("Download CSV or Excel, with or without audit flags.")
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Cleaned data (CSV)",
            data=clean_download_df.to_csv(index=False),
            file_name="students_clean.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "Cleaned data with audit flags (CSV)",
            data=clean_df.to_csv(index=False),
            file_name="students_clean_audit.csv",
            mime="text/csv",
            use_container_width=True,
        )

    dl3, dl4 = st.columns(2)
    with dl3:
        st.download_button(
            "Cleaned data (Excel)",
            data=_to_excel_bytes(clean_download_df),
            file_name="students_clean.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with dl4:
        st.download_button(
            "Cleaned data with audit flags (Excel)",
            data=_to_excel_bytes(clean_df),
            file_name="students_clean_audit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

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
    rdl1, rdl2 = st.columns(2)
    with rdl1:
        st.download_button(
            "Download rejected CSV",
            data=rejected_df.to_csv(index=False),
            file_name="rejected_records.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with rdl2:
        st.download_button(
            "Download rejected Excel",
            data=_to_excel_bytes(rejected_df),
            file_name="rejected_records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

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
            "Output": [
                "Cleaned CSV (no audit flag)",
                "Cleaned CSV (audit flags)",
                "Rejected CSV",
                "SQLite DB",
                "Quality report",
                "Analysis report",
                "Charts folder",
            ],
            "Path": [
                _relative_path(CLEAN_DATA_FILE),
                _relative_path(CLEAN_AUDIT_DATA_FILE),
                _relative_path(REJECTED_DATA_FILE),
                f"{_relative_path(SQLITE_DB_FILE)} (tables: {SQLITE_TABLE}, {SQLITE_AUDIT_TABLE})",
                _relative_path(QUALITY_REPORT_FILE),
                _relative_path(ANALYSIS_REPORT_FILE),
                _relative_path(OUTPUTS_CHARTS_DIR),
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
