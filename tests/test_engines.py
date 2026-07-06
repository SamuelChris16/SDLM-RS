"""
tests/test_engines.py
------------------------
Unit test dasar untuk memastikan logic tiap engine benar secara ISOLASI
(tidak bergantung pada data hasil generator), memakai data buatan kecil
yang hasilnya sudah diketahui pasti.

Jalankan:
    pytest tests/ -v
"""

import sys
from pathlib import Path
from datetime import date

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from engine import classification_engine, retention_engine, risk_engine, lifecycle_engine


def make_policy_df():
    return pd.DataFrame([
        {"DocumentType": "Payroll", "Department": "HR", "Classification": "Restricted",
         "RetentionYear": 10, "ArchiveAfter": 5, "DeleteAfter": 10, "NeedApproval": "YES", "BusinessCritical": False},
        {"DocumentType": "Fuel Report", "Department": "Operation", "Classification": "Internal",
         "RetentionYear": 3, "ArchiveAfter": 1, "DeleteAfter": 3, "NeedApproval": "NO", "BusinessCritical": False},
        {"DocumentType": "Mining Permit & License", "Department": "HSE", "Classification": "Restricted",
         "RetentionYear": 30, "ArchiveAfter": 10, "DeleteAfter": 30, "NeedApproval": "YES", "BusinessCritical": True},
    ])


def test_classification_engine_fills_missing_classification():
    policy_df = make_policy_df()
    docs_df = pd.DataFrame([
        {"DocumentType": "Payroll", "Classification": None},
        {"DocumentType": "Fuel Report", "Classification": "Wrong Value"},
    ])
    result = classification_engine.classify_documents(docs_df, policy_df)
    assert result.loc[0, "Classification"] == "Restricted"
    assert result.loc[0, "ClassificationSource"] == "AUTO_FILLED"
    assert result.loc[1, "Classification"] == "Internal"
    assert result.loc[1, "ClassificationSource"] == "AUTO_CORRECTED"


def test_retention_engine_flags_expired_document():
    policy_df = make_policy_df()
    old_date = pd.Timestamp(config.SIMULATION_DATE) - pd.Timedelta(days=365 * 5)  # 5 tahun lalu
    docs_df = pd.DataFrame([
        {"DocumentType": "Fuel Report", "CreatedDate": old_date, "RetentionYear": 3},
    ])
    result = retention_engine.apply_retention_rules(docs_df, policy_df)
    assert bool(result.loc[0, "Expired"]) is True
    assert bool(result.loc[0, "DeleteDue"]) is True


def test_retention_engine_active_document_not_expired():
    policy_df = make_policy_df()
    recent_date = pd.Timestamp(config.SIMULATION_DATE) - pd.Timedelta(days=30)
    docs_df = pd.DataFrame([
        {"DocumentType": "Payroll", "CreatedDate": recent_date, "RetentionYear": 10},
    ])
    result = retention_engine.apply_retention_rules(docs_df, policy_df)
    assert bool(result.loc[0, "Expired"]) is False
    assert bool(result.loc[0, "ArchiveDue"]) is False


def test_risk_engine_never_accessed_gets_max_access_score():
    docs_df = pd.DataFrame([
        {"DocumentID": 1, "Classification": "Restricted", "LastAccessDate": pd.NaT, "OverdueYears": 0.0},
    ])
    access_log_df = pd.DataFrame(columns=["DocumentID", "UserID"])
    result = risk_engine.compute_risk_scores(docs_df, access_log_df)
    assert result.loc[0, "AccessFrequencyScore"] == config.ACCESS_SCORE_NEVER_ACCESSED
    assert result.loc[0, "ClassificationScore"] == config.CLASSIFICATION_WEIGHT["Restricted"]


def test_lifecycle_engine_business_critical_always_keep():
    row = pd.Series({
        "BusinessCritical": True, "DeleteDue": True, "ArchiveDue": True,
        "Classification": "Restricted", "NeedApproval": "YES",
        "LastAccessDate": pd.NaT, "AccessFrequencyScore": 20,
    })
    rec, reason = lifecycle_engine._recommend_row(row)
    assert rec == "KEEP"


def test_lifecycle_engine_expired_sensitive_goes_to_review():
    row = pd.Series({
        "BusinessCritical": False, "DeleteDue": True, "ArchiveDue": True,
        "Classification": "Restricted", "NeedApproval": "YES",
        "LastAccessDate": pd.NaT, "AccessFrequencyScore": 20,
    })
    rec, reason = lifecycle_engine._recommend_row(row)
    assert rec == "REVIEW"


def test_lifecycle_engine_expired_non_sensitive_goes_to_delete():
    row = pd.Series({
        "BusinessCritical": False, "DeleteDue": True, "ArchiveDue": True,
        "Classification": "Internal", "NeedApproval": "NO",
        "LastAccessDate": pd.NaT, "AccessFrequencyScore": 20,
    })
    rec, reason = lifecycle_engine._recommend_row(row)
    assert rec == "DELETE"
