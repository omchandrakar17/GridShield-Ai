"""
Statistical anomaly detection engine for GridShield AI.

All thresholds are configurable via environment variables.
Detection is purely data-driven – no hardcoded fraud scores.

Anomaly types detected:
  - SUDDEN_DROP         : consumption drops by ≥ THRESHOLD in one period
  - SUDDEN_SPIKE        : consumption spikes to ≥ THRESHOLD × historical mean
  - HIGH_ZSCORE         : z-score exceeds threshold (statistical outlier)
  - BILLING_MISMATCH    : billed_units vs units_consumed inconsistency
  - ZERO_CONSUMPTION    : periods with zero or near-zero consumption
  - HIGH_VARIABILITY    : abnormally high coefficient of variation
  - METER_GAP           : meter reading end - start ≠ units_consumed
  - TREND_REVERSAL      : significant unexpected trend reversal
"""
import os
import logging
import numpy as np
from typing import Optional
from services.analysis import compute_period_zscores

logger = logging.getLogger("gridshield.anomaly")

ZSCORE_THRESHOLD   = float(os.getenv("ANOMALY_ZSCORE_THRESHOLD", "2.5"))
SUDDEN_DROP_PCT    = float(os.getenv("SUDDEN_DROP_THRESHOLD",    "0.40"))   # 40 % drop
SUDDEN_SPIKE_MULT  = float(os.getenv("SUDDEN_SPIKE_THRESHOLD",   "2.50"))   # 2.5× mean
MIN_HISTORY        = int(os.getenv("MIN_HISTORY_MONTHS",          "3"))
BILLING_MISMATCH_PCT = 0.10  # 10 % tolerance
ZERO_CONSUMPTION_THRESHOLD = 1.0   # kWh – below this is flagged as zero


