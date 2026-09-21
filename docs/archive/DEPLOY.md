# HLS SAS DBX Migration — Manual Deployment Guide

**Auth Issue:** The current PAT token lacks required scopes (sql, workspace, databricks-connect). Use this guide to deploy manually via Databricks UI.

---

## Deployment Steps

### ✅ Step 1: Generate Synthetic Data (SQL Editor)

**Option A: Via Databricks SQL Editor**

1. Open **Databricks SQL Editor** in the workspace
2. Select warehouse: **SQL Warehouse (ID: 2f51df324d05e45d)**
3. Copy and paste the SQL below
4. Run each section sequentially

**SQL Script:**

```sql
-- ============================================================================
-- 1. CREATE SCHEMA
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS na-dbxtraining.demo_bravo_insurance_claims;

-- ============================================================================
-- 2. RAW POLICYHOLDERS (~100K rows)
-- ============================================================================
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders
USING DELTA
AS
WITH policy_base AS (
  SELECT
    CONCAT('POL-', LPAD(CAST(seq AS STRING), 6, '0')) AS policy_id,
    CONCAT('Policyholder ', CAST(seq AS STRING)) AS policyholder_name,
    CONCAT('policy', CAST(seq AS STRING), '@hls-sas-dbx.com') AS email,
    seq
  FROM (SELECT EXPLODE(SEQUENCE(0, 99999)) AS seq)
),
states AS (
  SELECT 'IL' AS state, 0.12 AS weight, 41.88 AS lat, -87.63 AS lng, 'Chicago' AS city
  UNION ALL SELECT 'TX', 0.10, 29.76, -95.37, 'Houston'
  UNION ALL SELECT 'CA', 0.10, 34.05, -118.25, 'Los Angeles'  
  UNION ALL SELECT 'FL', 0.09, 25.76, -80.19, 'Miami'
  UNION ALL SELECT 'NY', 0.08, 40.71, -74.01, 'New York'
  UNION ALL SELECT 'OH', 0.07, 41.50, -81.69, 'Cleveland'
  UNION ALL SELECT 'MI', 0.06, 42.33, -83.05, 'Detroit'
  UNION ALL SELECT 'IN', 0.06, 39.77, -86.16, 'Indianapolis'
  UNION ALL SELECT 'PA', 0.05, 39.95, -75.17, 'Philadelphia'
  UNION ALL SELECT 'WI', 0.04, 43.04, -87.91, 'Milwaukee'
)
SELECT
  p.policy_id,
  p.policyholder_name,
  p.email,
  s.state,
  s.city,
  ROUND(s.lat + (RAND(p.seq * 7) - 0.5) * 0.1, 5) AS policyholder_lat,
  ROUND(s.lng + (RAND(p.seq * 11) - 0.5) * 0.1, 5) AS policyholder_lng,
  CASE 
    WHEN RAND(p.seq * 13) < 0.70 THEN 'homeowners'
    WHEN RAND(p.seq * 13) < 0.90 THEN 'renters'
    ELSE 'condo'
  END AS policy_type,
  ROUND(50000 + RAND(p.seq * 17) * 450000, 0) AS coverage_limit_usd,
  DATE_FORMAT(DATE_SUB(CURRENT_DATE(), CAST(60 + RAND(p.seq * 19) * 1035 AS INT)), 'yyyy-MM-dd') AS effective_date
FROM policy_base p
CROSS JOIN (
  SELECT state, weight, lat, lng, city,
         SUM(weight) OVER (ORDER BY state) - weight AS cum_low,
         SUM(weight) OVER (ORDER BY state) AS cum_high
  FROM states
) s
WHERE RAND(p.seq * 23) >= s.cum_low AND RAND(p.seq * 23) < s.cum_high;

-- Verify
SELECT COUNT(*) AS row_count FROM na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders;

-- ============================================================================
-- 3. RAW APPLIANCES (~10 rows)
-- ============================================================================
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_appliances (
  appliance_id STRING,
  model_name STRING,
  manufacturer STRING,
  category STRING,
  retail_price_usd DOUBLE,
  launch_year INT
)
USING DELTA;

INSERT INTO na-dbxtraining.demo_bravo_insurance_claims.raw_appliances VALUES
('APP-000001', 'AquaClean DW-9500 Series', 'AquaClean', 'dishwasher', 850.0, 2025),
('APP-000002', 'AquaClean DW-8200', 'AquaClean', 'dishwasher', 720.0, 2024),
('APP-000003', 'AquaClean DW-7500', 'AquaClean', 'dishwasher', 650.0, 2023),
('APP-000004', 'WashMaster Pro 5000', 'WashMaster', 'washer', 1100.0, 2025),
('APP-000005', 'WashMaster Elite 4200', 'WashMaster', 'washer', 950.0, 2024),
('APP-000006', 'DryFast Turbo 9000', 'DryFast', 'dryer', 900.0, 2025),
('APP-000007', 'DryFast Eco 7500', 'DryFast', 'dryer', 750.0, 2024),
('APP-000008', 'ChillMax Ultra 800L', 'ChillMax', 'refrigerator', 2200.0, 2025),
('APP-000009', 'ChillMax Compact 500L', 'ChillMax', 'refrigerator', 1400.0, 2024),
('APP-000010', 'HotFlow Elite 50gal', 'HotFlow', 'water_heater', 1200.0, 2024);

-- Verify
SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_appliances;

-- ============================================================================
-- 4. RAW APPLIANCE BATCHES (~500 rows)
-- ============================================================================
CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches
USING DELTA
AS
WITH batch_gen AS (
  SELECT
    appliance_id,
    batch_num,
    DATE_FORMAT(DATE_SUB(CURRENT_DATE(), CAST((batch_num / 4) * 30 + (batch_num % 4) * 7 AS INT)), 'yyyy-MM-dd') AS manufacture_date
  FROM (
    SELECT 'APP-000001' AS appliance_id UNION ALL
    SELECT 'APP-000002' UNION ALL SELECT 'APP-000003' UNION ALL
    SELECT 'APP-000004' UNION ALL SELECT 'APP-000005' UNION ALL
    SELECT 'APP-000006' UNION ALL SELECT 'APP-000007' UNION ALL
    SELECT 'APP-000008' UNION ALL SELECT 'APP-000009' UNION ALL
    SELECT 'APP-000010'
  ) appliances
  CROSS JOIN (SELECT EXPLODE(SEQUENCE(0, 49)) AS batch_num)
)
SELECT
  CONCAT('BATCH-', DATE_FORMAT(manufacture_date, 'yyyy-MM'), '-', RIGHT(appliance_id, 3)) AS appliance_batch_id,
  appliance_id,
  manufacture_date,
  CASE WHEN RAND(batch_num * 31) < 0.25 THEN 'Rockford-IL'
       WHEN RAND(batch_num * 31) < 0.50 THEN 'Louisville-KY'
       WHEN RAND(batch_num * 31) < 0.75 THEN 'Phoenix-AZ'
       ELSE 'Nashville-TN'
  END AS plant_location,
  CAST(500 + RAND(batch_num * 37) * 1500 AS INT) AS units_produced,
  'active' AS status,
  NULL AS recall_notice
FROM batch_gen;

-- Add affected batch with recall notice
INSERT INTO na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches VALUES (
  'AC-2026-Q1',
  'APP-000001',
  DATE_FORMAT(DATE_SUB(CURRENT_DATE(), 270), 'yyyy-MM-dd'),
  'Rockford-IL',
  12000,
  'recalled',
  'Product Safety Recall Notice PSR-2026-02-28. Product: AquaClean DW-9500 Series Dishwasher, Batch AC-2026-Q1 (manufactured Jan-Mar 2026, Rockford IL facility). Issue: defective inlet valve seal causing slow water leaks during wash cycles. Root cause: supplier batch of EPDM seals outside hardness spec (Shore A 68 vs required 75-80). Affected units: ~12,000 distributed across IL, IN, OH, MI, WI. Risk: property water damage from undetected leaks. Action: voluntary recall issued 2026-02-28; free replacement + installation offered to all registered owners.'
);

-- Verify
SELECT COUNT(*) FROM na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches;
SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches WHERE appliance_batch_id = 'AC-2026-Q1';

-- ============================================================================
-- 5. RAW CLAIMS (~15K rows) - SIMPLIFIED VERSION
-- ============================================================================
-- Note: Full version with spike pattern requires more complex SQL
-- For demo purposes, run the Python script generate_data.py after fixing auth
-- OR manually create a smaller dataset for testing:

CREATE OR REPLACE TABLE na-dbxtraining.demo_bravo_insurance_claims.raw_claims
USING DELTA
AS
WITH claim_base AS (
  SELECT
    CONCAT('CLM-', DATE_FORMAT(claim_date, 'yyyyMMdd'), '-', UPPER(SUBSTR(MD5(CONCAT(policy_id, CAST(claim_date AS STRING), CAST(seq AS STRING))), 1, 6))) AS claim_id,
    policy_id,
    claim_date,
    claim_type,
    claim_amount_usd,
    seq
  FROM (
    SELECT
      CONCAT('POL-', LPAD(CAST(FLOOR(RAND(seq * 41) * 100000) AS STRING), 6, '0')) AS policy_id,
      TIMESTAMP(DATE_SUB(CURRENT_DATE(), CAST(1 + RAND(seq * 43) * 180 AS INT))) AS claim_date,
      CASE
        WHEN RAND(seq * 47) < 0.25 THEN 'water_damage'
        WHEN RAND(seq * 47) < 0.40 THEN 'fire'
        WHEN RAND(seq * 47) < 0.60 THEN 'theft'
        WHEN RAND(seq * 47) < 0.80 THEN 'wind'
        ELSE 'other'
      END AS claim_type,
      ROUND(1000 + RAND(seq * 53) * 15000, 2) AS claim_amount_usd,
      seq
    FROM (SELECT EXPLODE(SEQUENCE(0, 14999)) AS seq)
  )
)
SELECT
  claim_id,
  policy_id,
  CASE WHEN claim_type = 'water_damage' AND RAND(seq * 59) < 0.3 THEN 'APP-000001' ELSE NULL END AS appliance_id,
  CASE WHEN claim_type = 'water_damage' AND RAND(seq * 59) < 0.02 THEN 'AC-2026-Q1' ELSE NULL END AS appliance_batch_id,
  claim_date,
  claim_type,
  claim_amount_usd,
  CASE WHEN claim_type = 'water_damage' THEN 'Water damage from appliance leak' ELSE 'Standard claim' END AS claim_description,
  CASE
    WHEN claim_type = 'water_damage' AND claim_amount_usd > 5000 THEN 'high'
    WHEN claim_amount_usd > 10000 THEN 'high'
    WHEN claim_amount_usd > 3000 THEN 'medium'
    ELSE 'low'
  END AS severity,
  'IL' AS state  -- Simplified: all IL for demo
FROM claim_base;

-- Verify
SELECT COUNT(*) AS total_claims FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims;
SELECT COUNT(*) AS affected_claims FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims WHERE appliance_batch_id = 'AC-2026-Q1';
```

