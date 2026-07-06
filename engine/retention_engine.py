"""
engine/retention_engine.py
------------------------------
Retention Engine (Engine 1 pada spesifikasi).

Input : CreatedDate, Retention Policy, Current Date (SIMULATION_DATE)
Output: DocumentAgeYears, Expired (YES/NO), ArchiveDue (YES/NO), DeleteDue (YES/NO)

Pseudo asli dari spesifikasi:
    IF CurrentDate > CreatedDate + Retention -> Expired

Di implementasi ini logika yang sama dipecah menjadi tiga ambang batas
(bukan cuma satu) supaya lebih dekat ke kebutuhan nyata siklus hidup
dokumen: kapan mulai dipertimbangkan untuk archive, dan kapan sudah boleh
dihapus.
"""

from __future__ import annotations
import pandas as pd
import config


def apply_retention_rules(documents_df: pd.DataFrame, retention_policy_df: pd.DataFrame) -> pd.DataFrame:
    df = documents_df.copy()

    policy_cols = ["DocumentType", "ArchiveAfter", "DeleteAfter", "NeedApproval", "BusinessCritical"]
    df = df.merge(retention_policy_df[policy_cols], on="DocumentType", how="left")

    simulation_date = pd.Timestamp(config.SIMULATION_DATE)
    age_days = (simulation_date - df["CreatedDate"]).dt.days
    df["DocumentAgeYears"] = (age_days / 365.25).round(2)

    df["Expired"] = df["DocumentAgeYears"] > df["RetentionYear"]
    df["ArchiveDue"] = df["DocumentAgeYears"] >= df["ArchiveAfter"]
    df["DeleteDue"] = df["DocumentAgeYears"] >= df["DeleteAfter"]
    df["OverdueYears"] = (df["DocumentAgeYears"] - df["RetentionYear"]).clip(lower=0).round(2)

    return df
