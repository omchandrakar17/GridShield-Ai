"""
SQLAlchemy ORM models for GridShield AI
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from services.database import Base


class ConsumerRecord(Base):
    """Stores raw ingested billing/meter records per consumer per period."""
    __tablename__ = "consumer_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    consumer_id = Column(String(64), index=True, nullable=False)
    billing_period = Column(String(20), nullable=False)   # YYYY-MM
    meter_reading_start = Column(Float, nullable=True)
    meter_reading_end = Column(Float, nullable=True)
    units_consumed = Column(Float, nullable=True)
    billed_units = Column(Float, nullable=True)
    amount_billed = Column(Float, nullable=True)
    tariff_category = Column(String(32), nullable=True)
    sanctioned_load_kw = Column(Float, nullable=True)
    consumer_type = Column(String(32), nullable=True)    # residential/commercial/industrial
    location = Column(String(128), nullable=True)
    division = Column(String(64), nullable=True)
    source_file = Column(String(256), nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    extra_fields = Column(JSON, nullable=True)            # store any additional dataset fields


class AnomalyResult(Base):
    """Stores computed anomaly detection results per consumer."""
    __tablename__ = "anomaly_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    consumer_id = Column(String(64), index=True, nullable=False)
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    fraud_risk_score = Column(Float, nullable=False)      # 0–100
    risk_level = Column(String(16), nullable=False)       # Low/Medium/High/Critical
    anomaly_flags = Column(JSON, nullable=True)           # list of detected anomaly types
    affected_periods = Column(JSON, nullable=True)        # billing periods implicated
    statistical_evidence = Column(JSON, nullable=True)    # z-scores, deviations, percentages
    ai_reasoning = Column(Text, nullable=True)            # watsonx narrative explanation
    recommended_action = Column(String(128), nullable=True)
    confidence_score = Column(Float, nullable=True)       # 0–1
    model_version = Column(String(32), nullable=True)
    agent_trace = Column(JSON, nullable=True)             # per-agent outputs


class InvestigationCase(Base):
    """Investigation case created for a flagged consumer."""
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), unique=True, nullable=False)
    consumer_id = Column(String(64), index=True, nullable=False)
    status = Column(String(32), default="Open")           # Open/Under Investigation/Inspection Required/Resolved
    priority = Column(String(16), nullable=True)          # Low/Medium/High/Critical
    fraud_risk_score = Column(Float, nullable=True)
    risk_level = Column(String(16), nullable=True)
    assigned_to = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    anomaly_result_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)


class CaseEvent(Base):
    """Audit trail / timeline events for an investigation case."""
    __tablename__ = "case_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), index=True, nullable=False)
    event_type = Column(String(64), nullable=False)       # status_change/note_added/ai_analysis/assigned/resolved
    description = Column(Text, nullable=False)
    performed_by = Column(String(64), default="system")
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
