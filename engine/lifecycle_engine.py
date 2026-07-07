from __future__ import annotations
import pandas as pd


def _recommend_row(row) -> tuple[str, str]:
    if bool(row.get("BusinessCritical")):
        return "KEEP", "Dokumen bersifat business critical untuk operasional site."

    if row["DeleteDue"]:
        if row["Classification"] in ("Restricted", "Confidential") or row["NeedApproval"] == "YES":
            return (
                "REVIEW",
                "Masa retensi telah berakhir, namun klasifikasi sensitif/memerlukan "
                "persetujuan sebelum dihapus.",
            )
        return "DELETE", "Masa retensi telah berakhir dan dokumen tidak lagi diperlukan."

    if row["ArchiveDue"]:
        low_access = pd.isna(row["LastAccessDate"]) or row["AccessFrequencyScore"] >= 8
        if low_access:
            return "ARCHIVE", "Telah melewati periode aktif dan jarang/tidak pernah diakses."
        return "KEEP", "Telah melewati periode aktif namun masih sering diakses."

    return "KEEP", "Masih dalam masa retensi aktif."


def generate_recommendations(documents_df: pd.DataFrame) -> pd.DataFrame:
    df = documents_df.copy()
    results = df.apply(_recommend_row, axis=1, result_type="expand")
    df["Recommendation"] = results[0]
    df["Reason"] = results[1]

    # Kolom pendukung report akhir (workflow approval, lihat spesifikasi)
    df["Reviewer"] = ""
    df["Approval"] = df["Recommendation"].apply(
        lambda r: "Pending" if r in ("REVIEW", "DELETE") else "Not Required"
    )

    return df
