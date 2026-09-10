"""End-to-end validation script."""
import requests, json, sys

BASE = 'http://localhost:8000'
PASS = 0
FAIL = 0

def check(label, cond, info=""):
    global PASS, FAIL
    if cond:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} {info}")
        FAIL += 1

# 1. Upload full dataset
print("1. Uploading full 200-consumer dataset...")
with open('../data/sample/sample_billing_data.csv', 'rb') as f:
    r = requests.post(f'{BASE}/api/data/upload',
                      files={'file': ('sample_billing_data.csv', f, 'text/csv')},
                      timeout=60)
check("Upload ok", r.ok, str(r.status_code))
if r.ok:
    rep = r.json().get('report', {})
    ins = rep.get("inserted_rows", 0)
    final = rep.get("final_rows", 0)
    fields = rep.get("canonical_fields_present", [])
    print(f"     Inserted {ins}/{final} rows, fields: {fields}")
    check("Got canonical fields", len(fields) >= 4)

# 2. Batch analysis
print("\n2. Running batch analysis (200 consumers)...")
r2 = requests.post(f'{BASE}/api/analysis/run-batch?limit=200', timeout=120)
check("Batch analysis ok", r2.ok)
d2 = r2.json()
processed = d2.get("processed", 0)
check(f"Processed >= 100 consumers ({processed})", processed >= 100)

# 3. Dashboard
print("\n3. Dashboard statistics...")
r3 = requests.get(f'{BASE}/api/analysis/dashboard', timeout=10)
check("Dashboard ok", r3.ok)
d3 = r3.json()
check("total_consumers > 0", d3.get("total_consumers", 0) > 0)
check("total_analyzed > 0", d3.get("total_analyzed", 0) > 0)
check("risk_distribution populated", bool(d3.get("risk_distribution")))
print(f"     Stats: consumers={d3['total_consumers']}, analyzed={d3['total_analyzed']}, high_risk={d3['high_risk_count']}")
print(f"     Risk dist: {d3['risk_distribution']}")
check("Has High or Critical consumers", d3.get("high_risk_count", 0) > 0)

# 4. Find a high-risk consumer
print("\n4. High-risk consumer investigation...")
r4 = requests.get(f'{BASE}/api/analysis/anomaly-list?page=1&page_size=5', timeout=10)
check("Anomaly list ok", r4.ok)
d4 = r4.json()
results = d4.get("results", [])
check("Anomaly results exist", len(results) > 0)

if results:
    top = results[0]
    cid = top['consumer_id']
    score = top['fraud_risk_score']
    level = top['risk_level']
    check("Top consumer has valid score", 0 <= score <= 100)
    print(f"     Top consumer: {cid}, score={score}, level={level}")

    # 5. Full profile
    r5 = requests.get(f'{BASE}/api/analysis/consumer/{cid}/profile', timeout=10)
    check("Profile ok", r5.ok)
    prof = r5.json()
    check("Profile has consumption_values", len(prof.get("consumption_values", [])) > 0)
    check("Profile has billing_data", len(prof.get("billing_data", [])) > 0)

    # 6. Anomaly detail
    r6 = requests.get(f'{BASE}/api/analysis/consumer/{cid}/anomalies', timeout=10)
    check("Anomaly detail ok", r6.ok)
    ad = r6.json()
    flags = ad.get("anomaly_result", {}).get("flags", [])
    risk_score = ad.get("risk_assessment", {}).get("fraud_risk_score", -1)
    check("Risk score 0-100", 0 <= risk_score <= 100)

    # 7. AI investigation pipeline
    print("\n5. AI investigation (5-agent pipeline)...")
    r7 = requests.post(f'{BASE}/api/agents/investigate/{cid}', timeout=30)
    check("Investigation ok", r7.ok)
    inv = r7.json()
    trace = inv.get("agent_trace", {})
    agents = trace.get("agents", [])
    check("5 agents ran", len(agents) == 5)
    check("Has DataAnalysisAgent", any(a["agent"] == "DataAnalysisAgent" for a in agents))
    check("Has AnomalyDetectionAgent", any(a["agent"] == "AnomalyDetectionAgent" for a in agents))
    check("Has FraudInvestigationAgent", any(a["agent"] == "FraudInvestigationAgent" for a in agents))
    check("Has ExplainabilityAgent", any(a["agent"] == "ExplainabilityAgent" for a in agents))
    check("Has DecisionSupportAgent", any(a["agent"] == "DecisionSupportAgent" for a in agents))
    check("Has recommended_action", bool(inv.get("recommended_action")))
    check("Has disclaimer", "not a legal" in inv.get("disclaimer", "").lower())
    print(f"     Final action: {inv.get('recommended_action')}")
    print(f"     watsonx: {trace.get('watsonx_available')} | model: {trace.get('model_id')}")

    # 8. Case management
    print("\n6. Case management workflow...")
    r8 = requests.post(f'{BASE}/api/cases/', json={"consumer_id": cid}, timeout=10)
    if r8.status_code in (200, 201):
        case_id = r8.json()["case_id"]
        check("Case created", True)
        check("Case ID format", case_id.startswith("GS-"))

        # update
        ru = requests.patch(f'{BASE}/api/cases/{case_id}',
                            json={"status": "Under Investigation", "assigned_to": "Inv-01"}, timeout=10)
        check("Case updated", ru.ok)

        # add note
        rn = requests.post(f'{BASE}/api/cases/{case_id}/events',
                           json={"event_type": "note_added", "description": "E2E test note"}, timeout=10)
        check("Note added", rn.ok)

        # get case with timeline
        rg = requests.get(f'{BASE}/api/cases/{case_id}', timeout=10)
        check("Case get ok", rg.ok)
        cdata = rg.json()
        check("Timeline has events", len(cdata.get("timeline", [])) >= 2)

        # PDF report
        rp = requests.get(f'{BASE}/api/reports/{case_id}/pdf', timeout=20)
        check("PDF report generated", rp.ok and rp.headers.get("content-type") == "application/pdf")
        check("PDF has content", len(rp.content) > 1000)
        print(f"     PDF size: {len(rp.content)} bytes")

        # JSON report
        rj = requests.get(f'{BASE}/api/reports/{case_id}/json', timeout=10)
        check("JSON report ok", rj.ok)
        rep_j = rj.json()
        check("Report has consumer_profile", bool(rep_j.get("consumer_profile")))
        check("Report has timeline", bool(rep_j.get("timeline")))
        check("Report has disclaimer", "not a legal" in rep_j.get("disclaimer", "").lower())
    elif r8.status_code == 409:
        check("Case exists (409 - ok for repeated runs)", True)
    else:
        check("Case created", False, str(r8.status_code))

print(f"\n{'='*48}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("FULL END-TO-END VALIDATION PASSED")
else:
    print(f"FAILED: {FAIL} tests")
    sys.exit(1)