**⚠️ Note:** The SQL version above creates simplified data for testing. For production-quality synthetic data with proper spike patterns and geographic distribution, you need to:
1. Fix the service principal OAuth scopes (add: sql, workspace, databricks-connect)
2. Run `python data_generation/generate_data.py`

---

### ✅ Step 2: Deploy Pipeline (UI Method)

**Method A: Upload Python Notebook**

1. Open **Workspace** in Databricks UI
2. Navigate to `/Repos/<your-user>/`
3. Create folder: `hls_sas_dbx_claims`
4. Upload `pipeline/claims_pipeline.py` as a notebook
5. Go to **Workflows → Delta Live Tables → Create Pipeline**
6. Configure:
   - **Name:** `hls_sas_dbx_claims_pipeline`
   - **Product Edition:** Advanced
   - **Notebook:** Select the uploaded `claims_pipeline.py`
   - **Target:** `na-dbxtraining.hls_sas_dbx_claims`
   - **Storage location:** `/Volumes/na-dbxtraining/hls_sas_dbx_claims/pipeline_storage`
   - **Cluster mode:** Serverless
   - **Enable Photon:** ✓
   - **Configuration:**
     ```
     baseline_weekly_claims: 2500000
     spike_threshold_ratio: 1.25
     affected_batch_id: AC-2026-Q1
     ```
