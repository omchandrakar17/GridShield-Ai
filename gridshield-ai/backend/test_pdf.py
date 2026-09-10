"""Direct PDF generation test – no server required."""
import sys
sys.path.insert(0, '.')

from services.report_service import generate_pdf_report

# Build a realistic test payload
profile = {
    'consumer_id': 'CON10074',
    'consumer_type': 'Commercial',
    'tariff_category': 'Industrial',
    'location': 'North Zone',
    'division': 'Div-B',
    'periods_available': 18,
    'mean_consumption': 850.4,
    'std_consumption': 412.1,
    'min_consumption': 12.3,
    'max_consumption': 3200.5,
    'coefficient_of_variation': 0.48,
    'trend_slope': -5.2,
    'billing_data': [
        {'billing_period': '2023-01', 'units_consumed': 900, 'billed_units': 900, 'amount_billed': 7200, 'meter_reading_start': 10000, 'meter_reading_end': 10900},
        {'billing_period': '2023-02', 'units_consumed': 100, 'billed_units': 100, 'amount_billed': 800, 'meter_reading_start': 10900, 'meter_reading_end': 11000},
    ]
}
case = {
    'case_id': 'GS-20240101-ABCDEF',
    'consumer_id': 'CON10074',
    'status': 'Under Investigation',
    'priority': 'Critical',
    'fraud_risk_score': 100.0,
    'risk_level': 'Critical',
    'assigned_to': 'Inspector-01',
    'notes': 'Significant consumption drop detected',
    'created_at': '2024-01-01T10:00:00',
    'updated_at': '2024-01-02T14:30:00',
    'resolved_at': None,
    'resolution_notes': None,
}
anomaly = {
    'fraud_risk_score': 100.0,
    'risk_level': 'Critical',
    'confidence_score': 0.92,
    'anomaly_flags': [
        {'type': 'SUDDEN_DROP', 'severity': 'High', 'period': '2023-02', 'description': 'Consumption dropped 88.9% from 900.0 to 100.0 kWh'},
        {'type': 'ZERO_CONSUMPTION', 'severity': 'High', 'period': '2023-03', 'description': 'Near-zero consumption while historical average is 850 kWh'},
    ],
    'ai_reasoning': 'DataAnalysisAgent: Consumer has 18 periods of data with very high variability.\n\nAnomalyDetectionAgent: SUDDEN_DROP detected - likely meter bypass or tampering.\n\nFraudInvestigationAgent: Strong indicators of meter fraud.',
    'recommended_action': 'Immediate field inspection and meter audit required',
}
events = [
    {'id': 1, 'case_id': 'GS-20240101-ABCDEF', 'event_type': 'case_created',
     'description': 'Case created for consumer CON10074', 'performed_by': 'system', 'created_at': '2024-01-01T10:00:00'},
    {'id': 2, 'case_id': 'GS-20240101-ABCDEF', 'event_type': 'ai_analysis',
     'description': 'AI investigation completed. Risk: Critical (100/100)', 'performed_by': 'GridShield AI Agent Pipeline', 'created_at': '2024-01-01T10:05:00'},
    {'id': 3, 'case_id': 'GS-20240101-ABCDEF', 'event_type': 'status_change',
     'description': "Status changed to 'Under Investigation'", 'performed_by': 'investigator', 'created_at': '2024-01-02T14:30:00'},
]
agent_trace = {
    'watsonx_available': False,
    'model_id': 'not_configured',
    'agents': [
        {'agent': 'DataAnalysisAgent', 'output': 'Consumer has 18 periods...'},
        {'agent': 'AnomalyDetectionAgent', 'output': 'SUDDEN_DROP detected...'},
    ],
    'final_decision': {
        'recommended_action': 'Immediate field inspection and meter audit required',
        'risk_level': 'Critical',
        'fraud_risk_score': 100.0,
    }
}

pdf_bytes = generate_pdf_report(case, anomaly, profile, events, agent_trace)

assert len(pdf_bytes) > 2000, f"PDF too small: {len(pdf_bytes)} bytes"
assert pdf_bytes[:4] == b'%PDF', f"Not a valid PDF (got {pdf_bytes[:4]})"

print(f"[PASS] PDF generated: {len(pdf_bytes)} bytes, valid PDF header")

# Save for inspection
with open('test_report_output.pdf', 'wb') as f:
    f.write(pdf_bytes)
print("[PASS] Saved to test_report_output.pdf")
print("PDF UNIT TEST PASSED")
