"""
engine/classification_engine.py
----------------------------------
Classification Engine (Engine 2 pada spesifikasi).

Tugas: memastikan SETIAP dokumen punya Classification yang valid dan
konsisten dengan kebijakan (Restricted / Confidential / Internal / Public),
berdasarkan DocumentType-nya.

Kenapa perlu engine terpisah kalau data sudah ada kolom Classification?
Karena di dunia nyata data SAP sering punya klasifikasi yang kosong atau
tidak konsisten (typo, human error saat input). Engine ini men-standardisasi
ulang berdasarkan master kebijakan (retention_policy), bukan sekadar
mempercayai apa yang tertulis di kolom mentah.
"""

from __future__ import annotations
import pandas as pd


def classify_documents(documents_df: pd.DataFrame, retention_policy_df: pd.DataFrame) -> pd.DataFrame:
    df = documents_df.copy()

    type_to_classification = retention_policy_df.set_index("DocumentType")["Classification"].to_dict()

    standardized = df["DocumentType"].map(type_to_classification)

    # Kalau kolom Classification asli kosong ATAU tidak konsisten dengan
    # kebijakan resmi, timpa dengan hasil mapping resmi. Ini yang membuat
    # engine ini benar-benar "melakukan sesuatu", bukan sekadar copy kolom.
    mismatch_mask = df["Classification"].fillna("__MISSING__") != standardized.fillna("__MISSING__")

    df["ClassificationSource"] = "ORIGINAL"
    df.loc[df["Classification"].isna(), "ClassificationSource"] = "AUTO_FILLED"
    df.loc[mismatch_mask & df["Classification"].notna(), "ClassificationSource"] = "AUTO_CORRECTED"

    df["Classification"] = standardized

    return df
