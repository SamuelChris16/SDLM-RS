"""
utils/data_generator.py
------------------------
Generator data dummy yang MENYERUPAI kondisi nyata perusahaan tambang
(PT Saptaindra Sejati - JAHO) dengan 3 site: MACO, ADMO, SERA.

Kenapa data dibuat "kotor" sebagian (missing value, duplikat, dsb)?
Karena di dunia nyata, hasil export dari SAP hampir tidak pernah 100%
bersih. Ini sengaja dibuat supaya Data Validation Module (engine/data_validation.py)
punya sesuatu yang nyata untuk divalidasi — bukan cuma dekorasi kode.

Jalankan langsung:
    python -m utils.data_generator
"""

from __future__ import annotations

import random
import numpy as np
import pandas as pd
from faker import Faker

import config

fake = Faker("id_ID")
random.seed(config.RANDOM_SEED)
np.random.seed(config.RANDOM_SEED)
Faker.seed(config.RANDOM_SEED)


# =======================================================================
# 1. MASTER REFERENSI: JENIS DOKUMEN -> (departemen, klasifikasi, retensi)
# =======================================================================
# Retention Year mengacu ke "berapa lama dokumen WAJIB disimpan" sesuai
# kebijakan Data Lifecycle Management perusahaan.
# ArchiveAfter = umur (tahun) saat dokumen mulai layak dipindah ke archive.
# DeleteAfter  = umur (tahun) saat dokumen boleh dihapus (retention selesai).
DOCUMENT_TYPE_POLICY = [
    # DocumentType,              Department,  Classification, RetentionYear, ArchiveAfter, DeleteAfter, NeedApproval, BusinessCritical
    ("Payroll",                  "HR",        "Restricted",   10, 5, 10, "YES", False),
    ("Employment Contract",      "HR",        "Confidential", 10, 5, 10, "YES", False),
    ("Training Record",          "HR",        "Internal",      5, 3, 5,  "NO",  False),
    ("Vendor Contract",          "SCM",       "Confidential",  7, 4, 7,  "YES", False),
    ("Purchase Order",           "SCM",       "Internal",      7, 3, 7,  "NO",  False),
    ("Invoice",                  "Finance",   "Internal",     10, 5, 10, "YES", False),
    ("Tax Document",             "Finance",   "Restricted",   10, 5, 10, "YES", False),
    ("Audit Report",             "Finance",   "Confidential", 10, 5, 10, "YES", False),
    ("Production Report",        "Operation", "Internal",      5, 2, 5,  "NO",  True),
    ("Equipment Maintenance Log","Operation", "Internal",      5, 2, 5,  "NO",  True),
    ("Fuel Report",              "Operation", "Internal",      3, 1, 3,  "NO",  False),
    ("HSE Incident Report",      "HSE",       "Restricted",   10, 3, 10, "YES", True),
    ("Environmental Report",     "HSE",       "Confidential", 10, 5, 10, "YES", True),
    ("Mining Permit & License",  "HSE",       "Restricted",   30, 10, 30, "YES", True),
    ("CCTV Footage",             "IT",        "Restricted",    1, 1, 1,  "NO",  False),
    ("Internal Correspondence",  "IT",        "Internal",      3, 1, 3,  "NO",  False),
]

RETENTION_POLICY_COLUMNS = [
    "DocumentType", "Department", "Classification", "RetentionYear",
    "ArchiveAfter", "DeleteAfter", "NeedApproval", "BusinessCritical",
]

SITE_INFO = {
    "MACO": "PIC MACO - Site Coordinator",
    "ADMO": "PIC ADMO - Site Coordinator",
    "SERA": "PIC SERA - Site Coordinator",
}

STORAGE_LOCATION_BY_TYPE = {
    "CCTV Footage": "Local NVR Server",
    "Production Report": "SharePoint",
    "Equipment Maintenance Log": "SharePoint",
    "Fuel Report": "SharePoint",
}
DEFAULT_STORAGE_LOCATION = "SAP"

ROLES = ["Staff", "Supervisor", "Superintendent", "Manager", "Admin SAP", "Data Governance"]


