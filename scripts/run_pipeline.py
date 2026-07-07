"""
scripts/run_pipeline.py
--------------------------
Orchestrator end-to-end, merepresentasikan "batch job" yang di dunia
nyata akan dijalankan terjadwal (mis. tiap malam) setelah export data
dari SAP tersedia.

Alur (sesuai System Architecture di spesifikasi):

    SAP Export (CSV)
        -> Data Ingestion Module
        -> Data Validation Module
        -> Data Classification Engine
        -> Retention Rule Engine
        -> Risk Scoring Engine
        -> Lifecycle Recommendation
        -> simpan ke SQLite + reports/recommendation_report.xlsx

Cara jalan:
    python scripts/run_pipeline.py

Pastikan data mentah sudah ada (kalau belum, jalankan dulu):
    python -m utils.data_generator
"""

from __future__ import annotations

import sys
from pathlib import Path

# Supaya script ini bisa dijalankan langsung (python scripts/run_pipeline.py)
# maupun sebagai module, root project selalu ditambahkan ke sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

import config
from engine import data_ingestion, data_validation, classification_engine
from engine import retention_engine, risk_engine, lifecycle_engine
from utils import db_utils


REPORT_COLUMNS = [
    "DocumentID", "DocumentName", "Site", "Department", "DocumentType",
    "Classification", "Owner", "CreatedDate", "LastAccessDate",
    "DocumentAgeYears", "RetentionYear", "Expired", "ArchiveDue", "DeleteDue",
    "DistinctUserCount", "RiskScore", "RiskCategory",
    "Recommendation", "Reason", "Reviewer", "Approval", "StorageLocation", "SizeMB",
]


def run() -> pd.DataFrame:
    print("=" * 70)
    print("SDLM-RS PIPELINE — Smart Data Lifecycle Management Recommendation")
    print(f"Simulation date: {config.SIMULATION_DATE}")
    print("=" * 70)

    # 1) INGESTION -----------------------------------------------------
    print("\n[STEP 1] Data Ingestion Module")
    raw = data_ingestion.load_all()
    for name, df in raw.items():
        print(f"    - {name:<18}: {len(df):,} baris")

    # 2) VALIDATION ------------------------------------------------------
    print("\n[STEP 2] Data Validation Module")
    clean_docs, exception_docs, validation_report = data_validation.validate_and_clean_documents(
        raw["documents"], raw["retention_policy"]
    )
    data_validation.save_validation_report(validation_report)
    print(f"    - Dokumen valid untuk diproses : {len(clean_docs):,}")
    print(f"    - Dokumen exception (dikeluarkan): {len(exception_docs):,}")
    if not validation_report.empty:
        for _, r in validation_report.iterrows():
            print(f"      [{r['severity']}] {r['check']}: {r['count']} baris -> {r['action']}")

    # 3) CLASSIFICATION ----------------------------------------------------
    print("\n[STEP 3] Data Classification Engine")
    classified_docs = classification_engine.classify_documents(clean_docs, raw["retention_policy"])
    auto_filled = int((classified_docs["ClassificationSource"] == "AUTO_FILLED").sum())
    auto_corrected = int((classified_docs["ClassificationSource"] == "AUTO_CORRECTED").sum())
    print(f"    - Classification auto-filled   : {auto_filled:,}")
    print(f"    - Classification auto-corrected: {auto_corrected:,}")

    # 4) RETENTION RULE ENGINE ---------------------------------------------
    print("\n[STEP 4] Retention Rule Engine")
    retained_docs = retention_engine.apply_retention_rules(classified_docs, raw["retention_policy"])
    print(f"    - Expired    : {int(retained_docs['Expired'].sum()):,}")
    print(f"    - Archive due: {int(retained_docs['ArchiveDue'].sum()):,}")
    print(f"    - Delete due : {int(retained_docs['DeleteDue'].sum()):,}")

    # 5) RISK SCORING ENGINE -------------------------------------------------
    print("\n[STEP 5] Risk Scoring Engine")
    scored_docs = risk_engine.compute_risk_scores(retained_docs, raw["access_log"])
    print(scored_docs["RiskCategory"].value_counts().to_string())

    # 6) LIFECYCLE RECOMMENDATION ---------------------------------------------
    print("\n[STEP 6] Lifecycle Recommendation Engine")
    final_docs = lifecycle_engine.generate_recommendations(scored_docs)
    print(final_docs["Recommendation"].value_counts().to_string())

    # 7) PERSIST -------------------------------------------------------------
    print("\n[STEP 7] Menyimpan hasil ke database & report")
    db_utils.save_dataframe(raw["documents"], "raw_documents")
    db_utils.save_dataframe(raw["retention_policy"], "retention_policy")
    db_utils.save_dataframe(raw["access_log"], "access_log")
    db_utils.save_dataframe(raw["users"], "users")
    db_utils.save_dataframe(raw["sites"], "sites")
    db_utils.save_dataframe(exception_docs, "exception_documents")
    db_utils.save_dataframe(final_docs[REPORT_COLUMNS], "recommendation_output")
    db_utils.init_approval_log_table()

    export_excel_report(final_docs[REPORT_COLUMNS])

    print(f"\nSelesai. Database: {config.DATABASE_PATH}")
    print(f"Report Excel     : {config.RECOMMENDATION_REPORT_XLSX}")
    return final_docs


def export_excel_report(df: pd.DataFrame) -> None:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary = (
        df.groupby("Recommendation")
        .size()
        .rename("DocumentCount")
        .reset_index()
        .sort_values("DocumentCount", ascending=False)
    )

    with pd.ExcelWriter(config.RECOMMENDATION_REPORT_XLSX, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Recommendation Detail", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)

        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1F4E78", "font_color": "white", "border": 1
        })
        for sheet_name, sheet_df in [("Recommendation Detail", df), ("Summary", summary)]:
            ws = writer.sheets[sheet_name]
            for col_idx, col_name in enumerate(sheet_df.columns):
                ws.write(0, col_idx, col_name, header_fmt)
                width = max(14, min(38, int(sheet_df[col_name].astype(str).str.len().mean() + 4)))
                ws.set_column(col_idx, col_idx, width)


def generate_database():
    main()
    
if __name__ == "__main__":
    run()
