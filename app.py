"""
app.py
--------
Dashboard utama SDLM-RS (Streamlit).

Cara jalan:
    streamlit run app.py

Prasyarat (jalankan sekali di awal, atau setiap kali data mentah berubah):
    python -m utils.data_generator     # generate data mentah
    python scripts/run_pipeline.py     # proses semua engine -> database

Dashboard ini SENGAJA dibuat simple: 4 KPI utama, 4 chart utama, 1 tabel
eksplorasi dengan filter, dan 1 halaman workflow approval sederhana.
Tidak dibuat kompleks berlebihan supaya tetap "mudah diinterpretasikan"
sesuai request awal.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

import config
from utils import db_utils
from dashboard import components

st.set_page_config(
    page_title="SDLM-RS | PT Saptaindra Sejati (JAHO)",
    page_icon="🗂️",
    layout="wide",
)


# ---------------------------------------------------------------------
# DATA LOADING (cached supaya dashboard responsif)
# ---------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_recommendation_data() -> pd.DataFrame:
    df = db_utils.load_table("recommendation_output")
    df["CreatedDate"] = pd.to_datetime(df["CreatedDate"])
    df["LastAccessDate"] = pd.to_datetime(df["LastAccessDate"])
    return df


def load_approval_status() -> pd.DataFrame:
    return db_utils.load_latest_approval_status()

if not os.path.exists("database/sqlite.db"):
    from utils.data_generator import generate_database
    generate_database()

if not config.DATABASE_PATH.exists():
    st.error(
        "Database belum ada. Jalankan dulu di terminal:\n\n"
        "1. `python -m utils.data_generator`\n"
        "2. `python scripts/run_pipeline.py`\n\n"
        "Setelah itu, refresh halaman ini."
    )
    st.stop()

df = load_recommendation_data()

# ---------------------------------------------------------------------
# SIDEBAR — FILTER
# ---------------------------------------------------------------------
st.sidebar.title("🗂️ SDLM-RS")
st.sidebar.caption("Smart Data Lifecycle Management Recommendation System\n\nPT Saptaindra Sejati (JAHO)")
st.sidebar.markdown("---")
st.sidebar.subheader("Filter")

site_filter = st.sidebar.multiselect("Site", sorted(df["Site"].unique()), default=list(df["Site"].unique()))
dept_filter = st.sidebar.multiselect("Departemen", sorted(df["Department"].unique()), default=list(df["Department"].unique()))
rec_filter = st.sidebar.multiselect("Rekomendasi", sorted(df["Recommendation"].unique()), default=list(df["Recommendation"].unique()))
risk_filter = st.sidebar.multiselect("Risk Category", ["Low", "Medium", "High", "Critical"], default=["Low", "Medium", "High", "Critical"])

filtered_df = df[
    df["Site"].isin(site_filter)
    & df["Department"].isin(dept_filter)
    & df["Recommendation"].isin(rec_filter)
    & df["RiskCategory"].isin(risk_filter)
].copy()

st.sidebar.markdown("---")
st.sidebar.caption(f"Simulation date: **{config.SIMULATION_DATE}**")
st.sidebar.caption(f"Menampilkan **{len(filtered_df):,}** dari **{len(df):,}** dokumen")

# ---------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------
tab_overview, tab_explorer, tab_approval, tab_reports = st.tabs(
    ["📊 Overview", "🔍 Document Explorer", "✅ Approval Workflow", "📁 Reports"]
)

# =======================================================================
# TAB 1 — OVERVIEW
# =======================================================================
with tab_overview:
    st.subheader("Ringkasan Data Lifecycle Management")

    kpis = components.kpi_values(filtered_df)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Dokumen", f"{kpis['Total Dokumen']:,}")
    c2.metric("Expired", f"{kpis['Expired']:,}")
    c3.metric("Archive Candidate", f"{kpis['Archive Candidate']:,}")
    c4.metric("Delete Candidate", f"{kpis['Delete Candidate']:,}")
    c5.metric("Review Candidate", f"{kpis['Review Candidate']:,}")
    c6.metric("Storage Used", f"{kpis['Storage Used (GB)']:,} GB")

    st.markdown("")
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        st.plotly_chart(components.chart_by_site(filtered_df), use_container_width=True)
    with row1_col2:
        st.plotly_chart(components.chart_by_department(filtered_df), use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        st.plotly_chart(components.chart_lifecycle_status(filtered_df), use_container_width=True)
    with row2_col2:
        st.plotly_chart(components.chart_risk_distribution(filtered_df), use_container_width=True)

# =======================================================================
# TAB 2 — DOCUMENT EXPLORER
# =======================================================================
with tab_explorer:
    st.subheader("Eksplorasi & Pencarian Dokumen")

    search_term = st.text_input("Cari nama dokumen / owner", "")
    display_df = filtered_df.copy()
    if search_term:
        mask = (
            display_df["DocumentName"].str.contains(search_term, case=False, na=False)
            | display_df["Owner"].str.contains(search_term, case=False, na=False)
        )
        display_df = display_df[mask]

    st.dataframe(
        display_df[[
            "DocumentID", "DocumentName", "Site", "Department", "DocumentType",
            "Classification", "DocumentAgeYears", "RiskScore", "RiskCategory",
            "Recommendation", "Reason",
        ]].sort_values("RiskScore", ascending=False),
        use_container_width=True,
        height=420,
    )

    st.markdown("#### Detail Dokumen")
    selected_id = st.selectbox("Pilih DocumentID untuk melihat detail lengkap", display_df["DocumentID"].tolist())
    if selected_id:
        record = df[df["DocumentID"] == selected_id].iloc[0]
        d1, d2, d3 = st.columns(3)
        d1.write(f"**Nama:** {record['DocumentName']}")
        d1.write(f"**Site / Dept:** {record['Site']} / {record['Department']}")
        d1.write(f"**Tipe:** {record['DocumentType']}")
        d2.write(f"**Klasifikasi:** {record['Classification']}")
        d2.write(f"**Umur Dokumen:** {record['DocumentAgeYears']} tahun")
        d2.write(f"**Retention Policy:** {record['RetentionYear']} tahun")
        d3.write(f"**Risk Score:** {record['RiskScore']} ({record['RiskCategory']})")
        d3.write(f"**Rekomendasi:** {record['Recommendation']}")
        d3.write(f"**Alasan:** {record['Reason']}")

# =======================================================================
# TAB 3 — APPROVAL WORKFLOW (JAHO Data Governance Review)
# =======================================================================
with tab_approval:
    st.subheader("Workflow Approval — JAHO Data Governance Review")
    st.caption(
        "Mensimulasikan tahap review manusia sebelum eksekusi ke SAP. "
        "Sistem TIDAK mengubah data SAP secara langsung — keputusan di sini "
        "hanya tercatat sebagai rekomendasi keputusan (decision log)."
    )

    approval_status_df = load_approval_status()
    pending_df = df[df["Recommendation"].isin(["REVIEW", "DELETE"])].copy()
    if not approval_status_df.empty:
        pending_df = pending_df.merge(
            approval_status_df[["DocumentID", "Decision", "Reviewer", "DecisionDate"]],
            on="DocumentID", how="left",
        )
    else:
        pending_df["Decision"] = None

    pending_df["Decision"] = pending_df["Decision"].fillna("Pending")

    colf1, colf2 = st.columns([1, 3])
    with colf1:
        status_filter = st.radio("Tampilkan", ["Pending", "Sudah Diputuskan", "Semua"], index=0)

    if status_filter == "Pending":
        view_df = pending_df[pending_df["Decision"] == "Pending"]
    elif status_filter == "Sudah Diputuskan":
        view_df = pending_df[pending_df["Decision"] != "Pending"]
    else:
        view_df = pending_df

    st.dataframe(
        view_df[["DocumentID", "DocumentName", "Site", "Classification", "Recommendation", "Reason", "Decision"]],
        use_container_width=True,
        height=300,
    )

    st.markdown("#### Input Keputusan Review")
    with st.form("approval_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)
        doc_choice = f1.selectbox("DocumentID", pending_df["DocumentID"].tolist())
        decision_choice = f2.selectbox("Keputusan", ["Approved", "Rejected"])
        reviewer_name = f3.text_input("Nama Reviewer (JAHO Data Governance)")
        comment = st.text_area("Catatan (opsional)")
        submitted = st.form_submit_button("Simpan Keputusan")

        if submitted:
            if not reviewer_name.strip():
                st.warning("Nama reviewer wajib diisi.")
            else:
                rec_value = df.loc[df["DocumentID"] == doc_choice, "Recommendation"].iloc[0]
                db_utils.insert_approval_decision(
                    document_id=int(doc_choice),
                    recommendation=rec_value,
                    decision=decision_choice,
                    reviewer=reviewer_name.strip(),
                    comment=comment.strip(),
                    decision_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                st.success(f"Keputusan '{decision_choice}' untuk DocumentID {doc_choice} tersimpan.")
                st.rerun()

# =======================================================================
# TAB 4 — REPORTS
# =======================================================================
with tab_reports:
    st.subheader("Unduh Recommendation Report")
    st.caption("Report ini adalah decision support untuk JAHO — bukan eksekusi otomatis ke SAP.")

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        filtered_df.to_excel(writer, sheet_name="Recommendation Detail", index=False)
        filtered_df.groupby("Recommendation").size().rename("DocumentCount").reset_index().to_excel(
            writer, sheet_name="Summary", index=False
        )
    st.download_button(
        "⬇️ Download Excel Report (sesuai filter aktif)",
        data=buffer.getvalue(),
        file_name=f"SDLM_Recommendation_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("---")
    st.markdown("#### Data Validation Report (hasil pipeline terakhir)")
    if config.VALIDATION_REPORT_CSV.exists():
        st.dataframe(pd.read_csv(config.VALIDATION_REPORT_CSV), use_container_width=True)
    else:
        st.info("Belum ada validation report. Jalankan scripts/run_pipeline.py terlebih dahulu.")
