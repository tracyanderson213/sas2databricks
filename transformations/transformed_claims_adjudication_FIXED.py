# ==============================================================================
# TRANSFORMED SAS PIPELINE - PRODUCTION READY (WITH INTELLIGENT LAYER DETECTION)
# ==============================================================================
# Name:           transformed_claims_adjudication.py
# Original File:  claims_adjudication.sas
# Purpose:        Transformed from SAS to Spark Declarative Pipeline (SDP)
# Author:         3Cloud SAS Migration Team
# Transformed:    2026-09-18
# Target:         Databricks SDP (Spark Declarative Pipelines)
# Model:          sas2databricks
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# 2026-09-18 | 3Cloud SAS Migration Team | Initial transformation from SAS
# ------------------------------------------------------------------------------
#
# Medallion Layer Analysis:
# ------------------------------------------------------------------------------
# - fmt_diagcat                    → bronze layer (sas_tanderson_bronze)  [TABLE]
# - work_members                   → bronze layer (sas_tanderson_bronze)  [TABLE]
# - work_providers                 → bronze layer (sas_tanderson_bronze)  [TABLE]
# - work_benefit_plans             → bronze layer (sas_tanderson_bronze)  [TABLE]
# - work_claims_in                 → bronze layer (sas_tanderson_bronze)  [TABLE]
# - flag_eligibility               → silver layer (sas_tanderson_silver)  [VIEW]
# - sort_raw                       → silver layer (sas_tanderson_silver)  [VIEW]
# - sort_raw                       → silver layer (sas_tanderson_silver)  [VIEW]
# - work_claims_elig               → silver layer (sas_tanderson_silver)  [VIEW]
# - work_claims_elig2              → silver layer (sas_tanderson_silver)  [VIEW]
# - work_claims_network            → silver layer (sas_tanderson_silver)  [VIEW]
# - sort_raw                       → silver layer (sas_tanderson_silver)  [VIEW]
# - work_claims_dupflag            → silver layer (sas_tanderson_silver)  [VIEW]
# - sort_raw                       → silver layer (sas_tanderson_silver)  [VIEW]
# - sort_raw                       → silver layer (sas_tanderson_silver)  [VIEW]
# - work_claims_benefit            → silver layer (sas_tanderson_silver)  [VIEW]
# - sort_raw                       → silver layer (sas_tanderson_silver)  [VIEW]
# - work_claims_running            → silver layer (sas_tanderson_silver)  [TABLE]
# - clm_claims_adjudicated         → gold   layer (sas_tanderson_gold)  [TABLE]
# - result                         → gold   layer (sas_tanderson_gold)  [TABLE]
# - clm_claims_adjudicated_report  → gold   layer (sas_tanderson_gold)  [TABLE]
# ------------------------------------------------------------------------------
#
# Notes:
# - Layer detection: Bronze (raw), Silver (transforms), Gold (aggregates)
# - View optimization: Intermediate tables converted to views for efficiency
# - Review business logic carefully before deploying to production
# - Test with sample data before running on full dataset
#
# ==============================================================================

# ==============================================================================
# PARAMETERS (Widget-Driven)
# ==============================================================================

# Unity Catalog configuration (default values, override with widgets)
CATALOG = "na-dbxtraining"
SCHEMA_BRONZE = "sas_tanderson_bronze"    # Raw data ingestion layer (e.g., sas_tanderson_bronze)
SCHEMA_SILVER = "sas_tanderson_silver"    # Business logic transformation layer (e.g., sas_tanderson_silver)
SCHEMA_GOLD = "sas_tanderson_gold"        # Aggregated metrics and reporting layer (e.g., sas_tanderson_gold)

# Source paths
SOURCE_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA_BRONZE}/sas_migration"
INPUT_PATH = f"{SOURCE_VOLUME}/input"

# Data quality settings
ENABLE_EXPECTATIONS = True
EXPECTATION_ACTION = "drop"  # Options: "drop", "fail", "warn"

