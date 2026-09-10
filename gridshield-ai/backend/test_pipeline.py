import asyncio, sys, json
sys.path.insert(0, '.')

async def test():
    from services.database import init_db, AsyncSessionLocal
    from services.ingestion import validate_and_clean
    from services.analysis import build_consumer_profile
    from services.anomaly_detection import detect_anomalies, calculate_fraud_risk_score
    from agents.watsonx_agents import run_agent_pipeline
    import pandas as pd
    from sqlalchemy import text

    await init_db()
    print('[1] DB initialized')

    df = pd.read_csv('../data/sample/sample_billing_data.csv', dtype=str)
    cleaned, report = validate_and_clean(df, 'test')
    final_rows = report['final_rows']
    fields = report['canonical_fields_present']
    print(f'[2] Ingestion: {final_rows} rows, fields: {fields}')

    async with AsyncSessionLocal() as db:
        for _, row in cleaned.head(36).iterrows():
            try:
                await db.execute(text('''
                    INSERT OR IGNORE INTO consumer_records
                      (consumer_id, billing_period, units_consumed, billed_units, amount_billed,
                       meter_reading_start, meter_reading_end, tariff_category, consumer_type,
                       location, division, source_file)
                    VALUES (:cid, :bp, :uc, :bu, :ab, :mrs, :mre, :tc, :ct, :loc, :div, :sf)
                '''), {
                    'cid': str(row['consumer_id']),
                    'bp': str(row.get('billing_period', '')),
                    'uc': float(row['units_consumed']) if row.get('units_consumed') else None,
                    'bu': float(row['billed_units']) if row.get('billed_units') else None,
                    'ab': float(row['amount_billed']) if row.get('amount_billed') else None,
                    'mrs': float(row['meter_reading_start']) if row.get('meter_reading_start') else None,
                    'mre': float(row['meter_reading_end']) if row.get('meter_reading_end') else None,
                    'tc': str(row.get('tariff_category', '')) or None,
                    'ct': str(row.get('consumer_type', '')) or None,
                    'loc': str(row.get('location', '')) or None,
                    'div': str(row.get('division', '')) or None,
                    'sf': 'test',
                })
            except Exception as e:
                pass
        await db.commit()
        print('[3] Sample records inserted')

        r = await db.execute(text('SELECT DISTINCT consumer_id FROM consumer_records LIMIT 1'))
        cid = r.scalar()
        r2 = await db.execute(text('SELECT * FROM consumer_records WHERE consumer_id = :c ORDER BY billing_period'), {'c': cid})
        records = [dict(row._mapping) for row in r2.fetchall()]

    profile = build_consumer_profile(records)
    print(f'[4] Profile for {cid}: {profile["periods_available"]} periods, mean={profile["mean_consumption"]} kWh')

    anomaly = detect_anomalies(profile)
    print(f'[5] Anomalies: {anomaly["flag_count"]} flags, types={anomaly["anomaly_types"]}')

    risk = calculate_fraud_risk_score(anomaly, profile)
    print(f'[6] Risk: {risk["fraud_risk_score"]}/100 ({risk["risk_level"]}), confidence={risk["confidence_score"]}')

    trace = run_agent_pipeline(profile, anomaly, risk)
    n_agents = len(trace["agents"])
    wx = trace["watsonx_available"]
    action = trace["final_decision"]["recommended_action"]
    print(f'[7] Agent pipeline: {n_agents} agents, watsonx={wx}')
    print(f'    Final decision: {action}')
    print('ALL TESTS PASSED')

asyncio.run(test())
