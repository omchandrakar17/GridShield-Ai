"""
Analysis API routes – consumer profiling and anomaly detection.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.database import get_db
from services.analysis import build_consumer_profile
from services.anomaly_detection import detect_anomalies, calculate_fraud_risk_score, recommended_action

logger = logging.getLogger("gridshield.routes.analysis")
router = APIRouter()


async def _fetch_consumer_records(consumer_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        text("SELECT * FROM consumer_records WHERE consumer_id = :cid ORDER BY billing_period"),
        {"cid": consumer_id},
    )
    rows = result.mappings().fetchall()
    return [dict(r) for r in rows]


@router.get("/consumer/{consumer_id}/profile")
async def consumer_profile(consumer_id: str, db: AsyncSession = Depends(get_db)):
    """Build and return the consumption profile for one consumer."""
    records = await _fetch_consumer_records(consumer_id, db)
    if not records:
        raise HTTPException(404, f"No records found for consumer '{consumer_id}'")
    profile = build_consumer_profile(records)
    if not profile:
        raise HTTPException(422, "Insufficient data to build profile (no consumption column found)")
    return profile


@router.get("/consumer/{consumer_id}/anomalies")
async def consumer_anomalies(consumer_id: str, db: AsyncSession = Depends(get_db)):
    """Run anomaly detection on a consumer and return flags + risk score."""
    records = await _fetch_consumer_records(consumer_id, db)
    if not records:
        raise HTTPException(404, f"No records found for consumer '{consumer_id}'")

    profile = build_consumer_profile(records)
    if not profile:
        raise HTTPException(422, "Insufficient data to build profile")

    anomaly_result = detect_anomalies(profile)
    risk = calculate_fraud_risk_score(anomaly_result, profile)

    return {
        "consumer_id": consumer_id,
        "profile_summary": {
            "periods_available": profile["periods_available"],
            "mean_consumption": profile["mean_consumption"],
            "std_consumption": profile["std_consumption"],
        },
        "anomaly_result": anomaly_result,
        "risk_assessment": risk,
        "recommended_action": recommended_action(risk["risk_level"], anomaly_result.get("anomaly_types", [])),
    }


@router.get("/dashboard")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Aggregate dashboard statistics computed from actual DB data.
    """
    # total consumers
    r = await db.execute(text("SELECT COUNT(DISTINCT consumer_id) FROM consumer_records"))
    total_consumers = r.scalar() or 0

    # anomaly distribution (from stored anomaly_results)
    r = await db.execute(text("""
        SELECT risk_level, COUNT(*) as cnt
        FROM anomaly_results
        GROUP BY risk_level
    """))
    risk_distribution = {row[0]: row[1] for row in r.fetchall()}

    # total analyzed
    r = await db.execute(text("SELECT COUNT(DISTINCT consumer_id) FROM anomaly_results"))
    total_analyzed = r.scalar() or 0

    # high + critical risk
    r = await db.execute(text("""
        SELECT COUNT(*) FROM anomaly_results WHERE risk_level IN ('High', 'Critical')
    """))
    high_risk_count = r.scalar() or 0

    # total anomaly flags (sum across all results)
    r = await db.execute(text("SELECT SUM(json_array_length(anomaly_flags)) FROM anomaly_results WHERE anomaly_flags IS NOT NULL"))
    try:
        total_flags = r.scalar() or 0
    except Exception:
        total_flags = 0

    # open investigations
    r = await db.execute(text("SELECT COUNT(*) FROM investigation_cases WHERE status != 'Resolved'"))
    open_cases = r.scalar() or 0

    # recent flagged consumers (last 10 analyzed with any risk)
    r = await db.execute(text("""
        SELECT consumer_id, fraud_risk_score, risk_level, analysis_timestamp, recommended_action
        FROM anomaly_results
        ORDER BY analysis_timestamp DESC
        LIMIT 10
    """))
    recent_flagged = [dict(row._mapping) for row in r.fetchall()]

    # risk trend (last 6 months of analysis timestamps)
    r = await db.execute(text("""
        SELECT substr(analysis_timestamp, 1, 7) AS month,
               COUNT(*) AS total,
               SUM(CASE WHEN risk_level IN ('High','Critical') THEN 1 ELSE 0 END) AS high_risk
        FROM anomaly_results
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """))
    risk_trend = [dict(row._mapping) for row in r.fetchall()]

    return {
        "total_consumers": total_consumers,
        "total_analyzed": total_analyzed,
        "total_anomaly_flags": total_flags,
        "high_risk_count": high_risk_count,
        "open_cases": open_cases,
        "risk_distribution": risk_distribution,
        "recent_flagged": recent_flagged,
        "risk_trend": risk_trend,
    }


