-- ============================================================================
-- HLS SAS DBX Migration — Claims Analytics Pipeline (SQL Alternative)
-- ============================================================================
--
-- Alternative Implementation: Pure SQL Approach (Option 1)
-- For teams migrating PROC SQL-heavy SAS code with minimal Python dependencies
--
-- Produces IDENTICAL output to claims_pipeline.py
-- Choose this version if your SAS team is primarily PROC SQL-based
--
-- Migrated from SAS Enterprise Guide claims processing:
-- - Bronze: Raw data ingestion (replaces SAS/ACCESS + LIBNAME statements)
-- - Silver: Business rules & transformations (replaces PROC SQL)
-- - Gold: Analytics aggregations (replaces PROC SUMMARY + PROC FREQ)
--
-- SAS Business Rules:
-- - Baseline threshold: 2500000 (from %let baseline_claims = 2500000;)
-- - Spike threshold: 1.25 (from %let spike_ratio = 1.25;)
-- - Affected batch: AC-2026-Q1 (from macro variable)
-- ============================================================================

-- Configuration (replace with your catalog/schema)
-- CATALOG: na-dbxtraining
-- SCHEMA: hls_sas_dbx_claims
-- SOURCE_SCHEMA: demo_bravo_insurance_claims (raw data landing zone)

-- ============================================================================
-- BRONZE LAYER — Raw Ingestion
-- Replaces: SAS LIBNAME + PROC IMPORT
-- ============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_policyholders
COMMENT 'Raw policyholder data from legacy SAS system. Replaces SAS dataset: WORK.RAW_POLICIES'
AS SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_policyholders;

-- SAS equivalent:
-- libname source '/sas/claims/raw';
-- data work.raw_policies;
--     set source.policies;
-- run;

CREATE OR REFRESH STREAMING TABLE bronze_appliances
COMMENT 'Raw appliance catalog. Replaces SAS dataset: REFDATA.APPLIANCES'
AS SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_appliances;

CREATE OR REFRESH STREAMING TABLE bronze_appliance_batches
COMMENT 'Manufacturing batch data with recall notices. Replaces SAS dataset: REFDATA.BATCHES'
AS SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_appliance_batches;

