@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM GridShield AI – Generate + load sample dataset for testing
REM ─────────────────────────────────────────────────────────────────────────────
cd /d "%~dp0"

echo [1/2] Generating sample dataset (200 consumers x 18 months)...
python data/generate_sample.py 200

echo.
echo [2/2] Uploading to running backend at localhost:8000...
python -c "
import requests, os
f = open('data/sample/sample_billing_data.csv', 'rb')
r = requests.post('http://localhost:8000/api/data/upload', files={'file': f}, timeout=60)
if r.ok:
    rep = r.json().get('report', {})
    print(f'  Inserted: {rep.get(\"inserted_rows\")} rows')
    print(f'  Fields:   {rep.get(\"canonical_fields_present\")}')
    print('  Upload successful.')
    print()
    print('Now run batch analysis:')
    r2 = requests.post('http://localhost:8000/api/analysis/run-batch?limit=200', timeout=120)
    d2 = r2.json()
    print(f'  Analyzed: {d2.get(\"processed\")} consumers')
else:
    print(f'  Upload failed: {r.status_code} {r.text[:200]}')
    print('  Make sure the backend is running (start_backend.bat)')
"