# View optimization
ENABLE_VIEWS = True  # Convert intermediate tables to views

# ==============================================================================
# IMPORTS
# ==============================================================================
# API Style: dp
#
# DLT Style (backward compatible, still works):
#   from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
#   @dlt.table, @dlt.view
#
# DP/SDP Style (Apache Spark 4.1+ open standard - RECOMMENDED):
#   from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
#   @dp.table (persistent tables)
#   @dp.materialized_view (persistent views)
#   @dp.temporary_view (temporary views)
#
# Note: Databricks contributed SDP to Apache Spark as an open standard.
#       Lakeflow Pipelines (formerly Delta Live Tables) is built on SDP.
#       Both APIs work, but dp/SDP is recommended for forward compatibility.

from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
from pyspark.sql import functions as F
from pyspark.sql import types as T
from datetime import datetime

# ==============================================================================
# ORIGINAL SAS CODE (for reference)
# ==============================================================================
"""
/*******************************************************************
  CLAIMS ADJUDICATION - SAMPLE PROGRAM
  Purpose: Synthetic test case for SAS-to-Databricks conversion testing
  Covers:  DATA step table creation, PROC FORMAT, macros, MERGE,
           PROC SQL joins, RETAIN/duplicate detection, multi-branch
           IF/THEN logic, and summary reporting.
  Note:    All data below is synthetic. Business rules are simplified
           for illustration - not a real adjudication rule set.
********************************************************************/

options mprint mlogic symbolgen;
libname clm "/sasdata/claims_demo";  /* adjust or point to WORK for testing */

/*-------------------------------------------------------------------
  1. REFERENCE TABLES
-------------------------------------------------------------------*/

/* Custom format to bucket diagnosis codes into categories */
proc format;
    value $diagcat
        'E11'  = 'DIABETES'
        'I10'  = 'HYPERTENSION'
        'J45'  = 'ASTHMA'
        'M54'  = 'BACK_PAIN'
        other  = 'OTHER';
run;

/* Member eligibility spans */
data work.members;
    length member_id $10 plan_id $6;
    input member_id $ plan_id $ eff_date :mmddyy10. term_date :mmddyy10. dob :mmddyy10.;
    format eff_date term_date dob mmddyy10.;
    datalines;
M00001 PLNA01 01/01/2025 12/31/2025 05/14/1980
M00002 PLNA01 01/01/2025 06/30/2025 11/02/1975
M00003 PLNB02 03/01/2025 12/31/2025 07/23/1990
M00004 PLNB02 01/01/2025 12/31/2025 01/09/1965
M00005 PLNA01 01/01/2025 12/31/2025 09/30/2001
;
run;

/* Provider network status */
data work.providers;
    length provider_id $10 npi $10 specialty $20 network_status $12;
    input provider_id $ npi $ specialty $ network_status $;
    datalines;
P1001 1234567890 CARDIOLOGY  INNETWORK
P1002 2345678901 PRIMARYCARE INNETWORK
P1003 3456789012 ORTHOPEDIC  OUTOFNETWORK
P1004 4567890123 ENDOCRINOLOGY INNETWORK
;
run;

/* Benefit plan parameters */
data work.benefit_plans;
    length plan_id $6;
    input plan_id $ benefit_year annual_limit copay deductible;
    datalines;
PLNA01 2025 50000 25 500
PLNB02 2025 75000 40 1000
;
run;

/* Incoming claims to adjudicate */
data work.claims_in;
    length claim_id $10 member_id $10 provider_id $10 diag_code $5 proc_code $6 plan_id $6;
    input claim_id $ member_id $ provider_id $ service_date :mmddyy10.
          diag_code $ proc_code $ billed_amount plan_id $;
    format service_date mmddyy10.;
    datalines;
C90001 M00001 P1001 03/15/2025 I10 99213  120.00 PLNA01
C90002 M00002 P1002 07/10/2025 E11 99214  150.00 PLNA01
C90003 M00003 P1003 04/02/2025 M54 97110  200.00 PLNB02
C90004 M00004 P1004 05/20/2025 E11 99215  180.00 PLNB02
C90005 M00001 P1001 03/15/2025 I10 99213  120.00 PLNA01
C90006 M00005 P1002 02/11/2025 J45 94010   90.00 PLNA01
C90007 M00999 P1001 06/01/2025 I10 99213  130.00 PLNA01
;
run;

/*-------------------------------------------------------------------
  2. MACRO - reusable eligibility check
     (converter test target: macro parameter substitution, %IF logic)
-------------------------------------------------------------------*/
%macro flag_eligibility(dsin=, dsout=);
    data &dsout;
        set &dsin;
        if not missing(eff_date) and not missing(term_date) then do;
            if eff_date <= service_date <= term_date then elig_flag = 'Y';
            else elig_flag = 'N';
        end;
        else elig_flag = 'N';
    run;
%mend flag_eligibility;

/*-------------------------------------------------------------------
  3. ELIGIBILITY CHECK - MERGE claims with member spans
-------------------------------------------------------------------*/
proc sort data=work.claims_in; by member_id; run;
proc sort data=work.members;   by member_id; run;

data work.claims_elig;
    merge work.claims_in (in=inclaim)
          work.members    (in=inmember keep=member_id eff_date term_date);
    by member_id;
    if inclaim;                 /* keep claims even if member not found */
    if inmember = 0 then elig_flag = 'N';  /* no member match -> not eligible */
run;

%flag_eligibility(dsin=work.claims_elig, dsout=work.claims_elig2);

/*-------------------------------------------------------------------
  4. NETWORK STATUS CHECK - PROC SQL join
     (converter test target: SQL join -> pandas merge / SQL JOIN)
-------------------------------------------------------------------*/
proc sql;
    create table work.claims_network as
    select a.*,
           b.network_status,
           b.specialty
    from work.claims_elig2 as a
    left join work.providers as b
        on a.provider_id = b.provider_id;
quit;

/*-------------------------------------------------------------------
  5. DUPLICATE CLAIM DETECTION
     (converter test target: RETAIN, FIRST./LAST. logic)
-------------------------------------------------------------------*/
proc sort data=work.claims_network;
    by member_id provider_id service_date proc_code;
run;

data work.claims_dupflag;
    set work.claims_network;
    by member_id provider_id service_date proc_code;
    if not (first.proc_code and last.proc_code) then dup_flag = 'Y';
    else dup_flag = 'N';
run;

/*-------------------------------------------------------------------
  6. BENEFIT LIMIT CHECK - join to plan table, running total by member
-------------------------------------------------------------------*/
proc sort data=work.claims_dupflag; by plan_id; run;
proc sort data=work.benefit_plans; by plan_id; run;

data work.claims_benefit;
    merge work.claims_dupflag (in=inclaim)
          work.benefit_plans  (in=inplan);
    by plan_id;
    if inclaim;
run;

proc sort data=work.claims_benefit; by member_id service_date; run;

data work.claims_running;
    set work.claims_benefit;
    by member_id;
    retain ytd_paid 0;
    if first.member_id then ytd_paid = 0;
    ytd_paid + billed_amount;
    if ytd_paid > annual_limit then limit_exceeded = 'Y';
    else limit_exceeded = 'N';
run;

/*-------------------------------------------------------------------
  7. FINAL ADJUDICATION DECISION
     (converter test target: nested IF/ELSE branching -> CASE WHEN)
-------------------------------------------------------------------*/
data clm.claims_adjudicated;
    set work.claims_running;
    length diag_category $12 adj_status $8 deny_reason $40;
    diag_category = put(diag_code, $diagcat.);

    if elig_flag = 'N' then do;
        adj_status = 'DENIED';
        deny_reason = 'MEMBER NOT ELIGIBLE ON SERVICE DATE';
    end;
    else if dup_flag = 'Y' then do;
        adj_status = 'DENIED';
        deny_reason = 'DUPLICATE CLAIM';
    end;
    else if network_status = 'OUTOFNETWORK' then do;
        adj_status = 'PENDED';
        deny_reason = 'OUT OF NETWORK - MANUAL REVIEW';
    end;
    else if limit_exceeded = 'Y' then do;
        adj_status = 'DENIED';
        deny_reason = 'ANNUAL BENEFIT LIMIT EXCEEDED';
    end;
    else do;
        adj_status = 'APPROVED';
        deny_reason = '';
        paid_amount = billed_amount - copay;
    end;
run;

/*-------------------------------------------------------------------
  8. SUMMARY REPORT
-------------------------------------------------------------------*/
proc sql;
    select adj_status, count(*) as claim_count, sum(billed_amount) as total_billed
    from clm.claims_adjudicated
    group by adj_status;
quit;

proc print data=clm.claims_adjudicated noobs;
    var claim_id member_id adj_status deny_reason diag_category billed_amount paid_amount;
run;

"""

