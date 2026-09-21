# Databricks notebook source
# MAGIC %md
# MAGIC # 02b - Upload Comprehensive Claims Adjudication Example
# MAGIC
# MAGIC **Purpose:** Upload comprehensive SAS claims example covering ALL major SAS features
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC
# MAGIC **What this does:**
# MAGIC - Uploads complete claims adjudication SAS program
# MAGIC - Tests ALL major SAS conversion patterns:
# MAGIC   - ✅ PROC FORMAT (custom formats)
# MAGIC   - ✅ DATALINES (inline test data)
# MAGIC   - ✅ Macros with parameters
# MAGIC   - ✅ MERGE operations
# MAGIC   - ✅ PROC SQL joins
# MAGIC   - ✅ RETAIN (running totals)
# MAGIC   - ✅ FIRST./LAST. (BY-group processing)
# MAGIC   - ✅ Complex IF/THEN/ELSE logic
# MAGIC   - ✅ Summary reporting
# MAGIC
# MAGIC **This is THE BEST test case** - covers more features than any other example!

# COMMAND ----------

# MAGIC %md
# MAGIC ## Upload to Inbound (Landing Zone)

# COMMAND ----------

# Upload to 00_inbound (new production structure)
base_path = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/00_inbound"
subfolder = "manual_uploads"  # or "claims_mainframe" for automated feeds
upload_path = f"{base_path}/{subfolder}"

dbutils.fs.mkdirs(upload_path)
print(f"✅ Upload target: {upload_path}")
print()
print("📌 Files will be uploaded to 00_inbound/manual_uploads/")
print("👉 Next: Run 00_orchestrate_conversion_pipeline.py to validate and convert")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Upload Complete SAS Program

# COMMAND ----------

# Comprehensive claims adjudication SAS program
sas_comprehensive_claims = """/*******************************************************************
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

dbutils.fs.put(f"{upload_path}/claims_adjudication_comprehensive.sas",
               sas_comprehensive_claims,
               overwrite=True)

print(f"✅ Uploaded: claims_adjudication_comprehensive.sas")
print(f"   Size: {len(sas_comprehensive_claims)} bytes")
print(f"   Lines: ~180")
print(f"   Location: {upload_path}")
print()
print("📋 SAS Features Covered:")
print("   ✅ PROC FORMAT - custom value formats")
print("   ✅ DATALINES - inline test data")
print("   ✅ Macros - %macro, %mend, parameter substitution")
print("   ✅ MERGE - DATA step merges with IN= flags")
print("   ✅ PROC SQL - joins and aggregations")
print("   ✅ RETAIN - stateful processing (running totals)")
print("   ✅ FIRST./LAST. - BY-group processing")
print("   ✅ Complex IF/THEN/ELSE - multi-branch logic")
print("   ✅ PROC SORT - multiple sorts")
print("   ✅ PROC PRINT - reporting")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Project Config

# COMMAND ----------

config_yaml = """project_name: comprehensive_claims_adjudication
description: |
  COMPREHENSIVE SAS test case covering ALL major conversion patterns:

  Features tested:
  - PROC FORMAT (custom value formats)
  - DATALINES (inline synthetic data)
  - Macros with parameters (%macro, %mend)
  - DATA step MERGE operations with IN= flags
  - PROC SQL joins and aggregations
  - RETAIN for running totals (stateful processing)
  - FIRST./LAST. BY-group processing
  - Multi-branch IF/THEN/ELSE logic
  - PROC SORT
  - Summary reporting

  Business logic:
  - Member eligibility validation
  - Provider network status checks
  - Duplicate claim detection
  - Annual benefit limit tracking
  - Final adjudication decision tree

sas_version: 9.4
execution_order:
  - claims_adjudication_comprehensive.sas

target:
  pipeline_type: sdp
  medallion_layer: silver
  compute: serverless

libname_mapping:
  clm:
    catalog: na-dbxtraining
    schema: sas2dbx_migrate
  work:
    catalog: na-dbxtraining
    schema: temp_workspace

conversion:
  model: opus-4.8
  validate_output: true
  create_bundle: true
  preserve_comments: true
  include_original_sas: true

# Conversion difficulty by feature
expected_results:
  proc_format: HIGH_CONFIDENCE  # Deterministic mapping
  datalines: HIGH_CONFIDENCE    # Static data extraction
  macros: MEDIUM_CONFIDENCE     # Parameter substitution → Python functions
  merge: HIGH_CONFIDENCE        # MERGE → Spark join
  proc_sql: HIGH_CONFIDENCE     # SQL → Spark SQL (deterministic)
  retain: MEDIUM_CONFIDENCE     # RETAIN → window functions or cumulative sum
  first_last: MEDIUM_CONFIDENCE # BY-group → window functions
  if_then_else: HIGH_CONFIDENCE # Multi-branch → CASE WHEN

business_rules:
  - name: eligibility_check
    description: Member must be active on service date

  - name: duplicate_detection
    description: Same member + provider + date + procedure = duplicate

  - name: network_status
    description: Out-of-network claims pended for manual review

  - name: benefit_limit
    description: Annual limit check with running total by member

  - name: adjudication_decision
    description: Multi-step decision tree (eligibility → duplicate → network → limit)