7. Click **Create** and **Start**

**Method B: Deploy via DABs (If you have CLI access)**

```bash
# Would require working auth:
# databricks bundle deploy --target dev
# databricks pipelines start-update <pipeline-id> --full-refresh
```

---

### ✅ Step 3: Create Metric Views

Once the pipeline completes, run this SQL in **Databricks SQL Editor**:

```sql
-- Copy contents from pipeline/metric_views.sql
-- Execute each CREATE OR REPLACE METRIC VIEW statement
```

---

### ✅ Step 4: Verify Deployment

Run these validation queries in SQL Editor:

```sql
-- Check row counts
SELECT 'bronze_claims' AS table_name, COUNT(*) AS rows FROM na-dbxtraining.hls_sas_dbx_claims.bronze_claims
UNION ALL
SELECT 'silver_claims_enriched', COUNT(*) FROM na-dbxtraining.hls_sas_dbx_claims.silver_claims_enriched
UNION ALL
SELECT 'gold_weekly_summary', COUNT(*) FROM na-dbxtraining.hls_sas_dbx_claims.gold_weekly_summary;

-- Check affected batch
SELECT
  COUNT(*) AS affected_claims,
  SUM(claim_amount_usd) AS total_amount
FROM na-dbxtraining.hls_sas_dbx_claims.gold_claims
WHERE is_affected_batch = TRUE;

-- Check for spike alerts
SELECT week, weekly_claims, ratio, status
FROM na-dbxtraining.hls_sas_dbx_claims.gold_weekly_summary
WHERE status = 'ALERT'
ORDER BY week DESC;
```