# ==============================================================================
# CONVERTED PIPELINE CODE (from sas2databricks, enhanced with view optimization)
# ==============================================================================


# ==============================================================================
# POST-PROCESSING SUMMARY
# ==============================================================================
#
# ✅ AUTO-GENERATED from SAS DATALINES (ready to use!):
#   ✅ work_members: 5 rows × 5 columns
#      Columns: member_id, plan_id, eff_date, term_date, dob
#   ✅ work_providers: 4 rows × 4 columns
#      Columns: provider_id, npi, specialty, network_status
#   ✅ work_benefit_plans: 2 rows × 5 columns
#      Columns: plan_id, benefit_year, annual_limit, copay, deductible
#   ✅ work_claims_in: 7 rows × 8 columns
#      Columns: claim_id, member_id, provider_id, service_date, diag_code ... (+3 more)
#
# Automatic fixes applied:
#   ✓ Parsed 4 DATALINES blocks from original SAS code
#   ✓   • work_members: 5 rows, 5 columns
#   ✓   • work_providers: 4 rows, 4 columns
#   ✓   • work_benefit_plans: 2 rows, 5 columns
#   ✓   • work_claims_in: 7 rows, 8 columns
#   ✓ Extracted 1 PROC FORMAT definition(s)
#   ✓   • diagcat: 4 mappings
#   ✓ Detected 2 DATA step MERGE pattern(s)
#   ✓   • work_claims_elig: LEFT JOIN on member_id
#   ✓   • work_claims_benefit: LEFT JOIN on plan_id
#   ✓ Detected 1 RETAIN pattern(s) for running totals
#   ✓   • work_claims_running: ytd_paid accumulates billed_amount
#   ✓ Generated 1 format dictionary + UDF
#   ✓ Removed SAS macro placeholder table 'flag_eligibility' (macros are functions, not tables)
#   ✓ Generated correct JOIN for 'work_claims_elig'
#   ✓ Generated correct JOIN for 'work_claims_benefit'
#   ✓ Generated correct Window function for 'work_claims_running'
#   ✓ Successfully auto-generated 4 table(s) from DATALINES
#   ✓ Removed 6 PROC SORT artifact(s) (sort_raw functions)
#   ✓ Replaced SAS format functions with inline CASE expressions
#   ✓ Replaced SAS missing() function with SQL IS NOT NULL
#   ✓ Removed SAS 'then do;' syntax from SQL
#   ✓ Normalized 2 table reference(s) (lib.table → lib_table)
#
# ⚠️  Manual review still required:
#   ⚠️  Consider @dp.temporary_view for 'fmt_diagcat' (small reference data from DATALINES)
#   ⚠️  Consider @dp.temporary_view for 'work_members' (small reference data from DATALINES)
#   ⚠️  Consider @dp.temporary_view for 'work_providers' (small reference data from DATALINES)
#   ⚠️  Consider @dp.temporary_view for 'work_benefit_plans' (small reference data from DATALINES)
#   ⚠️  Consider @dp.temporary_view for 'work_claims_in' (small reference data from DATALINES)
#
# 💡 Recommendations:
#   - Consider using @dp.temporary_view for small reference data:
#     • fmt_diagcat
# ==============================================================================

