"""
dashboard/components.py
--------------------------
Kumpulan helper untuk membangun chart Plotly & elemen UI yang dipakai
berulang di app.py. Dipisah supaya app.py tetap fokus ke "alur halaman",
bukan detail styling chart.
"""

from __future__ import annotations
import plotly.express as px
import pandas as pd

COLOR_MAP_RECOMMENDATION = {
    "KEEP": "#2E7D32",
    "ARCHIVE": "#1565C0",
    "DELETE": "#C62828",
    "REVIEW": "#EF6C00",
}

COLOR_MAP_RISK = {
    "Low": "#2E7D32",
    "Medium": "#F9A825",
    "High": "#EF6C00",
    "Critical": "#C62828",
}


def chart_by_site(df: pd.DataFrame):
    counts = df["Site"].value_counts().reset_index()
    counts.columns = ["Site", "Jumlah Dokumen"]
    fig = px.bar(
        counts, x="Site", y="Jumlah Dokumen", text="Jumlah Dokumen",
        color="Site", title="Dokumen per Site",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, margin=dict(t=50, b=20))
    return fig


def chart_by_department(df: pd.DataFrame):
    counts = df["Department"].value_counts().reset_index()
    counts.columns = ["Department", "Jumlah Dokumen"]
    fig = px.bar(
        counts.sort_values("Jumlah Dokumen"), x="Jumlah Dokumen", y="Department",
        orientation="h", text="Jumlah Dokumen", title="Dokumen per Departemen",
    )
    fig.update_traces(textposition="outside", marker_color="#1565C0")
    fig.update_layout(margin=dict(t=50, b=20))
    return fig


def chart_lifecycle_status(df: pd.DataFrame):
    counts = df["Recommendation"].value_counts().reset_index()
    counts.columns = ["Recommendation", "Jumlah Dokumen"]
    fig = px.pie(
        counts, names="Recommendation", values="Jumlah Dokumen",
        color="Recommendation", color_discrete_map=COLOR_MAP_RECOMMENDATION,
        title="Distribusi Status Lifecycle", hole=0.45,
    )
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(margin=dict(t=50, b=20))
    return fig


def chart_risk_distribution(df: pd.DataFrame):
    order = ["Low", "Medium", "High", "Critical"]
    counts = df["RiskCategory"].value_counts().reindex(order).fillna(0).reset_index()
    counts.columns = ["RiskCategory", "Jumlah Dokumen"]
    fig = px.bar(
        counts, x="RiskCategory", y="Jumlah Dokumen", text="Jumlah Dokumen",
        color="RiskCategory", color_discrete_map=COLOR_MAP_RISK,
        title="Distribusi Risk Score", category_orders={"RiskCategory": order},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, margin=dict(t=50, b=20))
    return fig


def kpi_values(df: pd.DataFrame) -> dict:
    return {
        "Total Dokumen": len(df),
        "Expired": int(df["Expired"].sum()),
        "Archive Candidate": int((df["Recommendation"] == "ARCHIVE").sum()),
        "Delete Candidate": int((df["Recommendation"] == "DELETE").sum()),
        "Review Candidate": int((df["Recommendation"] == "REVIEW").sum()),
        "Storage Used (GB)": round(df["SizeMB"].sum() / 1024, 1),
    }
