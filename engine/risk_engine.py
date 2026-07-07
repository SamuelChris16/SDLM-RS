from __future__ import annotations
import pandas as pd
import numpy as np
import config


def _access_frequency_score(row) -> int:
    if pd.isna(row["LastAccessDate"]):
        return config.ACCESS_SCORE_NEVER_ACCESSED
    days_since_access = (pd.Timestamp(config.SIMULATION_DATE) - row["LastAccessDate"]).days
    years_since_access = days_since_access / 365.25
    if years_since_access > 2:
        return config.ACCESS_SCORE_OVER_2_YEARS
    elif years_since_access > 1:
        return config.ACCESS_SCORE_1_TO_2_YEARS
    return config.ACCESS_SCORE_RECENT


def _exposure_score(distinct_users: int) -> int:
    if distinct_users >= 10:
        return config.EXPOSURE_SCORE_HIGH
    elif distinct_users >= 3:
        return config.EXPOSURE_SCORE_MEDIUM
    return config.EXPOSURE_SCORE_LOW


def _expired_score(overdue_years: float) -> int:
    if overdue_years <= 0:
        return 0
    return int(min(overdue_years * config.EXPIRED_SCORE_PER_YEAR_OVERDUE, config.EXPIRED_MAX_SCORE))


def compute_risk_scores(documents_df: pd.DataFrame, access_log_df: pd.DataFrame) -> pd.DataFrame:
    df = documents_df.copy()

    # Jumlah distinct user yang pernah mengakses tiap dokumen
    distinct_users = (
        access_log_df.groupby("DocumentID")["UserID"].nunique().rename("DistinctUserCount")
    )
    df = df.merge(distinct_users, on="DocumentID", how="left")
    df["DistinctUserCount"] = df["DistinctUserCount"].fillna(0).astype(int)

    df["ClassificationScore"] = df["Classification"].map(config.CLASSIFICATION_WEIGHT).fillna(0).astype(int)
    df["ExpiredScore"] = df["OverdueYears"].apply(_expired_score)
    df["AccessFrequencyScore"] = df.apply(_access_frequency_score, axis=1)
    df["ExposureScore"] = df["DistinctUserCount"].apply(_exposure_score)

    df["RiskScore"] = (
        df["ClassificationScore"] + df["ExpiredScore"] + df["AccessFrequencyScore"] + df["ExposureScore"]
    ).clip(upper=100)

    df["RiskCategory"] = pd.cut(
        df["RiskScore"],
        bins=config.RISK_CATEGORY_BINS,
        labels=config.RISK_CATEGORY_LABELS,
        include_lowest=True,
    )

    return df
