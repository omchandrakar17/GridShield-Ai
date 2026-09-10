"""
IBM watsonx.ai agent integration for GridShield AI.

Architecture:
  DataAnalysisAgent      – interprets billing/consumption profile
  AnomalyDetectionAgent  – reviews statistical anomaly flags
  FraudInvestigationAgent– correlates indicators and generates investigation narrative
  ExplainabilityAgent    – produces structured evidence summary
  DecisionSupportAgent   – synthesises risk level, priority, and recommended action

Each agent calls watsonx.ai (granite-13b-chat-v2 or user-configured model) via the
IBM watsonx-ai Python SDK. If the SDK / credentials are unavailable, the system
returns a clearly marked "AI UNAVAILABLE" message rather than fabricating results.
"""
import os
import json
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("gridshield.agents")

_watsonx_available = False
_wx_client = None

def _init_watsonx():
    global _watsonx_available, _wx_client
    api_key    = os.getenv("IBM_WATSONX_API_KEY", "")
    project_id = os.getenv("IBM_WATSONX_PROJECT_ID", "")
    url        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or api_key == "your_ibm_cloud_api_key_here":
        logger.warning("IBM_WATSONX_API_KEY not configured – AI agent narratives unavailable")
        return

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(api_key=api_key, url=url)
        _wx_client = {
            "credentials": credentials,
            "project_id": project_id,
            "model_id": os.getenv("IBM_WATSONX_MODEL_ID", "ibm/granite-13b-chat-v2"),
        }
        _watsonx_available = True
        logger.info("IBM watsonx.ai client initialised (model: %s)", _wx_client["model_id"])
    except ImportError:
        logger.warning("ibm-watsonx-ai package not installed – install it to enable AI narratives")
    except Exception as e:
        logger.error("Failed to initialise IBM watsonx.ai client: %s", e)


_init_watsonx()


