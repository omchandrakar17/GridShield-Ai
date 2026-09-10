"""
Case management API routes.
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from services.database import get_db

logger = logging.getLogger("gridshield.routes.cases")
router = APIRouter()


class CreateCaseRequest(BaseModel):
    consumer_id: str
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class UpdateCaseRequest(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
    resolution_notes: Optional[str] = None


class AddEventRequest(BaseModel):
    event_type: str
    description: str
    performed_by: Optional[str] = "investigator"
    metadata: Optional[dict] = None


@router.post("/")
async def create_case(req: CreateCaseRequest, db: AsyncSession = Depends(get_db)):
    """Create an investigation case for a flagged consumer."""
    # check consumer exists
    r = await db.execute(
        text("SELECT COUNT(*) FROM consumer_records WHERE consumer_id = :cid"),
        {"cid": req.consumer_id},
    )
    if not r.scalar():
        raise HTTPException(404, f"Consumer '{req.consumer_id}' not found in database")

    # check for duplicate open case
    r = await db.execute(
        text("SELECT case_id FROM investigation_cases WHERE consumer_id = :cid AND status != 'Resolved'"),
        {"cid": req.consumer_id},
    )
    dup = r.fetchone()
    if dup:
        raise HTTPException(409, f"Open case already exists for consumer '{req.consumer_id}': {dup[0]}")

    # fetch anomaly result if available
    r = await db.execute(
        text("SELECT fraud_risk_score, risk_level FROM anomaly_results WHERE consumer_id = :cid"),
        {"cid": req.consumer_id},
    )
    anomaly_row = r.fetchone()
    score = anomaly_row[0] if anomaly_row else None
    level = anomaly_row[1] if anomaly_row else None
    priority = req.priority or level or "Medium"

    case_id = f"GS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    await db.execute(text("""
        INSERT INTO investigation_cases
          (case_id, consumer_id, status, priority, fraud_risk_score, risk_level, assigned_to, notes,
           created_at, updated_at)
        VALUES
          (:case_id, :cid, 'Open', :priority, :score, :level, :assigned_to, :notes,
           CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """), {
        "case_id": case_id,
        "cid": req.consumer_id,
        "priority": priority,
        "score": score,
        "level": level,
        "assigned_to": req.assigned_to,
        "notes": req.notes,
    })

    await db.execute(text("""
        INSERT INTO case_events (case_id, event_type, description, performed_by, created_at)
        VALUES (:case_id, 'case_created', :desc, 'system', CURRENT_TIMESTAMP)
    """), {
        "case_id": case_id,
        "desc": f"Case created for consumer {req.consumer_id}. Priority: {priority}.",
    })

    await db.commit()
    return {"case_id": case_id, "consumer_id": req.consumer_id, "status": "Open", "priority": priority}


@router.get("/")
async def list_cases(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    q = "SELECT * FROM investigation_cases WHERE 1=1"
    params: dict = {}
    if status:
        q += " AND status = :status"
        params["status"] = status
    if risk_level:
        q += " AND risk_level = :risk_level"
        params["risk_level"] = risk_level
    q += " ORDER BY created_at DESC LIMIT :lim OFFSET :off"
    params["lim"] = page_size
    params["off"] = offset

    r = await db.execute(text(q), params)
    cases = [dict(row._mapping) for row in r.fetchall()]

    count_q = "SELECT COUNT(*) FROM investigation_cases WHERE 1=1"
    count_params: dict = {}
    if status:
        count_q += " AND status = :status"
        count_params["status"] = status
    if risk_level:
        count_q += " AND risk_level = :risk_level"
        count_params["risk_level"] = risk_level
    cr = await db.execute(text(count_q), count_params)
    total = cr.scalar() or 0

    return {"cases": cases, "total": total, "page": page, "page_size": page_size}


@router.get("/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT * FROM investigation_cases WHERE case_id = :cid"),
        {"cid": case_id},
    )
    row = r.mappings().fetchone()
    if not row:
        raise HTTPException(404, f"Case '{case_id}' not found")
    case = dict(row)

    # include timeline
    r2 = await db.execute(
        text("SELECT * FROM case_events WHERE case_id = :cid ORDER BY created_at ASC"),
        {"cid": case_id},
    )
    events = [dict(ev._mapping) for ev in r2.fetchall()]
    case["timeline"] = events

    return case


@router.patch("/{case_id}")
async def update_case(case_id: str, req: UpdateCaseRequest, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT * FROM investigation_cases WHERE case_id = :cid"),
        {"cid": case_id},
    )
    row = r.mappings().fetchone()
    if not row:
        raise HTTPException(404, f"Case '{case_id}' not found")

    updates = []
    params: dict = {"cid": case_id}
    event_parts = []

    if req.status:
        updates.append("status = :status")
        params["status"] = req.status
        event_parts.append(f"Status changed to '{req.status}'")
        if req.status == "Resolved":
            updates.append("resolved_at = CURRENT_TIMESTAMP")
    if req.assigned_to:
        updates.append("assigned_to = :assigned_to")
        params["assigned_to"] = req.assigned_to
        event_parts.append(f"Assigned to '{req.assigned_to}'")
    if req.notes is not None:
        updates.append("notes = :notes")
        params["notes"] = req.notes
        event_parts.append("Notes updated")
    if req.resolution_notes is not None:
        updates.append("resolution_notes = :resolution_notes")
        params["resolution_notes"] = req.resolution_notes

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        await db.execute(
            text(f"UPDATE investigation_cases SET {', '.join(updates)} WHERE case_id = :cid"),
            params,
        )

    if event_parts:
        await db.execute(text("""
            INSERT INTO case_events (case_id, event_type, description, performed_by, created_at)
            VALUES (:case_id, 'status_change', :desc, 'investigator', CURRENT_TIMESTAMP)
        """), {"case_id": case_id, "desc": "; ".join(event_parts)})

    await db.commit()
    return {"success": True, "case_id": case_id}


@router.post("/{case_id}/events")
async def add_case_event(case_id: str, req: AddEventRequest, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT id FROM investigation_cases WHERE case_id = :cid"),
        {"cid": case_id},
    )
    if not r.fetchone():
        raise HTTPException(404, f"Case '{case_id}' not found")

    await db.execute(text("""
        INSERT INTO case_events (case_id, event_type, description, performed_by, event_metadata, created_at)
        VALUES (:case_id, :event_type, :description, :performed_by, :metadata, CURRENT_TIMESTAMP)
    """), {
        "case_id": case_id,
        "event_type": req.event_type,
        "description": req.description,
        "performed_by": req.performed_by,
        "metadata": json.dumps(req.metadata) if req.metadata else None,
    })
    await db.commit()
    return {"success": True}


@router.get("/{case_id}/timeline")
async def case_timeline(case_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        text("SELECT * FROM case_events WHERE case_id = :cid ORDER BY created_at ASC"),
        {"cid": case_id},
    )
    events = [dict(ev._mapping) for ev in r.fetchall()]
    return {"case_id": case_id, "events": events}
