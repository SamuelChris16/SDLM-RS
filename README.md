# SDLM-RS — Smart Data Lifecycle Management Recommendation System

Prototipe *Decision Support System* untuk membantu **JAHO (PT Saptaindra
Sejati)** mengevaluasi siklus hidup dokumen dari seluruh site (**MACO,
ADMO, SERA**) dan menghasilkan rekomendasi **KEEP / ARCHIVE / DELETE /
REVIEW** berdasarkan kebijakan Data Lifecycle Management.

> Sistem ini **tidak mengubah data di SAP secara langsung**. Output-nya
> adalah recommendation report + workflow review, sebagai bahan
> pengambilan keputusan untuk tim Data Governance JAHO.

---

## 1. Arsitektur Sistem

```
SAP Export (CSV)
      │
      ▼
Data Ingestion Module        (engine/data_ingestion.py)
      │
      ▼
Data Validation Module       (engine/data_validation.py)
      │
      ▼
Data Classification Engine   (engine/classification_engine.py)
      │
      ▼
Retention Rule Engine        (engine/retention_engine.py)
      │
      ▼
Risk Scoring Engine          (engine/risk_engine.py)
      │
      ▼
Lifecycle Recommendation     (engine/lifecycle_engine.py)
      │
      ▼
SQLite Database + Excel Report
      │
      ▼
Dashboard (Streamlit)  ──►  JAHO Data Governance Review  ──►  SAP Admin
```

Alur ini persis mengikuti spesifikasi awal, dipecah menjadi modul-modul
Python yang independen supaya mudah di-*maintain* dan di-*test* satu per
satu — bukan satu file monolitik.

---

## 2. Struktur Folder

```
SDLM-RS/
├── app.py                     # Dashboard Streamlit (entry point utama)
├── config.py                  # Semua path, konstanta, bobot scoring
├── requirements.txt
├── README.md
│
├── data/
│   ├── raw/                   # Hasil "export SAP" (CSV) — dari data_generator
│   │   ├── documents.csv          (DOCUMENT_MASTER, ~6000 baris)
│   │   ├── retention_policy.csv   (RETENTION_POLICY, 16 tipe dokumen)
│   │   ├── access_log.csv         (ACCESS_LOG, ~59.000 baris)
│   │   ├── users.csv              (USER, 180 user)
│   │   └── sites.csv              (SITE: MACO, ADMO, SERA)
│   └── processed/             # (reserved untuk output antara, kalau perlu)
│
├── database/
│   └── sdlm.db                 # SQLite — dibuat otomatis oleh pipeline
│
├── engine/                    # Semua "otak" bisnis logic ada di sini
│   ├── data_ingestion.py          # Baca CSV -> DataFrame
│   ├── data_validation.py         # Bersihkan & validasi data kotor
│   ├── classification_engine.py   # Standardisasi klasifikasi dokumen
│   ├── retention_engine.py        # Hitung umur & status retensi
│   ├── risk_engine.py             # Hitung risk score 0-100
│   └── lifecycle_engine.py        # Gabungkan semua -> rekomendasi akhir
│
├── dashboard/
│   └── components.py          # Helper chart Plotly untuk app.py
│
├── utils/
│   ├── data_generator.py      # Generator mock data realistis
│   └── db_utils.py            # Helper koneksi & query SQLite
│
├── scripts/
│   └── run_pipeline.py        # Orchestrator batch job end-to-end
│
├── tests/
│   └── test_engines.py        # Unit test tiap engine (pytest)
│
└── reports/
    ├── recommendation_report.xlsx   # Output pipeline (2 sheet: detail + summary)
    └── data_validation_report.csv   # Log temuan data kotor
```

---

## 3. Cara Menjalankan (VS Code, Python murni)

```bash
# 1. Buat virtual environment (opsional tapi disarankan)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependency
pip install -r requirements.txt

# 3. Generate data mentah (mensimulasikan hasil export SAP)
python -m utils.data_generator

# 4. Jalankan pipeline (ingestion -> validation -> classification ->
#    retention -> risk -> lifecycle -> simpan ke database + Excel report)
python scripts/run_pipeline.py

# 5. Jalankan dashboard
streamlit run app.py
```

Setiap kali `data_generator` dijalankan ulang, data akan **selalu sama**
(seeded random) supaya demo konsisten. Ubah `RANDOM_SEED` atau
`N_DOCUMENTS` di `config.py` kalau ingin variasi/volume berbeda.

Unit test:
```bash
pytest tests/ -v
```

---

## 4. Model Data (Mock Database)

| Tabel              | Isi                                                        |
|--------------------|-------------------------------------------------------------|
| `DOCUMENT_MASTER`  | Master dokumen: ID, nama, site, departemen, tipe, klasifikasi, tanggal, ukuran |
| `RETENTION_POLICY` | Kebijakan retensi per `DocumentType` (16 tipe dokumen realistis untuk perusahaan tambang) |
| `ACCESS_LOG`       | Riwayat akses (VIEW/EDIT/DOWNLOAD/DELETE) per dokumen per user |
| `SITE`             | MACO, ADMO, SERA                                            |
| `USER`             | 180 user dummy lintas departemen & site (nama Indonesia via Faker) |