---

### ✅ Step 5: Create AI/BI Dashboard

1. Go to **SQL → Dashboards → Create Dashboard**
2. Add visualizations:
   - **KPI Tiles:** Weekly claims, peak amount, % vs baseline
   - **Line Chart:** Weekly trend from `gold_weekly_summary`
   - **Bar Chart:** Claims by type from `gold_daily_summary`
   - **Map:** Geographic distribution (state-level bubbles)
3. Save as **"HLS SAS DBX Claims Dashboard"**

---

### ✅ Step 6: Create Genie Space

1. Go to **SQL → Genie Spaces → Create Space**
2. Name: **HLS Claims Investigation**
3. Select tables:
   - `hls_sas_dbx_claims.gold_claims`
   - `hls_sas_dbx_claims.gold_weekly_summary`
   - `hls_sas_dbx_claims.gold_affected_batch_analysis`
   - `hls_sas_dbx_claims.mv_claims_performance`
4. Add instructions:
   ```
   You help investigate insurance claims spikes. Key context:
   - Normal baseline: $2.5M weekly claims
   - Spike threshold: 25% above baseline
   - Affected batch: AC-2026-Q1 (AquaClean DW-9500 dishwashers)
   - When asked about spikes, check weekly_summary for ALERT status
   - Always cite the recall_notice text when discussing affected batch
   ```
5. Save and test: "Why are claims spiking?"

---

### ✅ Step 7: Update resources.json

After successful deployment, update `resources.json`:

```json
{
  "capabilities": {
    "buildable": ["synthetic-data-gen", "sdp", "metric-views", "aibi-dashboards", "genie"],
    "talking_track": ["lakeflow-connect", "genie-one", "genie-code", "unity-catalog"]
  },
  "created_resources": {
    "catalog": "na-dbxtraining",
    "source_schema": "demo_bravo_insurance_claims",
    "pipeline_schema": "hls_sas_dbx_claims",
    "pipeline_id": "<from_ui_after_create>",
    "pipeline_name": "hls_sas_dbx_claims_pipeline",
    "dashboard_id": "<from_ui_after_create>",
    "genie_space_id": "<from_ui_after_create>",
    "metric_views": [
      "hls_sas_dbx_claims.mv_claims_performance",
      "hls_sas_dbx_claims.mv_affected_batch_metrics"
    ]
  }
}
```

---

## Alternative: SQL-Only Pipeline

To deploy the pure SQL version (`claims_pipeline_sql.sql`):

1. Upload `pipeline/claims_pipeline_sql.sql` as a SQL notebook
2. Create pipeline pointing to that notebook instead
3. Everything else remains the same

---

## Troubleshooting

**Issue: "Invalid scope" errors**
- Root cause: Service principal/PAT lacks required OAuth scopes
- Fix: Update token scopes in Azure AD / Databricks settings
- Required scopes: `sql`, `workspace`, `databricks-connect`, `clusters`

**Issue: Pipeline fails with "Table not found"**
- Check that Step 1 (data generation) completed successfully
- Verify source tables exist: `SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims LIMIT 10`

**Issue: Metric Views fail to create**
- Ensure gold tables exist first (`gold_daily_summary`, `gold_claims`)
- Run pipeline to completion before creating Metric Views

---

## Files Ready for Upload

All files are in `/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/`:

- ✅ `pipeline/claims_pipeline.py` — Hybrid Python+SQL pipeline
- ✅ `pipeline/claims_pipeline_sql.sql` — Pure SQL alternative
- ✅ `pipeline/metric_views.sql` — Governed KPI definitions
- ✅ `pipeline/pipeline_config.yml` — Configuration (if using CLI)
- ✅ `specifications/SCHEMAS.md` — Complete schema reference
- ✅ `README.md` — Demo story and walkthrough

**Next:** Follow steps above to deploy via Databricks UI.