# Databricks notebook source
# Generated by sas2databricks -> target: Delta Live Tables
# Source: claims_adjudication.sas
from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
from pyspark.sql import functions as F

# ==============================================================================
# PROC FORMAT Definitions (auto-generated)
# ==============================================================================

DIAGCAT_FORMAT = {'E11': 'DIABETES', 'I10': 'HYPERTENSION', 'J45': 'ASTHMA', 'M54': 'BACK_PAIN'}
@F.udf(returnType=T.StringType())
def format_diagcat(code):
    """Apply diagcat format (from PROC FORMAT)"""
    return DIAGCAT_FORMAT.get(code, 'OTHER')


@dp.table(name='sas_tanderson_bronze.work_members', comment='SAS data')
def work_members():
    """Auto-generated from SAS DATALINES"""
    data = [
        ("M00001", "PLNA01", "2025-01-01", "2025-12-31", "1980-05-14"),
        ("M00002", "PLNA01", "2025-01-01", "2025-06-30", "1975-11-02"),
        ("M00003", "PLNB02", "2025-03-01", "2025-12-31", "1990-07-23"),
        ("M00004", "PLNB02", "2025-01-01", "2025-12-31", "1965-01-09"),
        ("M00005", "PLNA01", "2025-01-01", "2025-12-31", "2001-09-30"),
    ]
    schema = "member_id STRING, plan_id STRING, eff_date STRING, term_date STRING, dob STRING"
    return spark.createDataFrame(data, schema).select(
        "member_id",
        "plan_id",
        F.to_date("eff_date").alias("eff_date"),
        F.to_date("term_date").alias("term_date"),
        F.to_date("dob").alias("dob"),
    )

