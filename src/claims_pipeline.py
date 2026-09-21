# Databricks notebook source
"""
HLS SAS DBX Migration — Claims Analytics Pipeline

Migrated from SAS Enterprise Guide claims processing:
- Bronze: Raw data ingestion (replaces SAS/ACCESS + LIBNAME statements)
- Silver: Business rules & transformations (replaces SAS DATA steps + PROC SQL)
- Gold: Analytics aggregations (replaces SAS PROC SUMMARY + PROC FREQ)

SAS Business Rules Extracted by sas2databricks Accelerator:
- Baseline threshold: 2500000 (from %let baseline_claims = 2500000;)
- Spike threshold: 1.25 (from %let spike_ratio = 1.25;)
- Affected batch: AC-2026-Q1 (from macro variable)
- Severity classification logic (from SAS CASE statements)

Modern SDP API: Uses `pipelines as dp` (formerly `dlt`)
"""

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.types import *

# Configuration
CATALOG = "na-dbxtraining"
SCHEMA = "hls_sas_dbx_claims"
VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

# SAS business rule constants (extracted from SAS macros)
BASELINE_WEEKLY_CLAIMS = 2500000
SPIKE_THRESHOLD_RATIO = 1.25
AFFECTED_BATCH_ID = "AC-2026-Q1"

# ==============================================================================
# BRONZE LAYER — Raw Ingestion
# Replaces: SAS LIBNAME + PROC IMPORT + initial data steps
# ==============================================================================

@dp.table(
    name="bronze_policyholders",
    comment="Raw policyholder data from legacy SAS system. Replaces SAS dataset: WORK.RAW_POLICIES"
)
def bronze_policyholders():
    """
    SAS equivalent:
    libname source '/sas/claims/raw';
    data work.raw_policies;
        set source.policies;
    run;
    """
    return spark.read.table(f"`{CATALOG}`.demo_bravo_insurance_claims.raw_policyholders")

@dp.table(
    name="bronze_appliances",
    comment="Raw appliance catalog. Replaces SAS dataset: REFDATA.APPLIANCES"
)
def bronze_appliances():
    return spark.read.table(f"`{CATALOG}`.demo_bravo_insurance_claims.raw_appliances")

@dp.table(
    name="bronze_appliance_batches",
    comment="Manufacturing batch data with recall notices. Replaces SAS dataset: REFDATA.BATCHES"
)
def bronze_appliance_batches():
    return spark.read.table(f"`{CATALOG}`.demo_bravo_insurance_claims.raw_appliance_batches")

@dp.table(
    name="bronze_claims",
    comment="Raw claims from claims processing system. Replaces SAS dataset: SOURCE.CLAIMS"
)
@dp.expect_all({
    "valid_claim_id": "claim_id IS NOT NULL",
    "valid_amount": "claim_amount_usd > 0",
    "valid_date": "claim_date IS NOT NULL"
})
def bronze_claims():
    """
    SAS data quality checks migrated to SDP expectations:
    - proc sql; select * from claims where claim_id is null; quit; → expect "valid_claim_id"
    - where claim_amount > 0; → expect "valid_amount"
    """
    return spark.read.table(f"`{CATALOG}`.demo_bravo_insurance_claims.raw_claims")

# ==============================================================================
# SILVER LAYER — Business Rules & Enrichment
# Replaces: SAS DATA steps, PROC SQL joins, macro variable expansions
# ==============================================================================

@dp.table(
    name="silver_claims_enriched",
    comment="Claims enriched with policyholder, appliance, and batch information. Applies SAS business rules for severity classification and affected batch flagging."
)
@dp.expect_or_drop("positive_amount", "claim_amount_usd > 0")
@dp.expect_or_drop("valid_policy", "policy_id IS NOT NULL")
def silver_claims_enriched():
    """
    Replaces SAS code:

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
    """
    bronze_claims = spark.read.table("bronze_claims")
    bronze_policies = spark.read.table("bronze_policyholders")
    bronze_appliances = spark.read.table("bronze_appliances")
    bronze_batches = spark.read.table("bronze_appliance_batches")

    return (
        bronze_claims
        .join(bronze_policies, "policy_id", "left")
        .join(bronze_appliances, "appliance_id", "left")
        .join(bronze_batches,
              (bronze_claims.appliance_batch_id == bronze_batches.appliance_batch_id),
              "left")
        .select(
            # Claim fields
            bronze_claims["*"],
            # Policyholder fields
            bronze_policies.policyholder_name,
            bronze_policies.state,
            bronze_policies.city,
            bronze_policies.policyholder_lat,
            bronze_policies.policyholder_lng,
            bronze_policies.policy_type,
            bronze_policies.coverage_limit_usd,
            # Appliance fields
            bronze_appliances.model_name,
            bronze_appliances.manufacturer,
            bronze_appliances.category,
            # Batch fields
            bronze_batches.plant_location,
            bronze_batches.status.alias("batch_status"),
            # Business rules
            F.when(bronze_claims.appliance_batch_id == AFFECTED_BATCH_ID, True)
             .otherwise(False)
             .alias("is_affected_batch"),
            # SAS severity classification macro
            F.when(
                (bronze_claims.claim_type == "water_damage") &
                (bronze_claims.claim_amount_usd > 5000), "high"
            )
            .when(bronze_claims.claim_amount_usd > 10000, "high")
            .when(bronze_claims.claim_amount_usd > 3000, "medium")
            .otherwise("low")
            .alias("severity")
        )
    )

