"""
AI Agents API routes – trigger full agentic investigation pipeline.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.database import get_db
from services.analysis import build_consumer_profile
from services.anomaly_detection import detect_anomalies, calculate_fraud_risk_score, recommended_action
from agents.watsonx_agents import run_agent_pipeline

logger = logging.getLogger("gridshield.routes.agents")
router = APIRouter()


@router.post("/investigate/{consumer_id}")
async def run_investigation(consumer_id: str, db: AsyncSession = Depends(get_db)):
    """
    Run the full 5-agent investigation pipeline for a consumer.
    Results are stored and returned.
    """
    # fetch records
    r = await db.execute(
        text("SELECT * FROM consumer_records WHERE consumer_id = :cid ORDER BY billing_period"),
        {"cid": consumer_id},
    )
    records = [dict(row._mapping) for row in r.fetchall()]
    if not records:
        raise HTTPException(404, f"No records found for consumer '{consumer_id}'")

    profile = build_consumer_profile(records)
    if not profile:
        raise HTTPException(422, "Insufficient data to build profile for investigation")

    anomaly_result = detect_anomalies(profile)
    risk_assessment = calculate_fraud_risk_score(anomaly_result, profile)
    action = recommended_action(risk_assessment["risk_level"], anomaly_result.get("anomaly_types", []))

    # run multi-agent pipeline
    agent_trace = run_agent_pipeline(profile, anomaly_result, risk_assessment)
    final = agent_trace.get("final_decision", {})

    # build AI reasoning narrative from agents
    narratives = []
    for ag in agent_trace.get("agents", []):
        narratives.append(f"[{ag.get('agent')}]: {ag.get('output', ag.get('plain_language_summary', ''))}")
    ai_reasoning = "\n\n".join(narratives)

    # store/update anomaly result with agent trace
    existing = await db.execute(
        text("SELECT id FROM anomaly_results WHERE consumer_id = :cid"),
        {"cid": consumer_id},
    )
    ex_row = existing.fetchone()

    payload = {
        "cid": consumer_id,
        "score": risk_assessment["fraud_risk_score"],
        "level": risk_assessment["risk_level"],
        "flags": json.dumps(anomaly_result.get("flags", [])),
        "periods": json.dumps(anomaly_result.get("affected_periods", [])),
        "evidence": json.dumps(anomaly_result.get("statistical_evidence", {})),
        "reasoning": ai_reasoning,
        "action": final.get("recommended_action", action),
        "conf": risk_assessment.get("confidence_score", 0),
        "trace": json.dumps(agent_trace),
        "model": agent_trace.get("model_id", "not_configured"),
    }

    if ex_row:
        await db.execute(text("""
            UPDATE anomaly_results SET
              fraud_risk_score=:score, risk_level=:level,
              anomaly_flags=:flags, affected_periods=:periods,
              statistical_evidence=:evidence, ai_reasoning=:reasoning,
              recommended_action=:action, confidence_score=:conf,
              agent_trace=:trace, model_version=:model,
              analysis_timestamp=CURRENT_TIMESTAMP
            WHERE consumer_id=:cid
        """), payload)
    else:
        await db.execute(text("""
            INSERT INTO anomaly_results
              (consumer_id, fraud_risk_score, risk_level, anomaly_flags, affected_periods,
               statistical_evidence, ai_reasoning, recommended_action, confidence_score,
               agent_trace, model_version, analysis_timestamp)
            VALUES
              (:cid, :score, :level, :flags, :periods,
               :evidence, :reasoning, :action, :conf,
               :trace, :model, CURRENT_TIMESTAMP)
        """), payload)

    # if a case is open for this consumer, add an event
    r = await db.execute(
        text("SELECT case_id FROM investigation_cases WHERE consumer_id = :cid AND status != 'Resolved'"),
        {"cid": consumer_id},
    )
    open_case = r.fetchone()
    if open_case:
        await db.execute(text("""
            INSERT INTO case_events (case_id, event_type, description, performed_by, event_metadata, created_at)
            VALUES (:case_id, 'ai_analysis', :desc, 'GridShield AI Agent Pipeline', :meta, CURRENT_TIMESTAMP)
        """), {
            "case_id": open_case[0],
            "desc": f"AI investigation completed. Risk: {risk_assessment['risk_level']} ({risk_assessment['fraud_risk_score']}/100). "
                    f"Anomalies: {', '.join(anomaly_result.get('anomaly_types', []))}.",
            "meta": json.dumps({"risk_score": risk_assessment["fraud_risk_score"],
                                "risk_level": risk_assessment["risk_level"],
                                "watsonx_available": agent_trace.get("watsonx_available")}),
        })

    await db.commit()

    return {
        "consumer_id": consumer_id,
        "investigation_complete": True,
        "risk_assessment": risk_assessment,
        "anomaly_summary": {
            "flag_count": anomaly_result.get("flag_count", 0),
            "anomaly_types": anomaly_result.get("anomaly_types", []),
            "affected_periods": anomaly_result.get("affected_periods", []),
        },
        "agent_trace": agent_trace,
        "recommended_action": final.get("recommended_action", action),
        "ai_reasoning": ai_reasoning,
        "disclaimer": "AI-assisted investigation priority. Not a legal fraud determination.",
    }


@router.get("/status")
async def agent_status():
    """Check IBM watsonx.ai connectivity status."""
    from agents.watsonx_agents import _watsonx_available, _wx_client
    return {
        "watsonx_configured": _watsonx_available,
        "model_id": _wx_client["model_id"] if _wx_client else "not_configured",
        "required_env_vars": [
            "IBM_WATSONX_API_KEY",
            "IBM_WATSONX_PROJECT_ID",
            "IBM_WATSONX_URL",
        ],
        "note": (
            "Configure IBM_WATSONX_API_KEY and IBM_WATSONX_PROJECT_ID in .env to enable "
            "AI narrative generation via IBM watsonx.ai granite models. "
            "Statistical anomaly detection runs regardless of AI availability."
        ),
    }
