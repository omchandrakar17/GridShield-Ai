"""
GridShield AI – Sample dataset generator for testing.

This script generates a CSV dataset that MATCHES THE STRUCTURE of real open electricity 
billing datasets (e.g., Indian state electricity board formats, Kaggle electricity 
consumption datasets).

The values are algorithmically generated to simulate realistic consumption patterns 
INCLUDING known fraud patterns – they are NOT fabricated "fake AI results."

This data is clearly labeled as SAMPLE/TESTING data and must NOT be used in production.

HOW TO REPLACE WITH REAL DATA:
  1. Download a real dataset from:
     - Kaggle: "Electricity Theft Detection" (sgcc-electricity dataset)
       https://www.kaggle.com/datasets/dvnguyen/electricity-theft-detection
     - UCI: "Individual household electric power consumption"
       https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption
     - Open Government / Utility APIs (e.g., data.gov, open utility portals)
  2. Upload via the /api/data/upload endpoint

REAL DATASET SCHEMA REQUIREMENTS (minimum):
  - Consumer ID (string): unique identifier per account/meter
  - Billing Period (date/string): YYYY-MM or similar
  - Units Consumed (numeric): kWh consumed in the period
  
OPTIONAL BUT SUPPORTED:
  - Meter Reading Start/End (numeric)
  - Billed Units (numeric) – for mismatch detection
  - Amount Billed (numeric)
  - Tariff Category / Consumer Type
  - Location / Division
  - Sanctioned Load (kW)
"""
import csv
import math
import os
import random
import sys
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sample_billing_data.csv")

# NOTE: This file is for system testing ONLY.
# Replace with real electricity billing data for production use.
DATA_SOURCE_NOTE = "SAMPLE_TESTING_DATA_NOT_REAL"

random.seed(42)  # reproducible

TARIFFS = ["Residential", "Commercial", "Industrial", "Agricultural"]
LOCATIONS = ["North Zone", "South Zone", "East Zone", "West Zone", "Central Zone"]
DIVISIONS = ["Div-A", "Div-B", "Div-C", "Div-D"]
CONSUMER_TYPES = ["Residential", "Commercial", "Industrial"]


def generate_consumption_series(base_kwh: float, n_months: int, fraud_type: str | None = None):
    """
    Generate a realistic monthly consumption series with optional fraud patterns.
    
    fraud_type options:
      None           – normal consumer
      'sudden_drop'  – consumption drops significantly at some point
      'meter_bypass' – consumption much lower than expected for several months
      'tamper'       – billing/consumption mismatch
      'spike'        – unusual spikes
      'zero_periods' – several zero/near-zero periods
    """
    series = []
    reading = random.uniform(1000, 50000)  # starting meter reading
    records = []
    
    for i in range(n_months):
        # seasonal variation (roughly sinusoidal, higher in summer/winter)
        month_of_year = ((i % 12) + 1)
        seasonal_factor = 1.0 + 0.3 * math.cos((month_of_year - 7) * math.pi / 6)
        noise = random.gauss(0, base_kwh * 0.1)
        consumed = max(10, base_kwh * seasonal_factor + noise)
        
        # apply fraud pattern
        billed_units = consumed
        if fraud_type == "sudden_drop" and i >= n_months // 2:
            consumed = consumed * random.uniform(0.15, 0.35)
            billed_units = consumed
        elif fraud_type == "meter_bypass" and n_months // 3 <= i < 2 * n_months // 3:
            consumed = consumed * random.uniform(0.1, 0.3)
            # billed_units remains higher (billing mismatch)
            billed_units = consumed * random.uniform(2.5, 4.0)
        elif fraud_type == "tamper":
            consumed = consumed * random.uniform(0.6, 0.9)
            billed_units = consumed * random.uniform(1.3, 1.8)
        elif fraud_type == "spike" and random.random() < 0.2:
            consumed = consumed * random.uniform(3.0, 6.0)
            billed_units = consumed
        elif fraud_type == "zero_periods" and i % 4 == 0:
            consumed = random.uniform(0, 2)
            billed_units = consumed
        
        meter_end = reading + consumed
        
        records.append({
            "meter_reading_start": round(reading, 2),
            "meter_reading_end": round(meter_end, 2),
            "units_consumed": round(consumed, 2),
            "billed_units": round(billed_units, 2),
            "meter_reading_calculated": round(meter_end - reading, 2),
        })
        reading = meter_end
    
    return records