@dp.table(name='sas_tanderson_bronze.work_providers', comment='SAS data')
def work_providers():
    """Auto-generated from SAS DATALINES"""
    data = [
        ("P1001", "1234567890", "CARDIOLOGY", "INNETWORK"),
        ("P1002", "2345678901", "PRIMARYCARE", "INNETWORK"),
        ("P1003", "3456789012", "ORTHOPEDIC", "OUTOFNETWORK"),
        ("P1004", "4567890123", "ENDOCRINOLOGY", "INNETWORK"),
    ]
    schema = "provider_id STRING, npi STRING, specialty STRING, network_status STRING"
    return spark.createDataFrame(data, schema)

@dp.table(name='sas_tanderson_bronze.work_benefit_plans', comment='SAS data')
def work_benefit_plans():
    """Auto-generated from SAS DATALINES"""
    data = [
        ("PLNA01", 2025, 50000, 25, 500),
        ("PLNB02", 2025, 75000, 40, 1000),
    ]
    schema = "plan_id STRING, benefit_year INT, annual_limit INT, copay INT, deductible INT"
    return spark.createDataFrame(data, schema)

@dp.table(name='sas_tanderson_bronze.work_claims_in', comment='SAS data')
def work_claims_in():
    """Auto-generated from SAS DATALINES"""
    data = [
        ("C90001", "M00001", "P1001", "2025-03-15", "I10", "99213", 120.00, "PLNA01"),
        ("C90002", "M00002", "P1002", "2025-07-10", "E11", "99214", 150.00, "PLNA01"),
        ("C90003", "M00003", "P1003", "2025-04-02", "M54", "97110", 200.00, "PLNB02"),
        ("C90004", "M00004", "P1004", "2025-05-20", "E11", "99215", 180.00, "PLNB02"),
        ("C90005", "M00001", "P1001", "2025-03-15", "I10", "99213", 120.00, "PLNA01"),
        ("C90006", "M00005", "P1002", "2025-02-11", "J45", "94010", 90.00, "PLNA01"),
        ("C90007", "M00999", "P1001", "2025-06-01", "I10", "99213", 130.00, "PLNA01"),
    ]
    schema = "claim_id STRING, member_id STRING, provider_id STRING, service_date STRING, diag_code STRING, proc_code STRING, billed_amount DOUBLE, plan_id STRING"
    return spark.createDataFrame(data, schema).select(
        "claim_id",
        "member_id",
        "provider_id",
        F.to_date("service_date").alias("service_date"),
        "diag_code",
        "proc_code",
        "billed_amount",
        "plan_id",
    )