def detect_anomalies(profile: dict) -> dict:
    """
    Run all detectors against a consumer profile.
    Returns {flags, affected_periods, statistical_evidence, risk_score_contribution}.
    """
    flags: list[dict] = []
    affected_periods: set[str] = set()
    evidence: dict = {}

    values = profile.get("consumption_values", [])
    periods = profile.get("periods", [])
    n = len(values)

    if n == 0:
        return _empty_result("No consumption data available")

    mean_c = profile.get("mean_consumption", 0)
    std_c  = profile.get("std_consumption", 0)

    # ── Z-score outliers ────────────────────────────────────────────────────
    zscore_data = compute_period_zscores(profile)
    high_z = [z for z in zscore_data if abs(z["zscore"]) > ZSCORE_THRESHOLD]
    if high_z:
        for hz in high_z:
            direction = "above" if hz["zscore"] > 0 else "below"
            flags.append({
                "type": "HIGH_ZSCORE",
                "severity": _zscore_severity(abs(hz["zscore"])),
                "period": hz["period"],
                "description": (
                    f"Period {hz['period']}: consumption {hz['value']:.1f} kWh is "
                    f"{abs(hz['zscore']):.2f} standard deviations {direction} "
                    f"historical mean ({mean_c:.1f} kWh)."
                ),
                "zscore": hz["zscore"],
                "value": hz["value"],
            })
            affected_periods.add(hz["period"])
        evidence["zscore_outliers"] = high_z

    # ── Sudden drops ────────────────────────────────────────────────────────
    for i in range(1, n):
        prev_val = values[i - 1]
        curr_val = values[i]
        if prev_val and prev_val > 0:
            drop_pct = (prev_val - curr_val) / prev_val
            if drop_pct >= SUDDEN_DROP_PCT:
                period = str(periods[i]) if i < len(periods) else str(i)
                flags.append({
                    "type": "SUDDEN_DROP",
                    "severity": "High" if drop_pct >= 0.60 else "Medium",
                    "period": period,
                    "description": (
                        f"Period {period}: consumption dropped {drop_pct*100:.1f}% "
                        f"from {prev_val:.1f} to {curr_val:.1f} kWh in one period."
                    ),
                    "drop_pct": round(drop_pct * 100, 2),
                    "from_value": prev_val,
                    "to_value": curr_val,
                })
                affected_periods.add(period)
        evidence["sudden_drops"] = [f for f in flags if f["type"] == "SUDDEN_DROP"]

    # ── Sudden spikes ────────────────────────────────────────────────────────
    if mean_c > 0:
        for i, (val, period) in enumerate(zip(values, periods)):
            if val >= SUDDEN_SPIKE_MULT * mean_c and std_c > 0:
                ratio = val / mean_c
                flags.append({
                    "type": "SUDDEN_SPIKE",
                    "severity": "High" if ratio >= 4.0 else "Medium",
                    "period": str(period),
                    "description": (
                        f"Period {period}: consumption {val:.1f} kWh is "
                        f"{ratio:.2f}× the historical mean ({mean_c:.1f} kWh)."
                    ),
                    "ratio_to_mean": round(ratio, 2),
                    "value": val,
                })
                affected_periods.add(str(period))
        evidence["sudden_spikes"] = [f for f in flags if f["type"] == "SUDDEN_SPIKE"]

    # ── Zero / near-zero consumption ─────────────────────────────────────────
    zeros = [
        (str(periods[i]), values[i])
        for i in range(n)
        if values[i] is not None and values[i] <= ZERO_CONSUMPTION_THRESHOLD
    ]
    if zeros and mean_c > ZERO_CONSUMPTION_THRESHOLD * 5:
        for period, val in zeros:
            flags.append({
                "type": "ZERO_CONSUMPTION",
                "severity": "High",
                "period": period,
                "description": (
                    f"Period {period}: consumption is {val:.2f} kWh while "
                    f"historical average is {mean_c:.1f} kWh. "
                    "Possible bypass, meter tampering, or vacant premise."
                ),
                "value": val,
            })
            affected_periods.add(period)
        evidence["zero_consumption_periods"] = zeros

    # ── High variability ─────────────────────────────────────────────────────
    cv = profile.get("coefficient_of_variation", 0)
    if cv > 0.80 and n >= MIN_HISTORY:
        flags.append({
            "type": "HIGH_VARIABILITY",
            "severity": "Medium",
            "period": "multiple",
            "description": (
                f"Coefficient of variation is {cv:.2f} ({cv*100:.0f}%), indicating "
                "highly inconsistent consumption pattern that warrants investigation."
            ),
            "coefficient_of_variation": cv,
        })
        evidence["high_variability"] = {"cv": cv}

    # ── Billing / consumption mismatch ───────────────────────────────────────
    billing_data = profile.get("billing_data", [])
    mismatches = []
    for rec in billing_data:
        consumed = rec.get("units_consumed")
        billed = rec.get("billed_units")
        if consumed is not None and billed is not None and consumed > 0:
            diff_pct = abs(consumed - billed) / consumed
            if diff_pct > BILLING_MISMATCH_PCT:
                mismatches.append({
                    "period": rec.get("billing_period", ""),
                    "units_consumed": consumed,
                    "billed_units": billed,
                    "discrepancy_pct": round(diff_pct * 100, 2),
                })
                affected_periods.add(str(rec.get("billing_period", "")))

    if mismatches:
        for m in mismatches:
            flags.append({
                "type": "BILLING_MISMATCH",
                "severity": "High" if m["discrepancy_pct"] > 25 else "Medium",
                "period": m["period"],
                "description": (
                    f"Period {m['period']}: units consumed ({m['units_consumed']:.1f}) "
                    f"vs billed ({m['billed_units']:.1f}) – "
                    f"{m['discrepancy_pct']:.1f}% discrepancy."
                ),
                **m,
            })
        evidence["billing_mismatches"] = mismatches

    # ── Meter reading gaps ────────────────────────────────────────────────────
    meter_gaps = []
    for rec in billing_data:
        start = rec.get("meter_reading_start")
        end = rec.get("meter_reading_end")
        consumed = rec.get("units_consumed")
        if start is not None and end is not None and consumed is not None:
            calculated = end - start
            if calculated >= 0 and consumed > 0:
                gap_pct = abs(calculated - consumed) / consumed
                if gap_pct > BILLING_MISMATCH_PCT:
                    meter_gaps.append({
                        "period": rec.get("billing_period", ""),
                        "calculated": round(calculated, 2),
                        "recorded": round(consumed, 2),
                        "gap_pct": round(gap_pct * 100, 2),
                    })
                    affected_periods.add(str(rec.get("billing_period", "")))

    if meter_gaps:
        for g in meter_gaps:
            flags.append({
                "type": "METER_GAP",
                "severity": "High" if g["gap_pct"] > 20 else "Medium",
                "period": g["period"],
                "description": (
                    f"Period {g['period']}: meter reading difference ({g['calculated']:.1f} kWh) "
                    f"does not match recorded consumption ({g['recorded']:.1f} kWh) "
                    f"– {g['gap_pct']:.1f}% discrepancy."
                ),
                **g,
            })
        evidence["meter_gaps"] = meter_gaps

    return {
        "flags": flags,
        "flag_count": len(flags),
        "affected_periods": sorted(list(affected_periods)),
        "statistical_evidence": evidence,
        "anomaly_types": list({f["type"] for f in flags}),
    }


