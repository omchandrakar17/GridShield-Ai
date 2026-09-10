"""
Report generation API routes.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.database import get_db
from services.report_service import generate_pdf_report
from services.analysis import build_consumer_profile

logger = logging.getLogger("gridshield.routes.reports")
router = APIRouter()


@router.get("/{case_id}/pdf")
async def download_case_report(case_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and download a PDF investigation report for a case."""

    # fetch case
    r = await db.execute(
        text("SELECT * FROM investigation_cases WHERE case_id = :cid"),
        {"cid": case_id},
    )
    case_row = r.mappings().fetchone()
    if not case_row:
        raise HTTPException(404, f"Case '{case_id}' not found")
    case = dict(case_row)

    # fetch anomaly result
    r = await db.execute(
        text("SELECT * FROM anomaly_results WHERE consumer_id = :cid"),
        {"cid": case["consumer_id"]},
    )
    anom_row = r.mappings().fetchone()
    anomaly = dict(anom_row) if anom_row else {}

    # fetch consumer profile
    r = await db.execute(
        text("SELECT * FROM consumer_records WHERE consumer_id = :cid ORDER BY billing_period"),
        {"cid": case["consumer_id"]},
    )
    records = [dict(rec._mapping) for rec in r.fetchall()]
    profile = build_consumer_profile(records) if records else {}

    # fetch timeline events
    r = await db.execute(
        text("SELECT * FROM case_events WHERE case_id = :cid ORDER BY created_at ASC"),
        {"cid": case_id},
    )
    events = [dict(ev._mapping) for ev in r.fetchall()]

    import json as _json

    # parse JSON string columns (SQLite stores JSON as text)
    def _parse_json_col(val):
        if isinstance(val, str):
            try:
                return _json.loads(val)
            except Exception:
                return val
        return val

    anomaly["anomaly_flags"] = _parse_json_col(anomaly.get("anomaly_flags")) or []
    agent_trace = _parse_json_col(anomaly.get("agent_trace"))

    try:
        pdf_bytes = generate_pdf_report(case, anomaly, profile or {}, events, agent_trace)
    except Exception as e:
        raise HTTPException(500, f"PDF generation error: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="gridshield-{case_id}.pdf"'},
    )


@router.get("/{case_id}/json")
async def get_case_report_json(case_id: str, db: AsyncSession = Depends(get_db)):
    """Return a structured JSON investigation report for a case."""
    r = await db.execute(
        text("SELECT * FROM investigation_cases WHERE case_id = :cid"),
        {"cid": case_id},
    )
    case_row = r.mappings().fetchone()
    if not case_row:
        raise HTTPException(404, f"Case '{case_id}' not found")
    case = dict(case_row)

    r = await db.execute(
        text("SELECT * FROM anomaly_results WHERE consumer_id = :cid"),
        {"cid": case["consumer_id"]},
    )
    anom_row = r.mappings().fetchone()
    anomaly = dict(anom_row) if anom_row else {}

    r = await db.execute(
        text("SELECT * FROM consumer_records WHERE consumer_id = :cid ORDER BY billing_period"),
        {"cid": case["consumer_id"]},
    )
    records = [dict(rec._mapping) for rec in r.fetchall()]
    profile = build_consumer_profile(records) if records else {}

    r = await db.execute(
        text("SELECT * FROM case_events WHERE case_id = :cid ORDER BY created_at ASC"),
        {"cid": case_id},
    )
    events = [dict(ev._mapping) for ev in r.fetchall()]

    return {
        "case": case,
        "anomaly": anomaly,
        "consumer_profile": profile,
        "billing_records": records,
        "timeline": events,
        "disclaimer": "AI-assisted investigation report – not a legal determination of fraud.",
    }
