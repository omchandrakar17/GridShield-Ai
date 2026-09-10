"""
Consumption analysis engine – feature generation and historical trend analysis.
Works entirely from real ingested data stored in the DB.
"""
import logging
from typing import Optional
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger("gridshield.analysis")


def build_consumer_profile(records: list[dict]) -> Optional[dict]:
    """
    Given a list of billing records for one consumer (dicts from DB rows),
    compute a rich profile with statistical features.
    Returns None if insufficient data.
    """
    if not records:
        return None

    df = pd.DataFrame(records)

    # ensure sorted by period
    if "billing_period" in df.columns:
        df = df.sort_values("billing_period").reset_index(drop=True)

    cons_col = _pick_consumption_col(df)
    if cons_col is None:
        return None

    series: pd.Series = df[cons_col].dropna()
    if len(series) < 1:
        return None

    n = len(series)
    mean_consumption = float(series.mean())
    std_consumption = float(series.std()) if n > 1 else 0.0
    median_consumption = float(series.median())
    min_consumption = float(series.min())
    max_consumption = float(series.max())
    cv = (std_consumption / mean_consumption) if mean_consumption > 0 else 0.0

    # month-over-month percentage changes
    mom_changes = series.pct_change().dropna()
    avg_mom_change = float(mom_changes.mean()) if len(mom_changes) else 0.0

    # linear trend (positive = increasing, negative = decreasing)
    trend_slope = 0.0
    if n >= 3:
        x = np.arange(n)
        slope, _, _, _, _ = stats.linregress(x, series.values)
        trend_slope = float(slope)

    # rolling 3-period average for latest period
    rolling_3 = float(series.rolling(3, min_periods=1).mean().iloc[-1])

    periods = df["billing_period"].tolist() if "billing_period" in df.columns else list(range(n))
    last_value = float(series.iloc[-1])
    prev_value = float(series.iloc[-2]) if n >= 2 else None

    profile = {
        "consumer_id": str(df["consumer_id"].iloc[0]) if "consumer_id" in df.columns else "unknown",
        "consumer_type": str(df["consumer_type"].iloc[0]) if "consumer_type" in df.columns and df["consumer_type"].notna().any() else "unknown",
        "tariff_category": str(df["tariff_category"].iloc[0]) if "tariff_category" in df.columns and df["tariff_category"].notna().any() else "unknown",
        "location": str(df["location"].iloc[0]) if "location" in df.columns and df["location"].notna().any() else "unknown",
        "division": str(df["division"].iloc[0]) if "division" in df.columns and df["division"].notna().any() else "unknown",
        "periods_available": n,
        "periods": periods,
        "consumption_values": series.tolist(),
        "mean_consumption": round(mean_consumption, 4),
        "std_consumption": round(std_consumption, 4),
        "median_consumption": round(median_consumption, 4),
        "min_consumption": round(min_consumption, 4),
        "max_consumption": round(max_consumption, 4),
        "coefficient_of_variation": round(cv, 4),
        "trend_slope": round(trend_slope, 6),
        "avg_mom_change_pct": round(avg_mom_change * 100, 2),
        "rolling_3_avg": round(rolling_3, 4),
        "last_value": round(last_value, 4),
        "prev_value": round(prev_value, 4) if prev_value is not None else None,
        "billing_data": _extract_billing_data(df),
    }

    return profile


def _pick_consumption_col(df: pd.DataFrame) -> Optional[str]:
    for col in ["units_consumed", "billed_units"]:
        if col in df.columns and df[col].notna().sum() > 0:
            return col
    return None


def _extract_billing_data(df: pd.DataFrame) -> list[dict]:
    """Extract billing summary per period for display."""
    rows = []
    for _, row in df.iterrows():
        entry = {
            "billing_period": row.get("billing_period", ""),
            "units_consumed": _safe_float(row.get("units_consumed")),
            "billed_units": _safe_float(row.get("billed_units")),
            "amount_billed": _safe_float(row.get("amount_billed")),
            "meter_reading_start": _safe_float(row.get("meter_reading_start")),
            "meter_reading_end": _safe_float(row.get("meter_reading_end")),
        }
        rows.append(entry)
    return rows


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return round(v, 4) if not np.isnan(v) else None
    except (TypeError, ValueError):
        return None


def compute_period_zscores(profile: dict) -> list[dict]:
    """
    Compute z-score for each period's consumption relative to the consumer's
    own historical distribution. Returns list of {period, value, zscore}.
    """
    values = profile.get("consumption_values", [])
    periods = profile.get("periods", [])
    if len(values) < 2:
        return []

    arr = np.array(values, dtype=float)
    mean = np.nanmean(arr)
    std = np.nanstd(arr)
    if std == 0:
        zscores = [0.0] * len(arr)
    else:
        zscores = ((arr - mean) / std).tolist()

    return [
        {"period": str(p), "value": round(float(v), 4), "zscore": round(float(z), 4)}
        for p, v, z in zip(periods, values, zscores)
    ]