# ==============================================================================
# GOLD LAYER — Analytics-Ready Aggregations
# Replaces: SAS PROC SUMMARY, PROC FREQ, PROC MEANS output
# ==============================================================================

@dp.table(
    name="gold_claims",
    comment="Denormalized claims fact table for analytics. Replaces SAS output: ANALYTICS.CLAIMS_FACT"
)
def gold_claims():
    """
    Final analytics table - replaces SAS:

    data analytics.claims_fact;
        set work.claims_enriched;
    run;
    """
    return spark.read.table("silver_claims_enriched")

# ==============================================================================
# GOLD LAYER — SQL Aggregations (Option 3: Hybrid)
# Simple aggregations use SQL for familiarity to SAS PROC SQL teams
# ==============================================================================

@dp.table(
    name="gold_daily_summary",
    comment="Daily claims aggregations by state and type. Replaces SAS PROC SUMMARY output."
)
def gold_daily_summary():
    """
    Replaces SAS code:

    proc summary data=work.claims_enriched nway;
        class claim_date state claim_type;
        var claim_amount_usd;
        output out=analytics.daily_summary
            n=claim_count
            sum=claim_amount_usd;
    run;

    Migration Note: Using SQL syntax familiar to PROC SQL programmers.
    Modern SDP: No LIVE prefix needed - reference tables by name directly.
    """
    return spark.sql("""
        SELECT
            TO_DATE(claim_date) AS date,
            state,
            claim_type,
            COUNT(*) AS claim_count,
            SUM(claim_amount_usd) AS claim_amount_usd
        FROM silver_claims_enriched
        GROUP BY date, state, claim_type
    """)

@dp.table(
    name="gold_weekly_summary",
    comment="Weekly claims rollup with baseline comparison. Replaces SAS weekly_claims macro output."
)
def gold_weekly_summary():
    """
    Replaces SAS code:

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

    Migration Note: Macro variables become SQL literals or pipeline config.
    Modern SDP: No LIVE prefix needed - reference tables by name directly.
    """
    return spark.sql(f"""
        WITH weekly_agg AS (
            SELECT
                DATE_TRUNC('week', claim_date) AS week,
                COUNT(*) AS claim_count,
                SUM(claim_amount_usd) AS weekly_claims
            FROM silver_claims_enriched
            GROUP BY week
        )
        SELECT
            week,
            claim_count,
            weekly_claims,
            weekly_claims / {BASELINE_WEEKLY_CLAIMS} AS ratio,
            ((weekly_claims / {BASELINE_WEEKLY_CLAIMS}) - 1) * 100 AS vs_baseline_pct,
            CASE
                WHEN weekly_claims / {BASELINE_WEEKLY_CLAIMS} > {SPIKE_THRESHOLD_RATIO}
                THEN 'ALERT'
                ELSE 'NORMAL'
            END AS status
        FROM weekly_agg
        ORDER BY week
    """)

@dp.table(
    name="gold_affected_batch_analysis",
    comment="Analysis of affected appliance batch. Replaces SAS batch_analysis stored process."
)
def gold_affected_batch_analysis():
    """
    Replaces SAS stored process:

    %macro batch_analysis(batch_id=);
        proc freq data=work.claims_enriched;
            where appliance_batch_id = "&batch_id";
            tables state * claim_type / out=analytics.batch_analysis;
        run;
    %mend;
    %batch_analysis(batch_id=AC-2026-Q1);

    Migration Note: Macro parameter becomes SQL WHERE clause.
    Modern SDP: No LIVE prefix needed - reference tables by name directly.
    """
    return spark.sql(f"""
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
            FROM silver_claims_enriched
            WHERE is_affected_batch = TRUE
            GROUP BY state, claim_type, model_name, plant_location
        )
        SELECT
            *,
            100.0 * claim_count / SUM(claim_count) OVER () AS pct_of_total
        FROM batch_summary
    """)