"""

# NOTE: config.yaml not needed in new structure (00_inbound is simpler)
# dbutils.fs.put(f"{project_path}/config.yaml", config_yaml, overwrite=True)
# print(f"✅ Created: config.yaml")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: Create Metadata Documentation (for reference only)

# COMMAND ----------

# Document the test data structure
metadata_doc = """# Test Data Structure

## Members (5 records)
- member_id, plan_id, eff_date, term_date, dob
- Plans: PLNA01, PLNB02
- Coverage spans: 2025

## Providers (4 records)
- provider_id, npi, specialty, network_status
- Mix of in-network and out-of-network

## Benefit Plans (2 records)
- plan_id, benefit_year, annual_limit, copay, deductible
- PLNA01: $50K limit, $25 copay, $500 deductible
- PLNB02: $75K limit, $40 copay, $1000 deductible

## Claims (7 records)
- claim_id, member_id, provider_id, service_date, diag_code, proc_code, billed_amount
- Includes: duplicate claim (C90005), non-existent member (C90007), out-of-network provider (C90003)

## Diagnosis Codes
- E11: DIABETES
- I10: HYPERTENSION
- J45: ASTHMA
- M54: BACK_PAIN

## Expected Outcomes
After adjudication, claims should be:
- APPROVED: Valid, in-network, under limits
- DENIED: Not eligible, duplicate, or over limit
- PENDED: Out-of-network (manual review required)
"""

# NOTE: Optional metadata - not required in new structure
# metadata_path = f"{upload_path}/test_data_structure.md"
# dbutils.fs.put(metadata_path, metadata_doc, overwrite=True)
# print(f"✅ Created: test_data_structure.md")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("="*80)
print("📤 COMPREHENSIVE CLAIMS EXAMPLE UPLOADED!")
print("="*80)
print()
print(f"📁 Location: {upload_path}")
print()
print("📄 SAS Program:")
print("   claims_adjudication_comprehensive.sas (~180 lines)")
print()
print("🎯 This is THE BEST test case!")
print()
print("✅ Features Covered (10 major SAS patterns):")
print("   1. PROC FORMAT - custom formats")
print("   2. DATALINES - inline test data")
print("   3. Macros - parameter substitution")
print("   4. MERGE - DATA step merges with IN=")
print("   5. PROC SQL - joins and aggregations")
print("   6. RETAIN - running totals")
print("   7. FIRST./LAST. - BY-group processing")
print("   8. Complex IF/THEN/ELSE - multi-branch")
print("   9. PROC SORT - multiple sorts")
print("   10. PROC PRINT - summary reports")
print()
print("💡 Why This Example is Superior:")
print("   ✅ Tests MORE features than any other example")
print("   ✅ Includes macros (very common in production SAS)")
print("   ✅ Has embedded test data (DATALINES)")
print("   ✅ Tests RETAIN and FIRST./LAST. (tricky conversions)")
print("   ✅ Complete end-to-end workflow")
print()
print("🎯 Expected Conversion Challenges:")
print("   - MEDIUM: Macros → Python functions")
print("   - MEDIUM: RETAIN → Window functions or state management")
print("   - MEDIUM: FIRST./LAST. → Window functions with partitioning")
print("   - HIGH: Everything else (deterministic conversion)")
print()
print("="*80)
print()
print("📋 Next Steps:")
print("   Option 1 (Recommended): Run 00_orchestrate_conversion_pipeline.py")
print("   Option 2 (Direct):      Run 03d_convert_sas.py")
print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Comparison with Other Examples

# COMMAND ----------

print("="*80)
print("📊 EXAMPLE COMPARISON")
print("="*80)
print()

examples = [
    {
        "name": "Simple Examples (02_upload_sample_sas.py)",
        "files": 3,
        "lines": "~15-40 each",
        "features": ["PROC SQL", "PROC FORMAT", "DATA step", "SELECT/WHEN"],
        "complexity": "LOW-MEDIUM",
        "purpose": "Quick syntax validation"
    },
    {
        "name": "Healthcare Examples (02a_upload_healthcare_example.py)",
        "files": 2,
        "lines": "~250, ~140",
        "features": ["HCC risk adjustment", "Validation", "Business rules", "Multiple joins"],
        "complexity": "HIGH",
        "purpose": "Real production patterns"
    },
    {
        "name": "Comprehensive Claims (02b - THIS ONE)",
        "files": 1,
        "lines": "~180",
        "features": ["Macros", "MERGE", "RETAIN", "FIRST./LAST.", "DATALINES", "Complete workflow"],
        "complexity": "HIGH",
        "purpose": "⭐ BEST - Tests ALL SAS patterns"
    }
]

for i, ex in enumerate(examples, 1):
    print(f"{i}. {ex['name']}")
    print(f"   Files: {ex['files']}")
    print(f"   Lines: {ex['lines']}")
    print(f"   Features: {', '.join(ex['features'][:3])}")
    if len(ex['features']) > 3:
        print(f"             {', '.join(ex['features'][3:])}")
    print(f"   Complexity: {ex['complexity']}")
    print(f"   Purpose: {ex['purpose']}")
    print()

print("="*80)
print()
print("🏆 RECOMMENDATION: Run THIS example (02b) first!")
print("   It's the most comprehensive test of sas2databricks conversion.")
print()
print("="*80)
