"""
utils/db_utils.py
-------------------
Helper untuk operasi SQLite. Dipakai oleh pipeline (scripts/run_pipeline.py)
dan dashboard (app.py) supaya keduanya membaca dari SUMBER YANG SAMA
(database, bukan file CSV terpisah-pisah). Ini penting untuk konsistensi
data ala aplikasi enterprise sungguhan.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
import pandas as pd

import config


@contextmanager
def get_connection():
    config.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()


def save_dataframe(df: pd.DataFrame, table_name: str, if_exists: str = "replace") -> None:
    with get_connection() as conn:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)


def load_table(table_name: str) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn)


def table_exists(table_name: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        )
        return cur.fetchone() is not None


def init_approval_log_table() -> None:
    """
    Tabel approval_log merepresentasikan workflow persetujuan JAHO Data
    Governance yang disebut di spesifikasi ("Nilai tambah" - workflow
    approval). Dibuat idempotent (aman dipanggil berulang kali).
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_log (
                ApprovalID INTEGER PRIMARY KEY AUTOINCREMENT,
                DocumentID INTEGER NOT NULL,
                Recommendation TEXT,
                Decision TEXT NOT NULL,
                Reviewer TEXT NOT NULL,
                Comment TEXT,
                DecisionDate TEXT NOT NULL
            )
            """
        )
        conn.commit()


def insert_approval_decision(document_id: int, recommendation: str, decision: str,
                              reviewer: str, comment: str, decision_date: str) -> None:
    init_approval_log_table()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO approval_log (DocumentID, Recommendation, Decision, Reviewer, Comment, DecisionDate)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, recommendation, decision, reviewer, comment, decision_date),
        )
        conn.commit()


def load_latest_approval_status() -> pd.DataFrame:
    """
    Mengambil status approval TERBARU per DocumentID (kalau sebuah dokumen
    di-review lebih dari sekali, ambil keputusan paling akhir).
    """
    init_approval_log_table()
    with get_connection() as conn:
        try:
            df = pd.read_sql(
                """
                SELECT a.*
                FROM approval_log a
                INNER JOIN (
                    SELECT DocumentID, MAX(ApprovalID) AS max_id
                    FROM approval_log
                    GROUP BY DocumentID
                ) latest
                ON a.DocumentID = latest.DocumentID AND a.ApprovalID = latest.max_id
                """,
                conn,
            )
        except Exception:
            df = pd.DataFrame(columns=[
                "ApprovalID", "DocumentID", "Recommendation", "Decision",
                "Reviewer", "Comment", "DecisionDate"
            ])
        return df