def generate_sample_dataset(n_consumers: int = 200, n_months: int = 18):
    """Generate sample billing dataset for testing GridShield AI."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    fraud_distribution = {
        None: int(n_consumers * 0.60),           # 60% normal
        "sudden_drop": int(n_consumers * 0.12),  # 12% sudden drop
        "meter_bypass": int(n_consumers * 0.10), # 10% bypass
        "tamper": int(n_consumers * 0.08),        # 8% tampering
        "spike": int(n_consumers * 0.06),         # 6% spikes
        "zero_periods": int(n_consumers * 0.04), # 4% zero periods
    }
    
    consumer_fraud_map = {}
    for fraud_type, count in fraud_distribution.items():
        for _ in range(count):
            cid = f"CON{random.randint(10000, 99999)}"
            while cid in consumer_fraud_map:
                cid = f"CON{random.randint(10000, 99999)}"
            consumer_fraud_map[cid] = fraud_type
    
    # fill any remaining
    while len(consumer_fraud_map) < n_consumers:
        cid = f"CON{random.randint(10000, 99999)}"
        if cid not in consumer_fraud_map:
            consumer_fraud_map[cid] = None
    
    start_date = datetime(2023, 1, 1)
    rows = []
    
    for cid, fraud_type in consumer_fraud_map.items():
        base_kwh = random.choice([
            random.uniform(80, 300),      # small residential
            random.uniform(300, 1000),    # medium residential/commercial
            random.uniform(1000, 5000),   # commercial
        ])
        tariff = random.choice(TARIFFS)
        location = random.choice(LOCATIONS)
        division = random.choice(DIVISIONS)
        consumer_type = random.choice(CONSUMER_TYPES)
        load_kw = round(base_kwh / 200 + random.uniform(0.5, 2), 2)
        
        series = generate_consumption_series(base_kwh, n_months, fraud_type)
        
        for month_idx, rec in enumerate(series):
            period_date = start_date + relativedelta(months=month_idx)
            billing_period = period_date.strftime("%Y-%m")
            
            amount = round(rec["units_consumed"] * random.uniform(5.0, 8.5), 2)
            
            rows.append({
                "consumer_id": cid,
                "billing_period": billing_period,
                "meter_reading_start": rec["meter_reading_start"],
                "meter_reading_end": rec["meter_reading_end"],
                "units_consumed": rec["units_consumed"],
                "billed_units": rec["billed_units"],
                "amount_billed": amount,
                "tariff_category": tariff,
                "sanctioned_load_kw": load_kw,
                "consumer_type": consumer_type,
                "location": location,
                "division": division,
                "data_source": DATA_SOURCE_NOTE,
            })
    
    # write CSV
    fieldnames = list(rows[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"[OK] Sample dataset written to: {OUTPUT_FILE}")
    print(f"  Consumers: {len(consumer_fraud_map)}")
    print(f"  Rows: {len(rows)}")
    print(f"  Months per consumer: {n_months}")
    print(f"\n[WARNING] THIS IS SAMPLE/TESTING DATA - NOT REAL ELECTRICITY BILLING DATA")
    print(f"   Replace with a real dataset for production use.")
    print(f"\n   Real dataset sources:")
    print(f"   - Kaggle SGCC Electricity Theft: https://www.kaggle.com/datasets/dvnguyen/electricity-theft-detection")
    print(f"   - UCI Household Power Consumption: https://archive.ics.uci.edu/dataset/235")
    print(f"   - Open utility portals: data.gov, your country's open data portal")


if __name__ == "__main__":
    n_consumers = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    generate_sample_dataset(n_consumers=n_consumers)