CREATE OR REFRESH STREAMING TABLE bronze_claims (
  CONSTRAINT valid_claim_id EXPECT (claim_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_amount EXPECT (claim_amount_usd > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_date EXPECT (claim_date IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Raw claims from claims processing system. Replaces SAS dataset: SOURCE.CLAIMS'
AS SELECT * FROM na-dbxtraining.demo_bravo_insurance_claims.raw_claims;

-- SAS data quality checks migrated to DLT constraints:
-- proc sql;
--   select * from claims where claim_id is null;  /* → CONSTRAINT valid_claim_id */
--   select * from claims where claim_amount <= 0; /* → CONSTRAINT valid_amount */
-- quit;

-- ============================================================================
-- SILVER LAYER — Business Rules & Enrichment
-- Replaces: PROC SQL joins, macro variable expansions, CASE logic
-- ============================================================================

CREATE OR REFRESH STREAMING TABLE silver_claims_enriched (
  CONSTRAINT positive_amount EXPECT (claim_amount_usd > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_policy EXPECT (policy_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Claims enriched with policyholder, appliance, and batch information. Applies SAS business rules for severity classification and affected batch flagging.'
AS
-- Replaces SAS PROC SQL code:
/*
proc sql;
    create table work.claims_enriched as
    select
        c.*,
        p.policyholder_name,
        p.state,
        p.city,
        p.policy_type,
        a.model_name,
        a.category,
        b.plant_location,
        case
            when b.appliance_batch_id = "&affected_batch" then 1
            else 0
        end as is_affected_batch,
        case
            when c.claim_type = 'water_damage' and c.claim_amount > 5000 then 'high'
            when c.claim_amount > 10000 then 'high'
            when c.claim_amount > 3000 then 'medium'
            else 'low'
        end as severity
    from claims c
    left join policies p on c.policy_id = p.policy_id
    left join appliances a on c.appliance_id = a.appliance_id
    left join batches b on c.appliance_batch_id = b.appliance_batch_id;
quit;
*/
SELECT
    -- Claim fields
    c.*,
    -- Policyholder fields
    p.policyholder_name,
    p.state,
    p.city,
    p.policyholder_lat,
    p.policyholder_lng,
    p.policy_type,
    p.coverage_limit_usd,
    -- Appliance fields
    a.model_name,
    a.manufacturer,
    a.category,
    -- Batch fields
    b.plant_location,
    b.status AS batch_status,
    -- Business Rule 1: Affected Batch Flagging (from SAS macro)
    CASE
        WHEN c.appliance_batch_id = 'AC-2026-Q1' THEN TRUE
        ELSE FALSE
    END AS is_affected_batch,
    -- Business Rule 2: Severity Classification (from SAS CASE statement)
    CASE
        WHEN c.claim_type = 'water_damage' AND c.claim_amount_usd > 5000 THEN 'high'
        WHEN c.claim_amount_usd > 10000 THEN 'high'
        WHEN c.claim_amount_usd > 3000 THEN 'medium'
        ELSE 'low'
    END AS severity
FROM STREAM(LIVE.bronze_claims) c
LEFT JOIN STREAM(LIVE.bronze_policyholders) p ON c.policy_id = p.policy_id
LEFT JOIN STREAM(LIVE.bronze_appliances) a ON c.appliance_id = a.appliance_id
LEFT JOIN STREAM(LIVE.bronze_appliance_batches) b ON c.appliance_batch_id = b.appliance_batch_id;

-- ============================================================================
-- GOLD LAYER — Analytics-Ready Aggregations
-- Replaces: SAS PROC SUMMARY, PROC FREQ, PROC MEANS output
-- ============================================================================

CREATE OR REFRESH LIVE TABLE gold_claims
COMMENT 'Denormalized claims fact table for analytics. Replaces SAS output: ANALYTICS.CLAIMS_FACT'
AS
-- Replaces SAS:
-- data analytics.claims_fact;
--     set work.claims_enriched;
-- run;
SELECT * FROM LIVE.silver_claims_enriched;

CREATE OR REFRESH LIVE TABLE gold_daily_summary
COMMENT 'Daily claims aggregations by state and type. Replaces SAS PROC SUMMARY output.'
AS
-- Replaces SAS:
/*
proc summary data=work.claims_enriched nway;
    class claim_date state claim_type;
    var claim_amount_usd;
    output out=analytics.daily_summary
        n=claim_count
        sum=claim_amount_usd;
run;
*/
SELECT
    TO_DATE(claim_date) AS date,
    state,
    claim_type,
    COUNT(*) AS claim_count,
    SUM(claim_amount_usd) AS claim_amount_usd
FROM LIVE.silver_claims_enriched
GROUP BY date, state, claim_type;

CREATE OR REFRESH LIVE TABLE gold_weekly_summary
COMMENT 'Weekly claims rollup with baseline comparison. Replaces SAS weekly_claims macro output.'
AS
-- Replaces SAS macro:
/*
%macro weekly_rollup;
    %let baseline = 2500000;
    %let spike_threshold = 1.25;

    proc sql;
        create table analytics.weekly_claims as
        select
            intnx('week', claim_date, 0) as week,
            sum(claim_amount_usd) as weekly_claims,
            calculated weekly_claims / &baseline as ratio,
            case
                when calculated ratio > &spike_threshold then 'ALERT'
                else 'NORMAL'
            end as status
        from work.claims_enriched
        group by calculated week;
    quit;
%mend;
%weekly_rollup;
*/
WITH weekly_agg AS (
    SELECT
        DATE_TRUNC('week', claim_date) AS week,
        COUNT(*) AS claim_count,
        SUM(claim_amount_usd) AS weekly_claims
    FROM LIVE.silver_claims_enriched
    GROUP BY week
)
SELECT
    week,
    claim_count,
    weekly_claims,
    weekly_claims / 2500000 AS ratio,  -- SAS macro: %let baseline = 2500000
    ((weekly_claims / 2500000) - 1) * 100 AS vs_baseline_pct,
    CASE
        WHEN weekly_claims / 2500000 > 1.25  -- SAS macro: %let spike_threshold = 1.25
        THEN 'ALERT'
        ELSE 'NORMAL'
    END AS status
FROM weekly_agg
ORDER BY week;

CREATE OR REFRESH LIVE TABLE gold_affected_batch_analysis
COMMENT 'Analysis of affected appliance batch. Replaces SAS batch_analysis stored process.'
AS
-- Replaces SAS stored process:
/*
%macro batch_analysis(batch_id=);
    proc freq data=work.claims_enriched;
        where appliance_batch_id = "&batch_id";
        tables state * claim_type / out=analytics.batch_analysis;
    run;

    proc means data=work.claims_enriched sum mean min max;
        where appliance_batch_id = "&batch_id";
        class state claim_type;
        var claim_amount_usd;
    run;
%mend;
%batch_analysis(batch_id=AC-2026-Q1);
*/
WITH batch_summary AS (
    SELECT
        state,
        claim_type,
        model_name,
        plant_location,
        COUNT(*) AS claim_count,
        SUM(claim_amount_usd) AS total_amount,
        AVG(claim_amount_usd) AS avg_amount,
        MIN(claim_date) AS first_claim_date,
        MAX(claim_date) AS last_claim_date
    FROM LIVE.silver_claims_enriched
    WHERE is_affected_batch = TRUE  -- SAS: where appliance_batch_id = "&affected_batch"
    GROUP BY state, claim_type, model_name, plant_location
)
SELECT
    *,
    100.0 * claim_count / SUM(claim_count) OVER () AS pct_of_total
FROM batch_summary;

-- ============================================================================
-- DEPLOYMENT
-- ============================================================================
-- To deploy this SQL pipeline:
--
-- 1. Create pipeline via UI:
--    - Workspace → Workflows → Delta Live Tables → Create Pipeline
--    - Name: hls_sas_dbx_claims_pipeline_sql
--    - Notebook: /path/to/claims_pipeline_sql.sql
--    - Target: na-dbxtraining.hls_sas_dbx_claims
--    - Enable serverless & Photon
--
-- 2. OR via CLI/API (create pipeline_config_sql.yml first):
--    databricks pipelines create --json @pipeline/pipeline_config_sql.yml
--
-- 3. Run:
--    databricks pipelines start-update <pipeline_id> --full-refresh
--
-- ============================================================================
-- MIGRATION GUIDANCE
-- ============================================================================
--
-- When to use SQL vs Python pipelines:
--
-- ✓ Use SQL (this file) if:
--   - Your SAS codebase is 80%+ PROC SQL
--   - Team has strong SQL skills but limited Python experience
--   - Transformations are mostly joins, aggregations, CASE statements
--   - You want minimal syntax changes from SAS → Databricks
--
-- ✓ Use Python (claims_pipeline.py) if:
--   - SAS code has complex DATA steps with custom functions
--   - Need UDFs, window functions with complex partitioning
--   - Want to leverage PySpark libraries (pandas UDFs, ML pipelines)
--   - Team is already learning Python for ML/AI work
--
-- ✓ Use Hybrid (Option 3) if:
--   - Different layers have different complexity
--   - Want to show both approaches in one pipeline
--   - Migrating incrementally (start SQL, evolve to Python)
--
-- Both approaches produce identical Delta tables and work with:
-- - Metric Views (SQL-based, language-agnostic)
-- - AI/BI Dashboards (reads Delta tables)
-- - Genie Agents (natural language, doesn't care about pipeline language)
-- ============================================================================
