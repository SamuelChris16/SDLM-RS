"""
config.py
----------
Konfigurasi pusat untuk SDLM-RS (Smart Data Lifecycle Management
Recommendation System).

Semua path, parameter bisnis, dan bobot scoring didefinisikan di sini
supaya tidak ada "magic number" yang tersebar di banyak file
(prinsip single source of truth untuk enterprise app).
"""

from pathlib import Path
from datetime import date

# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATABASE_DIR = BASE_DIR / "database"
REPORTS_DIR = BASE_DIR / "reports"

DATABASE_PATH = DATABASE_DIR / "sdlm.db"

DOCUMENT_MASTER_CSV = DATA_RAW_DIR / "documents.csv"
RETENTION_POLICY_CSV = DATA_RAW_DIR / "retention_policy.csv"
ACCESS_LOG_CSV = DATA_RAW_DIR / "access_log.csv"
USERS_CSV = DATA_RAW_DIR / "users.csv"
SITES_CSV = DATA_RAW_DIR / "sites.csv"

RECOMMENDATION_REPORT_XLSX = REPORTS_DIR / "recommendation_report.xlsx"
VALIDATION_REPORT_CSV = REPORTS_DIR / "data_validation_report.csv"

# ---------------------------------------------------------------------
# SIMULATION "AS OF" DATE
# ---------------------------------------------------------------------
# Semua perhitungan umur dokumen (retensi, expired, dsb) dihitung relatif
# terhadap tanggal ini. Di dunia nyata ini = tanggal job batch dijalankan.
# Dibuat sebagai konstanta (bukan datetime.now()) supaya hasil selalu
# reproducible saat demo / testing.
SIMULATION_DATE = date(2026, 7, 1)

# ---------------------------------------------------------------------
# MASTER DATA — SITE & DEPARTMENT
# ---------------------------------------------------------------------
SITES = ["MACO", "ADMO", "SERA"]

DEPARTMENTS = ["HR", "Finance", "Operation", "SCM", "HSE", "IT"]

# ---------------------------------------------------------------------
# RISK ENGINE — BOBOT SCORING
# ---------------------------------------------------------------------
# Total maksimum = 100 (40 + 30 + 20 + 10)
CLASSIFICATION_WEIGHT = {
    "Restricted": 40,
    "Confidential": 30,
    "Internal": 15,
    "Public": 5,
}

# Expired score dibuat gradual (bukan cuma YES/NO) supaya lebih realistis:
# makin lama lewat masa retensi, makin tinggi skornya, dibatasi maksimum 30.
EXPIRED_MAX_SCORE = 30
EXPIRED_SCORE_PER_YEAR_OVERDUE = 10  # dikali tahun overdue, dicap di EXPIRED_MAX_SCORE

# Access frequency / recency score (maksimum 20)
ACCESS_SCORE_NEVER_ACCESSED = 20
ACCESS_SCORE_OVER_2_YEARS = 15
ACCESS_SCORE_1_TO_2_YEARS = 8
ACCESS_SCORE_RECENT = 0  # diakses < 1 tahun terakhir

# Exposure score — makin banyak user berbeda yang mengakses dokumen
# sensitif, makin tinggi risiko kebocoran data (maksimum 10)
EXPOSURE_SCORE_HIGH = 10   # >= 10 distinct users
EXPOSURE_SCORE_MEDIUM = 5  # 3-9 distinct users
EXPOSURE_SCORE_LOW = 0     # < 3 distinct users

RISK_CATEGORY_BINS = [0, 30, 60, 80, 100]
RISK_CATEGORY_LABELS = ["Low", "Medium", "High", "Critical"]

# ---------------------------------------------------------------------
# DATA GENERATOR — VOLUME (dibuat cukup besar agar mendekati kondisi riil)
# ---------------------------------------------------------------------
N_DOCUMENTS = 6000
N_USERS = 180
MIN_ACCESS_LOG_PER_DOC = 0
MAX_ACCESS_LOG_PER_DOC = 25
RANDOM_SEED = 42