**Data sengaja dibuat "kotor" sebagian** (≈1% tanggal kosong, ≈3%
klasifikasi kosong, ≈0.6% ID duplikat) — supaya Data Validation Module
punya kasus nyata untuk ditangani, bukan sekadar dekorasi kode.

16 jenis dokumen yang dimodelkan (lihat `utils/data_generator.py`):
`Payroll, Employment Contract, Training Record, Vendor Contract, Purchase
Order, Invoice, Tax Document, Audit Report, Production Report, Equipment
Maintenance Log, Fuel Report, HSE Incident Report, Environmental Report,
Mining Permit & License, CCTV Footage, Internal Correspondence` — dipilih
supaya relevan dengan operasional site tambang, bukan dokumen generik.

---

## 5. Logika Tiap Engine

### Engine 1 — Retention Engine
```
DocumentAgeYears = (SimulationDate - CreatedDate) / 365.25
Expired    = DocumentAgeYears > RetentionYear
ArchiveDue = DocumentAgeYears >= ArchiveAfter
DeleteDue  = DocumentAgeYears >= DeleteAfter
```

### Engine 2 — Classification Engine
Klasifikasi (`Restricted/Confidential/Internal/Public`) di-standardisasi
ulang berdasarkan mapping resmi `DocumentType -> Classification` di
`RETENTION_POLICY`, bukan sekadar percaya kolom mentah — kalau kosong
diisi otomatis, kalau tidak konsisten dikoreksi otomatis (tercatat di
kolom `ClassificationSource`).

### Engine 3 — Risk Scoring Engine (skala 0-100)
| Komponen              | Bobot Maks | Logika                                             |
|------------------------|-----------|----------------------------------------------------|
| Classification Score   | 40        | Restricted=40, Confidential=30, Internal=15, Public=5 |
| Expired Score          | 30        | Gradual: makin lama *overdue*, makin tinggi (dicap 30) |
| Access Frequency Score | 20        | Tidak pernah diakses=20, >2 thn=15, 1-2 thn=8, <1 thn=0 |
| Exposure Score         | 10        | Diakses ≥10 user berbeda=10, 3-9 user=5, <3 user=0  |

Kategori: `0-30 Low · 31-60 Medium · 61-80 High · 81-100 Critical`

### Engine 4 — Lifecycle Recommendation Engine
Dievaluasi berurutan (prioritas dari atas):
1. **Business Critical → KEEP** (mis. izin tambang, laporan produksi)
2. **Delete due** + klasifikasi sensitif/butuh approval **→ REVIEW**
3. **Delete due** + tidak sensitif **→ DELETE**
4. **Archive due** + jarang diakses **→ ARCHIVE**
5. Selain itu **→ KEEP**

Setiap rekomendasi disertai `Reason` (alasan berbahasa manusia) supaya
dashboard benar-benar berfungsi sebagai *Decision Support System*, bukan
cuma classifier tanpa penjelasan.

---

## 6. Dashboard (Streamlit)

Dibuat **simple & jelas**, 4 tab:

1. **Overview** — 6 KPI (Total, Expired, Archive/Delete/Review Candidate,
   Storage Used) + 4 chart (per Site, per Departemen, status Lifecycle,
   distribusi Risk).
2. **Document Explorer** — tabel dengan filter & pencarian, drill-down
   detail per dokumen (lengkap dengan alasan rekomendasi).
3. **Approval Workflow** — simulasi review oleh JAHO Data Governance:
   pilih dokumen berstatus REVIEW/DELETE, input keputusan
   Approve/Reject + nama reviewer, tersimpan permanen di tabel
   `approval_log` pada SQLite (bukan cuma disimpan di sesi browser).
4. **Reports** — download Excel report sesuai filter aktif, serta lihat
   log Data Validation Report.

Filter di sidebar (Site, Departemen, Rekomendasi, Risk Category) berlaku
ke seluruh tab secara konsisten.

---

## 7. Batasan & Asumsi (penting untuk disampaikan saat presentasi)

- **Tidak ada koneksi langsung ke SAP.** Input diasumsikan berupa hasil
  export manual (CSV/XLSX) — sesuai spesifikasi awal ("Future
  Integration").
- `SIMULATION_DATE` di `config.py` dipakai sebagai pengganti
  `datetime.now()` supaya demo selalu reproducible; di produksi nanti
  ini diganti tanggal job batch berjalan.
- Approval workflow di dashboard adalah **simulasi decision log**, bukan
  sistem approval multi-level dengan otentikasi/role-based access —
  itu wilayah pengembangan lanjutan kalau prototipe ini disetujui untuk
  dikembangkan jadi aplikasi produksi.
- Volume data (6.000 dokumen, ~59.000 log akses) dipilih agar dashboard
  terasa seperti kondisi nyata sekaligus tetap ringan dijalankan di
  laptop/Google Colab.

## 8. Rencana Pengembangan Lanjutan

- Ganti `utils/data_generator.py` dengan koneksi nyata ke hasil export
  SAP (CSV/XLSX asli).
- Tambah autentikasi role-based (Site PIC vs JAHO Data Governance vs SAP
  Admin) di layer approval workflow.
- Jadwalkan `scripts/run_pipeline.py` sebagai *cron job* / scheduled task
  supaya rekomendasi ter-update otomatis secara berkala.
- Tambah notifikasi (email/Teams) otomatis ke reviewer saat ada dokumen
  baru berstatus REVIEW.
