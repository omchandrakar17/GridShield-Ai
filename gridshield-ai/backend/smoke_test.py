"""
API smoke test – runs against a live backend server at localhost:8000.
Usage: python smoke_test.py
"""
import sys, json, time, requests

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label}  {detail}")
        FAIL += 1

def get(path, **kw):
    return requests.get(BASE + path, timeout=15, **kw)

def post(path, **kw):
    return requests.post(BASE + path, timeout=30, **kw)

print("\n=== GridShield AI API Smoke Tests ===\n")

# 1. Health
r = get("/api/health")
check("GET /api/health -> 200", r.status_code == 200)
check("Health response contains 'GridShield AI'", "GridShield AI" in r.json().get("service",""))

# 2. Data stats
r = get("/api/data/stats")
check("GET /api/data/stats -> 200", r.status_code == 200)
stats = r.json()
check("Stats has total_consumers", "total_consumers" in stats)

# 3. Consumer list
r = get("/api/data/consumers?page=1&page_size=5")
check("GET /api/data/consumers -> 200", r.status_code == 200)
consumers = r.json().get("consumers", [])
check("Consumers list populated", len(consumers) > 0, f"got {len(consumers)}")

if consumers:
    cid = consumers[0]

    # 4. Consumer records
    r = get(f"/api/data/consumers/{cid}/records")
    check(f"GET /api/data/consumers/{cid}/records -> 200", r.status_code == 200)
    recs = r.json().get("records", [])
    check("Records have units_consumed field", any("units_consumed" in rec for rec in recs))

    # 5. Consumer profile
    r = get(f"/api/analysis/consumer/{cid}/profile")
    check(f"GET /api/analysis/consumer/{cid}/profile -> 200", r.status_code == 200)
    profile = r.json()
    check("Profile has consumption_values", "consumption_values" in profile)
    check("Profile has mean_consumption", profile.get("mean_consumption") is not None)
    check("Profile has coefficient_of_variation", "coefficient_of_variation" in profile)

    # 6. Anomaly detection
    r = get(f"/api/analysis/consumer/{cid}/anomalies")
    check(f"GET /api/analysis/consumer/{cid}/anomalies -> 200", r.status_code == 200)
    anom = r.json()
    check("Anomaly result has risk_assessment", "risk_assessment" in anom)
    check("Risk score is numeric 0-100",
          0 <= anom.get("risk_assessment", {}).get("fraud_risk_score", -1) <= 100)
    check("Risk level is valid",
          anom.get("risk_assessment", {}).get("risk_level") in ["Low","Medium","High","Critical"])

    # 7. Agent status
    r = get("/api/agents/status")
    check("GET /api/agents/status -> 200", r.status_code == 200)
    a_status = r.json()
    check("Agent status has watsonx_configured field", "watsonx_configured" in a_status)

    # 8. AI investigation pipeline
    r = post(f"/api/agents/investigate/{cid}")
    check(f"POST /api/agents/investigate/{cid} -> 200", r.status_code == 200)
    inv = r.json()
    check("Investigation has agent_trace", "agent_trace" in inv)
    check("Agent trace has 5 agents", len(inv.get("agent_trace", {}).get("agents", [])) == 5)
    check("Investigation has risk_assessment", "risk_assessment" in inv)
    check("Investigation has disclaimer", "disclaimer" in inv)

    # 9. Dashboard stats
    r = get("/api/analysis/dashboard")
    check("GET /api/analysis/dashboard -> 200", r.status_code == 200)
    dash = r.json()
    check("Dashboard has total_consumers", "total_consumers" in dash)
    check("Dashboard has risk_distribution", "risk_distribution" in dash)

    # 10. Anomaly list
    r = get("/api/analysis/anomaly-list?page=1&page_size=10")
    check("GET /api/analysis/anomaly-list -> 200", r.status_code == 200)
    al = r.json()
    check("Anomaly list has results", "results" in al)

    # 11. Case creation
    r = post("/api/cases/", json={"consumer_id": cid})
    if r.status_code == 201 or r.status_code == 200:
        case_data = r.json()
        case_id = case_data.get("case_id")
        check("POST /api/cases/ -> 200/201", True)
        check("Case has case_id", bool(case_id))

        # 12. Get case
        r2 = get(f"/api/cases/{case_id}")
        check(f"GET /api/cases/{case_id} -> 200", r2.status_code == 200)
        check("Case has timeline", "timeline" in r2.json())

        # 13. Update case
        r3 = requests.patch(f"{BASE}/api/cases/{case_id}",
                            json={"status": "Under Investigation", "assigned_to": "Investigator-01"},
                            timeout=10)
        check(f"PATCH /api/cases/{case_id} -> 200", r3.status_code == 200)

        # 14. Add event
        r4 = post(f"/api/cases/{case_id}/events",
                  json={"event_type": "note_added", "description": "Smoke test note", "performed_by": "test"})
        check(f"POST /api/cases/{case_id}/events -> 200", r4.status_code == 200)

        # 15. Report JSON
        r5 = get(f"/api/reports/{case_id}/json")
        check(f"GET /api/reports/{case_id}/json -> 200", r5.status_code == 200)
        rep = r5.json()
        check("Report has consumer_profile", "consumer_profile" in rep)
        check("Report has disclaimer", "disclaimer" in rep)
    elif r.status_code == 409:
        check("POST /api/cases/ -> 409 (duplicate – case already exists)", True)
    else:
        check("POST /api/cases/ -> 200/201", False, f"got {r.status_code}: {r.text[:100]}")

print(f"\n{'='*40}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL SMOKE TESTS PASSED")
else:
    print(f"FAILED: {FAIL} tests")
    sys.exit(1)