@router.post("/run-batch")
async def run_batch_analysis(
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Run anomaly detection on all consumers in the database (or up to `limit`).
    Stores results in anomaly_results table.
    """
    r = await db.execute(text(
        "SELECT DISTINCT consumer_id FROM consumer_records ORDER BY consumer_id LIMIT :lim"
    ), {"lim": limit})
    consumer_ids = [row[0] for row in r.fetchall()]

    if not consumer_ids:
        raise HTTPException(404, "No consumer records found. Please upload data first.")

    processed = 0
    errors = []

    for cid in consumer_ids:
        try:
            records = await _fetch_consumer_records(cid, db)
            profile = build_consumer_profile(records)
            if not profile:
                continue
            anomaly_result = detect_anomalies(profile)
            risk = calculate_fraud_risk_score(anomaly_result, profile)
            action = recommended_action(risk["risk_level"], anomaly_result.get("anomaly_types", []))

            import json
            # upsert anomaly result
            existing = await db.execute(
                text("SELECT id FROM anomaly_results WHERE consumer_id = :cid"),
                {"cid": cid},
            )
            ex_row = existing.fetchone()

            payload = {
                "cid": cid,
                "score": risk["fraud_risk_score"],
                "level": risk["risk_level"],
                "flags": json.dumps(anomaly_result.get("flags", [])),
                "periods": json.dumps(anomaly_result.get("affected_periods", [])),
                "evidence": json.dumps(anomaly_result.get("statistical_evidence", {})),
                "action": action,
                "conf": risk.get("confidence_score", 0),
            }

            if ex_row:
                await db.execute(text("""
                    UPDATE anomaly_results SET
                      fraud_risk_score=:score, risk_level=:level,
                      anomaly_flags=:flags, affected_periods=:periods,
                      statistical_evidence=:evidence, recommended_action=:action,
                      confidence_score=:conf,
                      analysis_timestamp=CURRENT_TIMESTAMP
                    WHERE consumer_id=:cid
                """), payload)
            else:
                await db.execute(text("""
                    INSERT INTO anomaly_results
                      (consumer_id, fraud_risk_score, risk_level, anomaly_flags,
                       affected_periods, statistical_evidence, recommended_action, confidence_score,
                       analysis_timestamp)
                    VALUES
                      (:cid, :score, :level, :flags, :periods, :evidence, :action, :conf,
                       CURRENT_TIMESTAMP)
                """), payload)

            processed += 1
        except Exception as e:
            errors.append({"consumer_id": cid, "error": str(e)})

    await db.commit()
    return {
        "processed": processed,
        "total_consumers": len(consumer_ids),
        "errors": errors[:10],
    }


@router.get("/anomaly-list")
async def list_anomalies(
    risk_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List stored anomaly results with optional risk-level filter."""
    offset = (page - 1) * page_size
    q = "SELECT * FROM anomaly_results"
    params: dict = {}
    if risk_level:
        q += " WHERE risk_level = :level"
        params["level"] = risk_level
    q += " ORDER BY fraud_risk_score DESC LIMIT :lim OFFSET :off"
    params["lim"] = page_size
    params["off"] = offset

    r = await db.execute(text(q), params)
    rows = [dict(row._mapping) for row in r.fetchall()]

    count_q = "SELECT COUNT(*) FROM anomaly_results"
    count_params: dict = {}
    if risk_level:
        count_q += " WHERE risk_level = :level"
        count_params["level"] = risk_level
    cr = await db.execute(text(count_q), count_params)
    total = cr.scalar() or 0

    return {"results": rows, "total": total, "page": page, "page_size": page_size}