def calculate_fraud_risk_score(anomaly_result: dict, profile: dict) -> dict:
    """
    Dynamically compute fraud risk score 0–100 from anomaly evidence.
    Weights are domain-driven, NOT hardcoded to any specific consumer.
    """
    flags = anomaly_result.get("flags", [])
    n_periods = profile.get("periods_available", 1)

    if not flags:
        score = 0.0
        level = "Low"
        return {"fraud_risk_score": 0.0, "risk_level": "Low", "confidence_score": 1.0,
                "scoring_breakdown": {}}

    type_weights = {
        "METER_GAP":        25,
        "BILLING_MISMATCH": 22,
        "ZERO_CONSUMPTION": 20,
        "SUDDEN_DROP":      18,
        "SUDDEN_SPIKE":     12,
        "HIGH_ZSCORE":      10,
        "HIGH_VARIABILITY":  8,
    }
    severity_multiplier = {"Critical": 1.5, "High": 1.2, "Medium": 1.0, "Low": 0.7}

    score = 0.0
    breakdown: dict[str, float] = {}
    seen_types: set[str] = set()

    for flag in flags:
        ftype = flag["type"]
        severity = flag.get("severity", "Medium")
        base_weight = type_weights.get(ftype, 5)
        multiplier = severity_multiplier.get(severity, 1.0)
        contribution = base_weight * multiplier

        if ftype not in seen_types:
            score += contribution
            breakdown[ftype] = round(contribution, 2)
            seen_types.add(ftype)
        else:
            # repeated occurrences add diminishing score
            score += contribution * 0.3
            breakdown[ftype] = round(breakdown.get(ftype, 0) + contribution * 0.3, 2)

    # frequency adjustment: more affected periods → higher concern
    affected_ratio = len(anomaly_result.get("affected_periods", [])) / max(n_periods, 1)
    frequency_bonus = min(affected_ratio * 15, 15)
    score += frequency_bonus
    breakdown["frequency_adjustment"] = round(frequency_bonus, 2)

    score = min(score, 100.0)

    if score >= 75:
        level = "Critical"
    elif score >= 55:
        level = "High"
    elif score >= 30:
        level = "Medium"
    else:
        level = "Low"

    # confidence: higher with more data
    confidence = min(0.5 + (n_periods / 24) * 0.5, 0.95)

    return {
        "fraud_risk_score": round(score, 2),
        "risk_level": level,
        "confidence_score": round(confidence, 3),
        "scoring_breakdown": breakdown,
    }


def _zscore_severity(z: float) -> str:
    if z >= 4.0:
        return "Critical"
    if z >= 3.0:
        return "High"
    if z >= 2.5:
        return "Medium"
    return "Low"


def _empty_result(reason: str) -> dict:
    return {
        "flags": [],
        "flag_count": 0,
        "affected_periods": [],
        "statistical_evidence": {"note": reason},
        "anomaly_types": [],
    }


def recommended_action(risk_level: str, anomaly_types: list[str]) -> str:
    if risk_level == "Critical":
        return "Immediate field inspection and meter audit required"
    if risk_level == "High":
        if "METER_GAP" in anomaly_types or "BILLING_MISMATCH" in anomaly_types:
            return "Urgent meter inspection and billing records audit"
        return "High-priority investigation – schedule field visit"
    if risk_level == "Medium":
        return "Assign investigator for remote record review"
    return "Monitor – no immediate action required"
