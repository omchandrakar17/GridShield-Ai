"""
Report generation service – produces a structured PDF investigation report
from actual case data stored in the database.
"""
import io
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("gridshield.reports")


def generate_pdf_report(
    case: dict,
    anomaly: dict,
    profile: dict,
    events: list[dict],
    agent_trace: Optional[dict],
) -> bytes:
    """
    Generate a PDF investigation report.
    All content comes from passed-in DB data – nothing is fabricated.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether,
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    except ImportError:
        raise RuntimeError("reportlab is required for PDF generation. pip install reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=6)
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceAfter=4)
    style_body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, spaceAfter=4)
    style_small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    style_red = ParagraphStyle("Red", parent=styles["Normal"], fontSize=9, textColor=colors.red)

    elements = []

    # ── Header ─────────────────────────────────────────────────────────────
    elements.append(Paragraph("GridShield AI – Investigation Report", style_h1))
    elements.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Case: {case.get('case_id', 'N/A')}",
        style_small,
    ))
    elements.append(HRFlowable(width="100%", thickness=1))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(
        "DISCLAIMER: This report contains AI-assisted fraud risk assessment "
        "and is intended for investigative purposes only. It does not constitute "
        "a legal determination of fraud.",
        style_small,
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # ── Case Summary ────────────────────────────────────────────────────────
    elements.append(Paragraph("1. Case Summary", style_h2))
    case_data = [
        ["Case ID", case.get("case_id", "")],
        ["Consumer ID", case.get("consumer_id", "")],
        ["Status", case.get("status", "")],
        ["Priority", case.get("priority", "")],
        ["Fraud Risk Score", f"{case.get('fraud_risk_score', 'N/A')}/100"],
        ["Risk Level", case.get("risk_level", "")],
        ["Assigned To", case.get("assigned_to", "Unassigned")],
        ["Created", _fmt_dt(case.get("created_at"))],
        ["Last Updated", _fmt_dt(case.get("updated_at"))],
    ]
    elements.append(_make_table(case_data))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Consumer Profile ────────────────────────────────────────────────────
    elements.append(Paragraph("2. Consumer Profile", style_h2))
    profile_data = [
        ["Consumer Type", profile.get("consumer_type", "N/A")],
        ["Tariff Category", profile.get("tariff_category", "N/A")],
        ["Location", profile.get("location", "N/A")],
        ["Division", profile.get("division", "N/A")],
        ["Periods Analyzed", str(profile.get("periods_available", "N/A"))],
        ["Mean Consumption", f"{profile.get('mean_consumption', 'N/A')} kWh"],
        ["Std Deviation", f"{profile.get('std_consumption', 'N/A')} kWh"],
        ["Min Consumption", f"{profile.get('min_consumption', 'N/A')} kWh"],
        ["Max Consumption", f"{profile.get('max_consumption', 'N/A')} kWh"],
        ["Coeff. of Variation", str(profile.get("coefficient_of_variation", "N/A"))],
    ]
    elements.append(_make_table(profile_data))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Detected Anomalies ──────────────────────────────────────────────────
    elements.append(Paragraph("3. Detected Anomalies", style_h2))
    flags = anomaly.get("anomaly_flags", []) if anomaly else []
    if flags:
        for flag in flags:
            elements.append(Paragraph(
                f"• [{flag.get('type')}] ({flag.get('severity')}) – Period {flag.get('period','?')}: "
                f"{flag.get('description', '')}",
                style_body,
            ))
    else:
        elements.append(Paragraph("No anomalies detected.", style_body))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Risk Assessment ─────────────────────────────────────────────────────
    elements.append(Paragraph("4. Risk Assessment", style_h2))
    elements.append(Paragraph(
        f"Fraud Risk Score: {anomaly.get('fraud_risk_score', 'N/A')}/100 "
        f"(Level: {anomaly.get('risk_level', 'N/A')}) | "
        f"Confidence: {anomaly.get('confidence_score', 'N/A')}",
        style_body,
    ))
    elements.append(Paragraph(
        "Note: AI-assisted investigation priority indicator – not a legal fraud determination.",
        style_small,
    ))
    elements.append(Spacer(1, 0.3 * cm))

    # ── AI Reasoning ────────────────────────────────────────────────────────
    elements.append(Paragraph("5. AI Reasoning", style_h2))
    ai_reasoning = anomaly.get("ai_reasoning", "") if anomaly else ""
    if ai_reasoning:
        elements.append(Paragraph(ai_reasoning, style_body))
    elif agent_trace:
        for ag in agent_trace.get("agents", []):
            elements.append(Paragraph(f"[{ag.get('agent')}] {ag.get('output', '')}", style_body))
    else:
        elements.append(Paragraph(
            "AI reasoning not available. Configure IBM_WATSONX_API_KEY for AI narratives.",
            style_small,
        ))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Recommended Action ──────────────────────────────────────────────────
    elements.append(Paragraph("6. Recommended Action", style_h2))
    action = (agent_trace or {}).get("final_decision", {}).get("recommended_action", "")
    if not action and anomaly:
        action = anomaly.get("recommended_action", "No action specified.")
    elements.append(Paragraph(action or "No action specified.", style_body))
    elements.append(Spacer(1, 0.3 * cm))

    # ── Investigation Timeline ───────────────────────────────────────────────
    elements.append(Paragraph("7. Investigation Timeline", style_h2))
    if events:
        timeline_rows = [["Date/Time", "Event", "Performed By", "Description"]]
        for ev in sorted(events, key=lambda e: str(e.get("created_at") or ""), reverse=True):
            timeline_rows.append([
                _fmt_dt(ev.get("created_at")),
                ev.get("event_type", ""),
                ev.get("performed_by", "system"),
                (ev.get("description") or "")[:80],
            ])
        t = Table(timeline_rows, colWidths=[3 * cm, 3.5 * cm, 3 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fa")]),
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("No timeline events recorded.", style_body))

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5))
    elements.append(Paragraph(
        "GridShield AI – Electricity Fraud Detection & Investigation Platform | "
        "IBM watsonx.ai powered | Report generated automatically from system data.",
        style_small,
    ))

    doc.build(elements)
    return buffer.getvalue()


def _make_table(data: list[list]) -> "Table":
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    t = Table(data, colWidths=[5 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7f8fa")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _fmt_dt(val) -> str:
    if not val:
        return "N/A"
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M UTC")
    return str(val)[:19]
