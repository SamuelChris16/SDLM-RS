"""
engine/data_ingestion.py
--------------------------
Data Ingestion Module (lihat System Architecture di spesifikasi).

Tanggung jawab modul ini HANYA satu: membaca file mentah (hasil "export
SAP") menjadi DataFrame, dengan parsing tipe data yang benar. Tidak ada
logic bisnis di sini — itu tugas engine lain. Ini prinsip
"separation of concerns" ala aplikasi enterprise.
"""

from __future__ import annotations
import pandas as pd
import config


def load_raw_documents() -> pd.DataFrame:
    df = pd.read_csv(
        config.DOCUMENT_MASTER_CSV,
        parse_dates=["CreatedDate", "LastAccessDate"],
    )
    return df


def load_retention_policy() -> pd.DataFrame:
    return pd.read_csv(config.RETENTION_POLICY_CSV)


def load_access_log() -> pd.DataFrame:
    return pd.read_csv(config.ACCESS_LOG_CSV, parse_dates=["AccessDate"])


def load_users() -> pd.DataFrame:
    return pd.read_csv(config.USERS_CSV)


def load_sites() -> pd.DataFrame:
    return pd.read_csv(config.SITES_CSV)


def load_all() -> dict:
    """Mengembalikan seluruh sumber data mentah dalam satu dict, siap
    divalidasi oleh Data Validation Module."""
    return {
        "documents": load_raw_documents(),
        "retention_policy": load_retention_policy(),
        "access_log": load_access_log(),
        "users": load_users(),
        "sites": load_sites(),
    }