def _weighted_created_date() -> pd.Timestamp:
    """
    Umur dokumen dibuat tidak uniform: sebagian besar dokumen relatif baru
    (1-3 tahun), tapi ada ekor panjang dokumen lama (sampai 15 tahun)
    supaya skenario 'expired' & 'archive candidate' benar-benar muncul.
    """
    years_back = np.random.choice(
        np.arange(0, 16),
        p=_years_back_distribution(),
    )
    days_jitter = random.randint(0, 364)
    ts = pd.Timestamp(config.SIMULATION_DATE) - pd.Timedelta(days=int(years_back * 365 + days_jitter))
    return ts


def _years_back_distribution():
    # Distribusi condong ke dokumen baru (years_back kecil = bobot besar),
    # dengan ekor panjang ke dokumen lama (years_back besar = bobot kecil).
    raw = np.array([14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1.5, 1, 0.5])
    return raw / raw.sum()


def generate_retention_policy() -> pd.DataFrame:
    df = pd.DataFrame(DOCUMENT_TYPE_POLICY, columns=RETENTION_POLICY_COLUMNS)
    return df


def generate_sites() -> pd.DataFrame:
    rows = []
    for site in config.SITES:
        rows.append({
            "SiteID": site,
            "SiteName": {
                "MACO": "Site Melak Adang Coal Operation",
                "ADMO": "Site Adaro Mining Operation",
                "SERA": "Site Sebuku Reserve Area",
            }[site],
            "PIC": SITE_INFO[site],
            "TotalDocument": 0,  # akan di-update setelah dokumen digenerate
        })
    return pd.DataFrame(rows)


def generate_users(n_users: int = config.N_USERS) -> pd.DataFrame:
    rows = []
    for i in range(1, n_users + 1):
        dept = random.choice(config.DEPARTMENTS)
        site = random.choice(config.SITES)
        role = random.choices(ROLES, weights=[45, 25, 15, 8, 4, 3])[0]
        rows.append({
            "UserID": f"U{i:04d}",
            "Name": fake.name(),
            "Role": role,
            "Department": dept,
            "Site": site,
        })
    return pd.DataFrame(rows)


def generate_documents(n_docs: int = config.N_DOCUMENTS) -> pd.DataFrame:
    policy_df = generate_retention_policy()
    policy_lookup = policy_df.set_index("DocumentType").to_dict("index")
    doc_types = policy_df["DocumentType"].tolist()

    # Beberapa jenis dokumen jauh lebih umum daripada yang lain (realistis:
    # invoice & production report jauh lebih banyak daripada mining permit)
    type_weights = {
        "Payroll": 6, "Employment Contract": 3, "Training Record": 5,
        "Vendor Contract": 5, "Purchase Order": 9, "Invoice": 12,
        "Tax Document": 3, "Audit Report": 2, "Production Report": 14,
        "Equipment Maintenance Log": 12, "Fuel Report": 8,
        "HSE Incident Report": 5, "Environmental Report": 3,
        "Mining Permit & License": 1, "CCTV Footage": 9,
        "Internal Correspondence": 6,
    }
    weights = np.array([type_weights[t] for t in doc_types], dtype=float)
    weights = weights / weights.sum()

    owners_pool = [fake.name() for _ in range(300)]

    rows = []
    for i in range(1, n_docs + 1):
        doc_type = np.random.choice(doc_types, p=weights)
        pol = policy_lookup[doc_type]
        site = random.choice(config.SITES)
        created = _weighted_created_date()

        # LastAccessDate: sebagian dokumen TIDAK PERNAH diakses (realistis
        # untuk dokumen arsip/CCTV lama). Sisanya diakses setelah CreatedDate.
        never_accessed_prob = 0.18
        if random.random() < never_accessed_prob:
            last_access = pd.NaT
        else:
            max_days_since_created = max((pd.Timestamp(config.SIMULATION_DATE) - created).days, 1)
            offset = random.randint(0, max_days_since_created)
            last_access = created + pd.Timedelta(days=offset)

        size_mb = {
            "CCTV Footage": round(random.uniform(500, 8000), 1),
        }.get(doc_type, round(random.uniform(0.1, 45), 2))

        storage = STORAGE_LOCATION_BY_TYPE.get(doc_type, DEFAULT_STORAGE_LOCATION)

        classification = pol["Classification"]
        # Noise realistis: ~3% classification kosong (harus diisi ulang oleh
        # Classification Engine berdasarkan mapping DocumentType)
        if random.random() < 0.03:
            classification = np.nan

        created_out = created
        # Noise realistis: ~1% CreatedDate kosong/rusak (harus ditangkap oleh
        # Data Validation Module)
        if random.random() < 0.01:
            created_out = pd.NaT

        rows.append({
            "DocumentID": 10000 + i,
            "DocumentName": f"{doc_type.replace(' ', '_')}_{site}_{created.strftime('%b%Y') if pd.notna(created) else 'UNK'}_{i:05d}",
            "Site": site,
            "Department": pol["Department"],
            "DocumentType": doc_type,
            "Classification": classification,
            "Owner": random.choice(owners_pool),
            "CreatedDate": created_out,
            "LastAccessDate": last_access,
            "RetentionYear": pol["RetentionYear"],
            "Status": "ACTIVE",
            "StorageLocation": storage,
            "SizeMB": size_mb,
        })

    df = pd.DataFrame(rows)

    # Suntikkan sedikit duplikat DocumentID (realistis: kesalahan input /
    # duplikasi saat export SAP berulang) supaya Data Validation Module
    # punya kasus nyata untuk dideteksi & dibersihkan.
    dup_rows = df.sample(frac=0.006, random_state=config.RANDOM_SEED).copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df