@dp.materialized_view(name='sas_tanderson_silver.work_claims_elig')
def work_claims_elig():
    """Converted from SAS DATA step MERGE"""
    left_df = spark.read.table("sas_tanderson_bronze.work_claims_in")
    right_df = spark.read.table("sas_tanderson_bronze.work_members").select("member_id", "eff_date", "term_date")
    
    # LEFT JOIN (from SAS MERGE)
    result = left_df.join(right_df, "member_id", "left")
    
    # Add in= flags (from SAS MERGE options)
    result = result.withColumn("inclaim", F.lit(1))
    result = result.withColumn("inmember", 
        F.when(F.col("eff_date").isNotNull(), F.lit(1)).otherwise(F.lit(0))
    )
    return result

@dp.materialized_view(name='sas_tanderson_silver.work_claims_elig2', comment='SAS data')
def work_claims_elig2():
    """Apply eligibility flag logic (from flag_eligibility macro)"""
    return spark.sql("""
        SELECT *,
            CASE
                WHEN eff_date IS NOT NULL
                    AND term_date IS NOT NULL
                    AND service_date BETWEEN eff_date AND term_date
                THEN 'Y'
                ELSE 'N'
            END AS elig_flag
        FROM sas_tanderson_silver.work_claims_elig
    """)

@dp.materialized_view(name='sas_tanderson_silver.work_claims_network', comment='SAS sql')
def work_claims_network():
    return spark.sql("""SELECT
  a.*,
  b.network_status,
  b.specialty
FROM sas_tanderson_silver.work_claims_elig2 AS a
LEFT JOIN sas_tanderson_bronze.work_providers AS b
  ON a.provider_id = b.provider_id""")

@dp.materialized_view(name='sas_tanderson_silver.work_claims_dupflag', comment='SAS data')  # [REVIEW]
def work_claims_dupflag():
    return spark.sql("""SELECT *,
  CASE WHEN NOT ((row_number() OVER (PARTITION BY member_id, provider_id, service_date, proc_code ORDER BY _row_id) = 1) AND (row_number() OVER (PARTITION BY member_id, provider_id, service_date, proc_code ORDER BY _row_id DESC) = 1)) THEN 'Y' ELSE 'N' END AS dup_flag
FROM (SELECT *, monotonically_increasing_id() AS _row_id FROM sas_tanderson_silver.work_claims_network)""")

@dp.materialized_view(name='sas_tanderson_silver.work_claims_benefit')
def work_claims_benefit():
    """Converted from SAS DATA step MERGE"""
    left_df = spark.read.table("sas_tanderson_silver.work_claims_dupflag")
    right_df = spark.read.table("sas_tanderson_bronze.work_benefit_plans")
    
    # LEFT JOIN (from SAS MERGE)
    result = left_df.join(right_df, "plan_id", "left")
    
    # Add in= flags (from SAS MERGE options)
    result = result.withColumn("inclaim", F.lit(1))
    result = result.withColumn("inplan", 
        F.when(F.col("plan_id").isNotNull(), F.lit(1)).otherwise(F.lit(0))
    )
    return result

