"""
Data ingestion API routes.
Accepts CSV/Excel uploads or references a configured data directory.
"""
import os
import json
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.database import get_db
from services.ingestion import validate_and_clean

logger = logging.getLogger("gridshield.routes.data")
router = APIRouter()

DATA_DIR = os.getenv("DATA_DIR", "./data")


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV or Excel billing dataset.

    Expected columns (auto-mapped from common real-world names):
      consumer_id, billing_period, meter_reading_start, meter_reading_end,
      units_consumed, billed_units, amount_billed, tariff_category,
      sanctioned_load_kw, consumer_type, location, division

    Returns an ingestion report with row counts and validation issues.
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")

    suffix = file.filename.lower().split(".")[-1]
    if suffix not in ("csv", "xlsx", "xls", "txt"):
        raise HTTPException(400, f"Unsupported file type: {suffix}. Use CSV or Excel.")

    content = await file.read()
    try:
        if suffix in ("xlsx", "xls"):
            df = pd.read_excel(content, dtype=str)
        else:
            # try semicolon first, then comma
            import io
            try:
                df = pd.read_csv(io.BytesIO(content), sep=";", dtype=str, low_memory=False)
                if df.shape[1] < 2:
                    df = pd.read_csv(io.BytesIO(content), sep=",", dtype=str, low_memory=False)
            except Exception:
                df = pd.read_csv(io.BytesIO(content), sep=",", dtype=str, low_memory=False)
    except Exception as e:
        raise HTTPException(422, f"Could not parse file: {e}")

    try:
        cleaned_df, report = validate_and_clean(df, source_file=file.filename)
    except ValueError as e:
        raise HTTPException(422, str(e))

    inserted = 0
    skipped = 0
    canonical_fields = [
        "consumer_id", "billing_period", "meter_reading_start", "meter_reading_end",
        "units_consumed", "billed_units", "amount_billed", "tariff_category",
        "sanctioned_load_kw", "consumer_type", "location", "division", "source_file",
    ]
    extra_fields = [c for c in cleaned_df.columns if c not in canonical_fields]

    for _, row in cleaned_df.iterrows():
        consumer_id = str(row.get("consumer_id", "")).strip()
        billing_period = str(row.get("billing_period", "")).strip() if "billing_period" in row else None

        # upsert on (consumer_id, billing_period)
        if billing_period:
            existing = await db.execute(
                text("SELECT id FROM consumer_records WHERE consumer_id = :cid AND billing_period = :bp"),
                {"cid": consumer_id, "bp": billing_period},
            )
            if existing.fetchone():
                skipped += 1
                continue

        extra = {k: (None if bool(pd.isna(row[k])) else str(row[k])) for k in extra_fields if k in row.index}

        await db.execute(
            text("""
                INSERT INTO consumer_records
                  (consumer_id, billing_period, meter_reading_start, meter_reading_end,
                   units_consumed, billed_units, amount_billed, tariff_category,
                   sanctioned_load_kw, consumer_type, location, division, source_file, extra_fields,
                   ingested_at)
                VALUES
                  (:consumer_id, :billing_period, :mrs, :mre,
                   :uc, :bu, :ab, :tc,
                   :sl, :ct, :loc, :div, :sf, :ef,
                   CURRENT_TIMESTAMP)
            """),
            {
                "consumer_id": consumer_id,
                "billing_period": billing_period,
                "mrs": _safe_float(row.get("meter_reading_start")),
                "mre": _safe_float(row.get("meter_reading_end")),
                "uc": _safe_float(row.get("units_consumed")),
                "bu": _safe_float(row.get("billed_units")),
                "ab": _safe_float(row.get("amount_billed")),
                "tc": _str_or_none(row.get("tariff_category")),
                "sl": _safe_float(row.get("sanctioned_load_kw")),
                "ct": _str_or_none(row.get("consumer_type")),
                "loc": _str_or_none(row.get("location")),
                "div": _str_or_none(row.get("division")),
                "sf": file.filename,
                "ef": json.dumps(extra) if extra else None,
            },
        )
        inserted += 1

    await db.commit()
    report["inserted_rows"] = inserted
    report["skipped_duplicate_rows"] = skipped
    return JSONResponse({"success": True, "report": report})


@router.get("/consumers")
async def list_consumers(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List distinct consumers available in the database."""
    offset = (page - 1) * page_size
    base_q = "SELECT DISTINCT consumer_id FROM consumer_records"
    params: dict = {}
    if search:
        base_q += " WHERE consumer_id LIKE :search"
        params["search"] = f"%{search}%"
    base_q += " ORDER BY consumer_id LIMIT :limit OFFSET :offset"
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(text(base_q), params)
    consumers = [row[0] for row in result.fetchall()]

    # count total
    count_q = "SELECT COUNT(DISTINCT consumer_id) FROM consumer_records"
    count_params: dict = {}
    if search:
        count_q += " WHERE consumer_id LIKE :search"
        count_params["search"] = f"%{search}%"
    count_res = await db.execute(text(count_q), count_params)
    total = count_res.scalar() or 0

    return {"consumers": consumers, "total": total, "page": page, "page_size": page_size}


@router.get("/consumers/{consumer_id}/records")
async def get_consumer_records(consumer_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all billing records for a specific consumer."""
    result = await db.execute(
        text("SELECT * FROM consumer_records WHERE consumer_id = :cid ORDER BY billing_period"),
        {"cid": consumer_id},
    )
    rows = result.mappings().fetchall()
    if not rows:
        raise HTTPException(404, f"No records found for consumer '{consumer_id}'")
    return {"consumer_id": consumer_id, "records": [dict(r) for r in rows], "count": len(rows)}


@router.get("/stats")
async def dataset_stats(db: AsyncSession = Depends(get_db)):
    """Overall dataset statistics."""
    r = await db.execute(text("""
        SELECT
          COUNT(DISTINCT consumer_id) AS total_consumers,
          COUNT(*) AS total_records,
          MIN(billing_period) AS earliest_period,
          MAX(billing_period) AS latest_period,
          AVG(units_consumed) AS avg_consumption,
          COUNT(DISTINCT source_file) AS source_files
        FROM consumer_records
    """))
    row = r.mappings().fetchone()
    return dict(row) if row else {}


def _safe_float(val) -> Optional[float]:
    try:
        import numpy as np
        v = float(val)
        return None if (v != v) else v  # NaN check
    except (TypeError, ValueError):
        return None


def _str_or_none(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.lower() not in ("nan", "none", "") else None
