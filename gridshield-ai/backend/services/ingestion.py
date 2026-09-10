"""
Data ingestion, validation, and cleaning pipeline for GridShield AI.

Supported real dataset:
  - UCI / Kaggle: "Electric Power Consumption" (household_power_consumption.txt)
  - Open Government / Utility CSV exports with standard billing fields
  - Any CSV with column auto-mapping

Column auto-mapping covers common real-world column name variations:
  consumer_id, billing_period, meter_reading_start, meter_reading_end,
  units_consumed, billed_units, amount_billed, tariff_category,
  sanctioned_load_kw, consumer_type, location, division
"""
import os
import re
import logging
import hashlib
from datetime import datetime, date
from typing import Optional

import pandas as pd
import numpy as np
from dateutil import parser as dateparser

logger = logging.getLogger("gridshield.ingest")

# ── canonical column aliases ────────────────────────────────────────────────
COLUMN_ALIASES: dict[str, list[str]] = {
    "consumer_id": [
        "consumer_id", "consumerid", "consumer id", "account_no", "accountno",
        "account_number", "cust_id", "customer_id", "meter_no", "meterno",
        "meter_number", "account", "id",
    ],
    "billing_period": [
        "billing_period", "billingperiod", "billing period", "bill_month",
        "month", "period", "billing_month", "date", "bill_date",
    ],
    "meter_reading_start": [
        "meter_reading_start", "previous_reading", "prev_reading",
        "opening_reading", "start_reading", "meter_start",
    ],
    "meter_reading_end": [
        "meter_reading_end", "current_reading", "curr_reading",
        "closing_reading", "end_reading", "meter_end", "present_reading",
    ],
    "units_consumed": [
        "units_consumed", "consumption", "kwh", "energy_kwh", "units",
        "net_units", "net_consumption", "consumed_units", "global_active_power",
    ],
    "billed_units": [
        "billed_units", "billed_kwh", "assessed_units", "charged_units",
    ],
    "amount_billed": [
        "amount_billed", "bill_amount", "amount", "charge", "total_amount",
        "total_charge", "bill_total",
    ],
    "tariff_category": [
        "tariff_category", "tariff", "rate_category", "rate_code",
        "tariff_code", "category",
    ],
    "sanctioned_load_kw": [
        "sanctioned_load_kw", "sanctioned_load", "connected_load",
        "contract_demand", "load_kw", "load",
    ],
    "consumer_type": [
        "consumer_type", "consumer_category", "category", "segment",
        "customer_type", "service_type",
    ],
    "location": ["location", "address", "area", "locality", "zone"],
    "division": ["division", "circle", "district", "region", "substation"],
}


def _normalize_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "_", name.strip().lower())


def map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """
    Auto-map dataset columns to canonical GridShield field names.
    Returns (renamed_df, mapping_used).
    """
    norm_to_raw = {_normalize_col(c): c for c in df.columns}
    rename_map: dict[str, str] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            norm_alias = _normalize_col(alias)
            if norm_alias in norm_to_raw:
                rename_map[norm_to_raw[norm_alias]] = canonical
                break

    df = df.rename(columns=rename_map)
    return df, rename_map


def normalize_billing_period(series: pd.Series) -> pd.Series:
    """Convert varied date formats to YYYY-MM string."""
    def _parse(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        # already YYYY-MM
        if re.match(r"^\d{4}-\d{2}$", s):
            return s
        # MM/YYYY or MM-YYYY
        m = re.match(r"^(\d{1,2})[\/\-](\d{4})$", s)
        if m:
            return f"{m.group(2)}-{int(m.group(1)):02d}"
        # try dateutil
        try:
            dt = dateparser.parse(s, default=datetime(2000, 1, 1))
            return dt.strftime("%Y-%m")
        except Exception:
            return None
    return series.apply(_parse)


def validate_and_clean(df: pd.DataFrame, source_file: str = "") -> tuple[pd.DataFrame, dict]:
    """
    Full validation and cleaning pipeline.
    Returns (cleaned_df, report_dict).
    """
    report = {
        "source_file": source_file,
        "original_rows": len(df),
        "issues": [],
        "dropped_rows": 0,
        "mapped_columns": [],
        "canonical_fields_present": [],
        "extra_fields": [],
    }

    # 1. column mapping
    df, mapping = map_columns(df)
    report["mapped_columns"] = [f"{k} → {v}" for k, v in mapping.items()]

    canonical_fields = list(COLUMN_ALIASES.keys())
    report["canonical_fields_present"] = [f for f in canonical_fields if f in df.columns]
    report["extra_fields"] = [c for c in df.columns if c not in canonical_fields]

    # 2. require consumer_id
    if "consumer_id" not in df.columns:
        raise ValueError(
            "Dataset must contain a consumer/account ID column. "
            "Detected columns: " + ", ".join(df.columns.tolist())
        )

    # 3. normalize billing period
    if "billing_period" in df.columns:
        df["billing_period"] = normalize_billing_period(df["billing_period"])

    # 4. numeric coercion
    numeric_cols = [
        "meter_reading_start", "meter_reading_end", "units_consumed",
        "billed_units", "amount_billed", "sanctioned_load_kw",
    ]
    for col in numeric_cols:
        if col in df.columns:
            before = df[col].notna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            after = df[col].notna().sum()
            lost = before - after
            if lost:
                report["issues"].append(f"{col}: {lost} non-numeric values set to NaN")

    # 5. derived units_consumed if missing
    if "units_consumed" not in df.columns or df["units_consumed"].isna().all():
        if "meter_reading_start" in df.columns and "meter_reading_end" in df.columns:
            df["units_consumed"] = (
                df["meter_reading_end"] - df["meter_reading_start"]
            ).clip(lower=0)
            report["issues"].append("units_consumed derived from meter readings")

    # 6. drop rows missing both consumer_id and any consumption measure
    key_missing = df["consumer_id"].isna()
    if key_missing.any():
        report["dropped_rows"] += int(key_missing.sum())
        report["issues"].append(f"Dropped {int(key_missing.sum())} rows missing consumer_id")
        df = df[~key_missing]

    # 7. deduplicate (consumer_id + billing_period)
    if "billing_period" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["consumer_id", "billing_period"], keep="last")
        dup = before - len(df)
        if dup:
            report["issues"].append(f"Dropped {dup} duplicate consumer_id+billing_period rows")

    # 8. sanity checks on values
    if "units_consumed" in df.columns:
        neg = (df["units_consumed"] < 0).sum()
        if neg:
            report["issues"].append(f"{neg} negative units_consumed values clamped to 0")
            df.loc[df["units_consumed"] < 0, "units_consumed"] = 0

    # 9. stringify consumer_id
    df["consumer_id"] = df["consumer_id"].astype(str).str.strip()

    # 10. source_file tracking
    df["source_file"] = source_file

    report["final_rows"] = len(df)
    return df, report


def compute_record_hash(consumer_id: str, billing_period: str) -> str:
    return hashlib.sha256(f"{consumer_id}|{billing_period}".encode()).hexdigest()[:16]