@dp.table(name='sas_tanderson_silver.work_claims_running')
def work_claims_running():
    """Converted from SAS RETAIN - running total per member_id"""
    from pyspark.sql.window import Window
    
    # Window for running total (ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    window = Window.partitionBy("member_id") \
                   .orderBy("member_id", "service_date") \
                   .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    # V7: Layer-aware table reference with full schema name
    return spark.read.table("sas_tanderson_silver.work_claims_benefit") \
        .withColumn("ytd_paid", F.sum("billed_amount").over(window)) \
        .withColumn("limit_exceeded",
                    F.when(F.col("ytd_paid") > F.col("annual_limit"), "Y").otherwise("N"))

@dp.table(name='sas_tanderson_gold.clm_claims_adjudicated', comment='SAS data')
def clm_claims_adjudicated():
    """Final adjudication with nested IF/THEN/ELSE logic from SAS"""
    return spark.sql("""
        SELECT *,
            CASE diag_code
                WHEN 'E11' THEN 'DIABETES'
                WHEN 'I10' THEN 'HYPERTENSION'
                WHEN 'J45' THEN 'ASTHMA'
                WHEN 'M54' THEN 'BACK_PAIN'
                ELSE 'OTHER'
            END AS diag_category,

            CASE
                WHEN elig_flag = 'N' THEN 'DENIED'
                WHEN dup_flag = 'Y' THEN 'DENIED'
                WHEN network_status = 'OUTOFNETWORK' THEN 'PENDED'
                WHEN limit_exceeded = 'Y' THEN 'DENIED'
                ELSE 'APPROVED'
            END AS adj_status,

            CASE
                WHEN elig_flag = 'N' THEN 'MEMBER NOT ELIGIBLE ON SERVICE DATE'
                WHEN dup_flag = 'Y' THEN 'DUPLICATE CLAIM'
                WHEN network_status = 'OUTOFNETWORK' THEN 'OUT OF NETWORK - MANUAL REVIEW'
                WHEN limit_exceeded = 'Y' THEN 'ANNUAL BENEFIT LIMIT EXCEEDED'
                ELSE ''
            END AS deny_reason,

            CASE
                WHEN elig_flag = 'N' OR dup_flag = 'Y' OR network_status = 'OUTOFNETWORK' OR limit_exceeded = 'Y'
                THEN NULL
                ELSE billed_amount - copay
            END AS paid_amount

        FROM sas_tanderson_silver.work_claims_running""")

@dp.table(name='sas_tanderson_gold.result', comment='SAS sql')
def result():
    return spark.sql("""SELECT
  adj_status,
  COUNT(*) AS claim_count,
  SUM(billed_amount) AS total_billed
FROM sas_tanderson_gold.clm_claims_adjudicated
GROUP BY
  adj_status""")

# ==============================================================================
# HELPER: Add Bronze Metadata Columns
# ==============================================================================

def add_bronze_metadata(df, source_file="claims_adjudication.sas", layer="bronze"):
    """
    Adds standard metadata columns for audit trail

    Args:
        df: Input DataFrame
        source_file: Name of source SAS file
        layer: Medallion layer (bronze, silver, gold)

    Returns:
        DataFrame with metadata columns
    """
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
        .withColumn("medallion_layer", F.lit(layer))
    )

# ==============================================================================
# LAYER-SPECIFIC SCHEMAS
# ==============================================================================

def get_schema_for_layer(layer):
    """Returns appropriate schema based on medallion layer"""
    if layer == "bronze":
        return SCHEMA_BRONZE
    elif layer == "gold":
        return SCHEMA_GOLD
    else:
        return SCHEMA_SILVER

# ==============================================================================
# ENHANCED TABLES/VIEWS (with layer-specific schemas and metadata)
# ==============================================================================