def generate_access_log(documents_df: pd.DataFrame, users_df: pd.DataFrame) -> pd.DataFrame:
    activities = ["VIEW", "DOWNLOAD", "EDIT", "DELETE"]
    activity_weights = [70, 20, 8, 2]

    user_ids = users_df["UserID"].tolist()
    user_role_map = users_df.set_index("UserID")["Role"].to_dict()

    log_rows = []
    log_id = 1
    for _, doc in documents_df.iterrows():
        if pd.isna(doc["LastAccessDate"]) or pd.isna(doc["CreatedDate"]):
            continue  # dokumen yang tidak pernah diakses -> tidak ada log

        n_logs = np.random.randint(config.MIN_ACCESS_LOG_PER_DOC, config.MAX_ACCESS_LOG_PER_DOC)
        if n_logs == 0:
            continue

        span_days = max((doc["LastAccessDate"] - doc["CreatedDate"]).days, 1)
        n_distinct_users = min(len(user_ids), max(1, int(np.random.exponential(scale=3)) + 1))
        doc_users = random.sample(user_ids, k=n_distinct_users)

        for _ in range(n_logs):
            offset = random.randint(0, span_days)
            access_date = doc["CreatedDate"] + pd.Timedelta(days=offset)
            user = random.choice(doc_users)
            log_rows.append({
                "LogID": log_id,
                "DocumentID": doc["DocumentID"],
                "UserID": user,
                "Role": user_role_map.get(user, "Staff"),
                "AccessDate": access_date,
                "Activity": random.choices(activities, weights=activity_weights)[0],
            })
            log_id += 1

    return pd.DataFrame(log_rows)


def main():
    config.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/5] Generating retention policy master...")
    retention_policy_df = generate_retention_policy()

    print("[2/5] Generating sites master...")
    sites_df = generate_sites()

    print("[3/5] Generating users master...")
    users_df = generate_users()

    print(f"[4/5] Generating {config.N_DOCUMENTS} documents (DOCUMENT_MASTER)...")
    documents_df = generate_documents()

    print("[5/5] Generating access logs (this may take a few seconds)...")
    access_log_df = generate_access_log(documents_df, users_df)

    # Update TotalDocument per site (dihitung dari data riil, bukan hardcode)
    site_counts = documents_df["Site"].value_counts()
    sites_df["TotalDocument"] = sites_df["SiteID"].map(site_counts).fillna(0).astype(int)

    documents_df.to_csv(config.DOCUMENT_MASTER_CSV, index=False)
    retention_policy_df.to_csv(config.RETENTION_POLICY_CSV, index=False)
    users_df.to_csv(config.USERS_CSV, index=False)
    sites_df.to_csv(config.SITES_CSV, index=False)
    access_log_df.to_csv(config.ACCESS_LOG_CSV, index=False)

    print("\nSelesai. Ringkasan data yang dihasilkan:")
    print(f"  - documents.csv        : {len(documents_df):,} baris")
    print(f"  - retention_policy.csv : {len(retention_policy_df):,} baris")
    print(f"  - users.csv            : {len(users_df):,} baris")
    print(f"  - sites.csv             : {len(sites_df):,} baris")
    print(f"  - access_log.csv       : {len(access_log_df):,} baris")
    print(f"\nDisimpan di: {config.DATA_RAW_DIR}")

def generate_database():
    main()
if __name__ == "__main__":
    main()
