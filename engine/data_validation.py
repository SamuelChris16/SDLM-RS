"""
engine/data_validation.py
----------------------------
Data Validation Module.

Data hasil export dari sistem sumber (SAP) di dunia nyata JARANG bersih
100%. Modul ini mendeteksi & menangani masalah data umum sebelum masuk ke
engine klasifikasi/retensi/risiko, supaya rekomendasi yang dihasilkan
tidak salah karena data kotor:

    1. DocumentID duplikat          -> dibuang (ambil kemunculan pertama)
    2. CreatedDate kosong/tidak valid -> dokumen tidak bisa dihitung umurnya,
                                          dipisah ke laporan exception
    3. DocumentType yang tidak dikenal retention policy-nya -> exception
    4. Site tidak dikenal            -> exception

Semua temuan dicatat ke sebuah "validation report" (list of dict) yang
nantinya diekspor sebagai reports/data_validation_report.csv — supaya
proses ini AUDITABLE, bukan silent-cleaning yang tidak bisa dipertanggung-
jawabkan (penting untuk aplikasi tata kelola data).
"""

from __future__ import annotations
import pandas as pd
import config


def validate_and_clean_documents(documents_df: pd.DataFrame, retention_policy_df: pd.DataFrame):
    issues = []
    df = documents_df.copy()

    # --- 1. Duplicate DocumentID -------------------------------------
    dup_mask = df.duplicated(subset="DocumentID", keep="first")
    n_dup = int(dup_mask.sum())
    if n_dup:
        issues.append({
            "check": "duplicate_document_id",
            "severity": "WARNING",
            "count": n_dup,
            "action": "Baris duplikat dibuang, hanya kemunculan pertama yang dipakai.",
        })
    df = df.loc[~dup_mask].copy()

    # --- 2. Missing / invalid CreatedDate -----------------------------
    invalid_created = df["CreatedDate"].isna()
    n_invalid_created = int(invalid_created.sum())
    if n_invalid_created:
        issues.append({
            "check": "missing_created_date",
            "severity": "ERROR",
            "count": n_invalid_created,
            "action": "Dokumen dikeluarkan dari proses scoring (umur tidak bisa dihitung), masuk exception list.",
        })
    exception_df = df.loc[invalid_created].copy()
    df = df.loc[~invalid_created].copy()

    # --- 3. DocumentType tidak dikenal retention policy ----------------
    known_types = set(retention_policy_df["DocumentType"].unique())
    unknown_type_mask = ~df["DocumentType"].isin(known_types)
    n_unknown_type = int(unknown_type_mask.sum())
    if n_unknown_type:
        issues.append({
            "check": "unknown_document_type",
            "severity": "ERROR",
            "count": n_unknown_type,
            "action": "Dokumen dengan DocumentType tanpa kebijakan retensi dikeluarkan ke exception list.",
        })
    exception_df = pd.concat([exception_df, df.loc[unknown_type_mask]], ignore_index=True)
    df = df.loc[~unknown_type_mask].copy()

    # --- 4. Site tidak dikenal ------------------------------------------
    unknown_site_mask = ~df["Site"].isin(config.SITES)
    n_unknown_site = int(unknown_site_mask.sum())
    if n_unknown_site:
        issues.append({
            "check": "unknown_site",
            "severity": "ERROR",
            "count": n_unknown_site,
            "action": "Dokumen dengan Site tidak dikenal dikeluarkan ke exception list.",
        })
    exception_df = pd.concat([exception_df, df.loc[unknown_site_mask]], ignore_index=True)
    df = df.loc[~unknown_site_mask].copy()

    # --- 5. Missing Classification (bukan error — akan diisi Classification Engine)
    n_missing_classification = int(df["Classification"].isna().sum())
    if n_missing_classification:
        issues.append({
            "check": "missing_classification",
            "severity": "INFO",
            "count": n_missing_classification,
            "action": "Akan diisi otomatis oleh Classification Engine berdasarkan DocumentType.",
        })

    # --- 6. LastAccessDate lebih awal dari CreatedDate (data anomali) ---
    bad_access_mask = df["LastAccessDate"].notna() & (df["LastAccessDate"] < df["CreatedDate"])
    n_bad_access = int(bad_access_mask.sum())
    if n_bad_access:
        issues.append({
            "check": "last_access_before_created",
            "severity": "WARNING",
            "count": n_bad_access,
            "action": "LastAccessDate dianggap tidak valid, diperlakukan sebagai 'belum pernah diakses'.",
        })
        df.loc[bad_access_mask, "LastAccessDate"] = pd.NaT

    report_df = pd.DataFrame(issues, columns=["check", "severity", "count", "action"])

    return df.reset_index(drop=True), exception_df.reset_index(drop=True), report_df


def save_validation_report(report_df: pd.DataFrame) -> None:
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(config.VALIDATION_REPORT_CSV, index=False)