def _call_watsonx(prompt: str, max_tokens: int = 600) -> Optional[str]:
    """Make a single inference call to watsonx.ai. Returns text or None."""
    if not _watsonx_available or _wx_client is None:
        return None
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        model = ModelInference(
            model_id=_wx_client["model_id"],
            credentials=_wx_client["credentials"],
            project_id=_wx_client["project_id"],
            params={
                GenParams.MAX_NEW_TOKENS: max_tokens,
                GenParams.TEMPERATURE: 0.3,
                GenParams.REPETITION_PENALTY: 1.1,
            },
        )
        response = model.generate_text(prompt=prompt)
        return response.strip() if isinstance(response, str) else None
    except Exception as e:
        logger.error("watsonx.ai inference error: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Agent implementations
# ─────────────────────────────────────────────────────────────────────────────

class DataAnalysisAgent:
    """Interprets the consumer billing/consumption profile."""

    name = "DataAnalysisAgent"

    def run(self, profile: dict) -> dict:
        prompt = f"""You are a data analysis agent for an electricity fraud detection system.

Analyze the following consumer consumption profile and provide a concise behavioral summary.

Consumer ID: {profile.get('consumer_id')}
Type: {profile.get('consumer_type', 'unknown')}
Category: {profile.get('tariff_category', 'unknown')}
Location: {profile.get('location', 'unknown')}
Periods of data: {profile.get('periods_available')}
Mean consumption: {profile.get('mean_consumption')} kWh
Std deviation: {profile.get('std_consumption')} kWh
Min consumption: {profile.get('min_consumption')} kWh
Max consumption: {profile.get('max_consumption')} kWh
Coefficient of variation: {profile.get('coefficient_of_variation')}
Average MoM change: {profile.get('avg_mom_change_pct')}%
Trend slope: {profile.get('trend_slope')} kWh/period

In 2–3 sentences, describe what is normal about this consumer's electricity usage and whether the overall pattern raises any concerns.
Focus only on facts from the data above. Do not speculate beyond the provided figures."""

        text = _call_watsonx(prompt, max_tokens=300)
        return {
            "agent": self.name,
            "status": "completed" if text else "ai_unavailable",
            "output": text or (
                f"Consumer {profile.get('consumer_id')} has {profile.get('periods_available')} "
                f"periods of data. Mean consumption: {profile.get('mean_consumption')} kWh "
                f"(CV={profile.get('coefficient_of_variation'):.2f}). "
                "IBM watsonx.ai narrative unavailable – configure IBM_WATSONX_API_KEY."
            ),
        }


class AnomalyDetectionAgent:
    """Reviews statistical anomaly flags and contextualises them."""

    name = "AnomalyDetectionAgent"

    def run(self, anomaly_result: dict, profile: dict) -> dict:
        flags = anomaly_result.get("flags", [])
        if not flags:
            return {
                "agent": self.name,
                "status": "completed",
                "output": "No statistical anomalies detected for this consumer.",
            }

        flag_summary = "\n".join(
            f"  - [{f['type']}] ({f.get('severity','?')}) {f['description']}"
            for f in flags[:8]  # cap to avoid token overrun
        )

        prompt = f"""You are an anomaly detection agent for an electricity fraud detection system.

The following anomalies were detected for consumer {profile.get('consumer_id')}:

{flag_summary}

Consumer historical mean: {profile.get('mean_consumption')} kWh/period

For each anomaly type present, briefly explain what it might indicate in the context of electricity theft or meter fraud.
Be factual and evidence-based. Do not fabricate data. If an anomaly could have a legitimate explanation, acknowledge it."""

        text = _call_watsonx(prompt, max_tokens=400)
        default = (
            f"Detected {len(flags)} anomaly flag(s) across "
            f"{len(anomaly_result.get('affected_periods', []))} period(s). "
            "Anomaly types: " + ", ".join(anomaly_result.get("anomaly_types", [])) + ". "
            "IBM watsonx.ai narrative unavailable – configure IBM_WATSONX_API_KEY for AI explanations."
        )
        return {
            "agent": self.name,
            "status": "completed" if text else "ai_unavailable",
            "output": text or default,
            "anomaly_count": len(flags),
            "anomaly_types": anomaly_result.get("anomaly_types", []),
        }


class FraudInvestigationAgent:
    """Correlates multiple indicators and produces an investigation narrative."""

    name = "FraudInvestigationAgent"

    def run(self, anomaly_result: dict, risk_assessment: dict, profile: dict) -> dict:
        flags = anomaly_result.get("flags", [])
        score = risk_assessment.get("fraud_risk_score", 0)
        level = risk_assessment.get("risk_level", "Low")

        if not flags:
            return {
                "agent": self.name,
                "status": "completed",
                "output": "No indicators requiring investigation were found.",
            }

        flag_types = anomaly_result.get("anomaly_types", [])
        affected = anomaly_result.get("affected_periods", [])
        breakdown = risk_assessment.get("scoring_breakdown", {})

        prompt = f"""You are a fraud investigation agent for an electricity distribution utility.

Consumer: {profile.get('consumer_id')}
Risk Score: {score}/100 (Level: {level})
Anomaly types detected: {', '.join(flag_types)}
Affected billing periods: {', '.join(str(p) for p in affected[:6])}
Score breakdown: {json.dumps(breakdown)}

Provide a concise investigation assessment (3–5 sentences) that:
1. States what evidence exists for potential fraud or irregularity
2. Notes which anomaly types are most significant and why
3. Suggests what a field investigator should look for
4. Notes any alternative legitimate explanations that should be ruled out

Base your assessment strictly on the data provided. Do not invent facts."""

        text = _call_watsonx(prompt, max_tokens=500)
        default = (
            f"Risk score {score}/100 ({level}). "
            f"Key anomaly indicators: {', '.join(flag_types)}. "
            f"Affecting {len(affected)} billing period(s). "
            "IBM watsonx.ai narrative unavailable – configure IBM_WATSONX_API_KEY for full investigation narrative."
        )
        return {
            "agent": self.name,
            "status": "completed" if text else "ai_unavailable",
            "output": text or default,
        }


class ExplainabilityAgent:
    """Converts analysis into structured, human-readable evidence."""

    name = "ExplainabilityAgent"

    def run(
        self,
        profile: dict,
        anomaly_result: dict,
        risk_assessment: dict,
        investigation_output: str,
    ) -> dict:
        flags = anomaly_result.get("flags", [])
        score = risk_assessment.get("fraud_risk_score", 0)
        level = risk_assessment.get("risk_level", "Low")
        confidence = risk_assessment.get("confidence_score", 0)

        # build evidence items from flags – always data-driven
        evidence_items = []
        for flag in flags:
            evidence_items.append({
                "type": flag["type"],
                "severity": flag.get("severity", "Medium"),
                "period": flag.get("period", ""),
                "description": flag["description"],
                "confidence": _flag_confidence(flag, profile),
            })

        prompt = f"""You are an explainability agent for an electricity fraud detection system.

Summarise the following investigation findings in plain language suitable for a utility investigator:

Consumer: {profile.get('consumer_id')}
Risk Level: {level} ({score}/100)
Number of anomaly flags: {len(flags)}
Evidence from investigation agent: {investigation_output[:300]}

Provide a clear 2–3 sentence plain-language summary that:
- States the overall risk assessment result
- Highlights the single most concerning finding
- Recommends what the investigator should prioritise first"""

        text = _call_watsonx(prompt, max_tokens=300)
        return {
            "agent": self.name,
            "status": "completed" if text else "ai_unavailable",
            "plain_language_summary": text or (
                f"This consumer has a {level} fraud investigation risk ({score}/100) "
                f"based on {len(flags)} detected anomaly flag(s). "
                "IBM watsonx.ai narrative unavailable – configure IBM_WATSONX_API_KEY."
            ),
            "evidence_items": evidence_items,
            "risk_score": score,
            "risk_level": level,
            "confidence_score": confidence,
        }


class DecisionSupportAgent:
    """Synthesises findings into actionable decision support."""

    name = "DecisionSupportAgent"

    def run(
        self,
        profile: dict,
        anomaly_result: dict,
        risk_assessment: dict,
        explainability_output: dict,
    ) -> dict:
        from services.anomaly_detection import recommended_action

        score = risk_assessment.get("fraud_risk_score", 0)
        level = risk_assessment.get("risk_level", "Low")
        anomaly_types = anomaly_result.get("anomaly_types", [])
        action = recommended_action(level, anomaly_types)

        priority_map = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}
        priority_label = {"Critical": "P1 – Immediate", "High": "P2 – Urgent",
                          "Medium": "P3 – Standard", "Low": "P4 – Monitor"}

        return {
            "agent": self.name,
            "status": "completed",
            "fraud_risk_score": score,
            "risk_level": level,
            "investigation_priority": priority_map.get(level, 4),
            "investigation_priority_label": priority_label.get(level, "P4 – Monitor"),
            "key_evidence": [e["description"] for e in explainability_output.get("evidence_items", [])[:5]],
            "recommended_action": action,
            "anomaly_count": anomaly_result.get("flag_count", 0),
            "affected_periods": anomaly_result.get("affected_periods", []),
            "confidence_score": risk_assessment.get("confidence_score", 0),
            "disclaimer": "AI-assisted fraud risk assessment – not a legal determination of fraud.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator: run full multi-agent pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_agent_pipeline(profile: dict, anomaly_result: dict, risk_assessment: dict) -> dict:
    """
    Execute all five agents sequentially (each builds on prior output).
    Returns full agent_trace suitable for storage and display.
    """
    started_at = datetime.utcnow().isoformat()
    trace: dict = {"started_at": started_at, "agents": []}

    # Agent 1 – Data Analysis
    agent1 = DataAnalysisAgent()
    a1_out = agent1.run(profile)
    trace["agents"].append(a1_out)

    # Agent 2 – Anomaly Detection
    agent2 = AnomalyDetectionAgent()
    a2_out = agent2.run(anomaly_result, profile)
    trace["agents"].append(a2_out)

    # Agent 3 – Fraud Investigation
    agent3 = FraudInvestigationAgent()
    a3_out = agent3.run(anomaly_result, risk_assessment, profile)
    trace["agents"].append(a3_out)

    # Agent 4 – Explainability
    agent4 = ExplainabilityAgent()
    a4_out = agent4.run(profile, anomaly_result, risk_assessment, a3_out["output"])
    trace["agents"].append(a4_out)

    # Agent 5 – Decision Support
    agent5 = DecisionSupportAgent()
    a5_out = agent5.run(profile, anomaly_result, risk_assessment, a4_out)
    trace["agents"].append(a5_out)

    trace["completed_at"] = datetime.utcnow().isoformat()
    trace["watsonx_available"] = _watsonx_available
    trace["model_id"] = _wx_client["model_id"] if _wx_client else "not_configured"
    trace["final_decision"] = a5_out

    return trace


def _flag_confidence(flag: dict, profile: dict) -> float:
    """Estimate confidence in a flag based on data quality and sample size."""
    base = {"HIGH_ZSCORE": 0.80, "SUDDEN_DROP": 0.75, "SUDDEN_SPIKE": 0.72,
            "ZERO_CONSUMPTION": 0.85, "BILLING_MISMATCH": 0.90,
            "METER_GAP": 0.92, "HIGH_VARIABILITY": 0.65}
    base_conf = base.get(flag.get("type", ""), 0.60)
    n_periods = profile.get("periods_available", 1)
    # more data → higher confidence
    data_factor = min(n_periods / 12, 1.0)
    return round(base_conf * 0.5 + base_conf * 0.5 * data_factor, 3)