# TODO: Review the tables above and enhance with:
# 1. Correct schema based on detected layer
# 2. Bronze metadata for audit trail
# 3. Data quality expectations
#
# Example pattern:
#
# @dlt.view(  # Changed from table to view for intermediate processing
#     name="silver_intermediate_claims",
#     comment="Intermediate transformation - Silver layer"
# )
# def silver_intermediate_claims():
#     df = spark.table("LIVE.bronze_claims")
#     # Add transformation logic
#     return df.filter(F.col("status") == "active")
#
# @dlt.table(
#     name="gold_claims_summary",
#     comment="Final aggregated metrics - Gold layer",
#     schema=f"`{CATALOG}`.{SCHEMA_GOLD}"  # Write to Gold schema
# )
# @dlt.expect_or_drop("valid_count", "claim_count > 0")
# def gold_claims_summary():
#     df = spark.table("LIVE.silver_intermediate_claims")
#     result = df.groupBy("region").agg(
#         F.count("*").alias("claim_count"),
#         F.sum("amount").alias("total_amount")
#     )
#     return add_bronze_metadata(result, layer="gold")

# ==============================================================================
# DETECTED TABLE ANALYSIS
# ==============================================================================
"""
Intelligent layer detection results:

Table Name                     | Layer  | Schema               | Type
---------------------------------------------------------------------------
fmt_diagcat                    | bronze | sas_tanderson_bronze | TABLE
work_members                   | bronze | sas_tanderson_bronze | TABLE
work_providers                 | bronze | sas_tanderson_bronze | TABLE
work_benefit_plans             | bronze | sas_tanderson_bronze | TABLE
work_claims_in                 | bronze | sas_tanderson_bronze | TABLE
flag_eligibility               | silver | sas_tanderson_silver | VIEW 
sort_raw                       | silver | sas_tanderson_silver | VIEW 
sort_raw                       | silver | sas_tanderson_silver | VIEW 
work_claims_elig               | silver | sas_tanderson_silver | VIEW 
work_claims_elig2              | silver | sas_tanderson_silver | VIEW 
work_claims_network            | silver | sas_tanderson_silver | VIEW 
sort_raw                       | silver | sas_tanderson_silver | VIEW 
work_claims_dupflag            | silver | sas_tanderson_silver | VIEW 
sort_raw                       | silver | sas_tanderson_silver | VIEW 
sort_raw                       | silver | sas_tanderson_silver | VIEW 
work_claims_benefit            | silver | sas_tanderson_silver | VIEW 
sort_raw                       | silver | sas_tanderson_silver | VIEW 
work_claims_running            | silver | sas_tanderson_silver | TABLE
clm_claims_adjudicated         | gold   | sas_tanderson_gold   | TABLE
result                         | gold   | sas_tanderson_gold   | TABLE
clm_claims_adjudicated_report  | gold   | sas_tanderson_gold   | TABLE

Recommendations:
- Bronze tables: Add bronze_metadata for audit trail
- Silver tables: Add data quality expectations
- Gold tables: Verify aggregation logic matches SAS
- Views: Use for intermediate transformations (no persistence)

# ==============================================================================
# DATA QUALITY EXPECTATIONS
# ==============================================================================

# Add expectations based on SAS validation rules
# Example patterns by layer:
#
# Bronze (data quality at ingestion):
# @dlt.expect_or_drop("valid_dates", "date_col >= '2020-01-01'")
# @dlt.expect_or_drop("no_nulls_in_key", "key_col IS NOT NULL")
#
# Silver (business rule validation):
# @dlt.expect_or_warn("valid_status", "status IN ('active', 'pending', 'closed')")
# @dlt.expect_or_drop("positive_amounts", "amount > 0")
#
# Gold (aggregation validation):
# @dlt.expect("min_record_count", "count > 0")
# @dlt.expect("valid_totals", "total_amount >= 0")

# ==============================================================================
# END OF CONVERTED PIPELINE
# ==============================================================================
#
# Deployment checklist:
# □ Review layer assignments (Bronze/Silver/Gold)
# □ Verify schema configuration for each layer
# □ Update view vs table decisions
# □ Add bronze metadata to appropriate tables
# □ Test with sample data
# □ Validate output matches SAS results
# □ Update widgets for prod deployment
# □ Deploy via DAB or pipeline UI
#
# ==============================================================================
"""
