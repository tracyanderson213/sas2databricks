# Databricks notebook source
# MAGIC %md
# MAGIC # 02a - Upload Healthcare Claims Example (Complex)
# MAGIC
# MAGIC **Purpose:** Upload realistic, complex healthcare SAS code for testing
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC
# MAGIC **What this does:**
# MAGIC - Uploads complex claims adjudication SAS program
# MAGIC - Includes business rules, edits, and risk adjustments
# MAGIC - ~200 lines of SAS with realistic healthcare logic
# MAGIC
# MAGIC **Use case:** Claims processing with RAF (Risk Adjustment Factor) scoring

# COMMAND ----------

# MAGIC %md
# MAGIC ## Complex Example: Claims Adjudication with Risk Adjustment

# COMMAND ----------

# Create project folder
base_path = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input"
project_name = "hc_claims_adjudication"
project_path = f"{base_path}/{project_name}"

dbutils.fs.mkdirs(f"{project_path}/sas")
dbutils.fs.mkdirs(f"{project_path}/metadata")
print(f"✅ Created: {project_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## SAS Program: claims_adjudication.sas

# COMMAND ----------

# Complex healthcare claims adjudication SAS code
sas_claims_adjudication = """/*******************************************************************************
* Program: claims_adjudication.sas
* Purpose: Process healthcare claims with business edits and risk adjustment
* Author:  Claims Analytics Team
* Date:    2024-01-15
*
* Business Rules:
*   - Validate claim completeness (member, provider, diagnosis codes)
*   - Apply CMS HCC risk adjustment model
*   - Flag claims for medical review based on thresholds
*   - Calculate allowed amounts using fee schedules
*   - Identify duplicate claims within 7-day window
*
* Input:  claims.raw_837 (EDI 837 claims)
*         refdata.hcc_weights (CMS-HCC V28 weights)
*         refdata.fee_schedule (CPT-4 allowed amounts by region)
*         refdata.member_eligibility (active members)
*
* Output: claims.adjudicated_claims (processed claims ready for payment)
*         claims.medical_review_queue (claims flagged for review)
*         claims.claims_audit_log (audit trail)
*******************************************************************************/

options mprint mlogic symbolgen;

/*==============================================================================
  STEP 1: Load and validate raw claims data
==============================================================================*/

libname claims '/sas/data/claims';
libname refdata '/sas/data/reference';

/* Load raw EDI 837 claims */
data work.raw_claims;
    set claims.raw_837;

    /* Validate required fields */
    length edit_reason $200;
    array required{*} member_id provider_npi claim_date diag_code1 procedure_code;

    edit_flag = 0;
    edit_reason = '';

    /* Check for missing critical fields */
    do i = 1 to dim(required);
        if missing(required{i}) then do;
            edit_flag = 1;
            edit_reason = catx('; ', edit_reason,
                              cats(vname(required{i}), ' is missing'));
        end;
    end;

    /* Validate date range */
    if not missing(claim_date) then do;
        if claim_date < '01JAN2020'd or claim_date > today() then do;
            edit_flag = 1;
            edit_reason = catx('; ', edit_reason, 'Invalid claim_date');
        end;
    end;

    /* Validate billed amount */
    if billed_amount <= 0 or billed_amount > 1000000 then do;
        edit_flag = 1;
        edit_reason = catx('; ', edit_reason, 'Invalid billed_amount');
    end;

    drop i;
run;

/* Summary stats on validation */
proc sql;
    create table work.validation_summary as
    select
        count(*) as total_claims,
        sum(case when edit_flag = 0 then 1 else 0 end) as valid_claims,
        sum(case when edit_flag = 1 then 1 else 0 end) as failed_edits,
        calculated failed_edits / calculated total_claims as fail_rate format=percent8.2
    from work.raw_claims;
quit;

/*==============================================================================
  STEP 2: Enrich with member eligibility and risk scores
==============================================================================*/

/* Join to active member eligibility */
proc sql;
    create table work.eligible_claims as
    select
        a.*,
        b.plan_id,
        b.coverage_start_date,
        b.coverage_end_date,
        b.benefit_tier,
        case
            when a.claim_date between b.coverage_start_date and b.coverage_end_date
            then 1
            else 0
        end as eligibility_flag,
        case
            when calculated eligibility_flag = 0
            then 'Member not eligible on date of service'
            else a.edit_reason
        end as edit_reason_updated
    from work.raw_claims a
    left join refdata.member_eligibility b
        on a.member_id = b.member_id
    where a.edit_flag = 0  /* Only process valid claims */
    ;
quit;

/*==============================================================================
  STEP 3: Calculate HCC risk adjustment factor (RAF)
==============================================================================*/

/* Extract up to 5 diagnosis codes per claim */
data work.claim_diagnoses;
    set work.eligible_claims;

    array diag_codes{5} $ diag_code1-diag_code5;

    do i = 1 to 5;
        if not missing(diag_codes{i}) then do;
            diagnosis_code = diag_codes{i};
            output;
        end;
    end;

    keep claim_id member_id diagnosis_code plan_id claim_date;
run;

/* Map ICD-10 diagnosis codes to HCC categories */
proc sql;
    create table work.claim_hccs as
    select distinct
        a.claim_id,
        a.member_id,
        a.diagnosis_code,
        b.hcc_category,
        b.hcc_description,
        b.coefficient as hcc_weight
    from work.claim_diagnoses a
    inner join refdata.hcc_weights b
        on substr(a.diagnosis_code, 1, 5) = b.icd10_code  /* Match first 5 chars */
    where b.model_version = 'V28'  /* CMS-HCC V28 */
    ;
quit;

/* Calculate member-level RAF score */
proc sql;
    create table work.member_raf as
    select
        member_id,
        count(distinct hcc_category) as hcc_count,
        sum(hcc_weight) as raw_raf_score,
        /* Apply demographic adjustments (simplified) */
        calculated raw_raf_score * 1.0 as adjusted_raf_score
    from work.claim_hccs
    group by member_id
    having calculated hcc_count > 0
    ;
quit;

/*==============================================================================
  STEP 4: Apply fee schedule and calculate allowed amounts
==============================================================================*/

proc sql;
    create table work.claims_with_allowed as
    select
        a.*,
        b.adjusted_raf_score,
        c.allowed_amount as fee_schedule_allowed,
        /* Business rule: Use lesser of billed or fee schedule */
        case
            when a.billed_amount < c.allowed_amount
            then a.billed_amount
            else c.allowed_amount
        end as calculated_allowed_amount,
        /* Flag high-dollar claims for review */
        case
            when calculated calculated_allowed_amount > 50000
            then 1
            else 0
        end as high_dollar_flag
    from work.eligible_claims a
    left join work.member_raf b
        on a.member_id = b.member_id
    left join refdata.fee_schedule c
        on a.procedure_code = c.cpt_code
       and a.provider_region = c.region_code
    where a.eligibility_flag = 1
    ;
quit;

/*==============================================================================
  STEP 5: Duplicate claim detection (7-day window)
==============================================================================*/

proc sql;
    create table work.duplicate_check as
    select
        a.claim_id,
        a.member_id,
        a.provider_npi,
        a.procedure_code,
        a.claim_date,
        a.calculated_allowed_amount,
        b.claim_id as prior_claim_id,
        b.claim_date as prior_claim_date,
        case
            when not missing(b.claim_id)
            then 1
            else 0
        end as duplicate_flag
    from work.claims_with_allowed a
    left join work.claims_with_allowed b
        on a.member_id = b.member_id
       and a.provider_npi = b.provider_npi
       and a.procedure_code = b.procedure_code
       and a.claim_id ne b.claim_id
       and abs(a.claim_date - b.claim_date) <= 7  /* Within 7 days */
       and b.claim_date < a.claim_date  /* Prior claim only */
    order by a.claim_id
    ;
quit;

/* Keep only unique claims (first occurrence) */
data work.unique_claims;
    set work.duplicate_check;
    by claim_id;
    if first.claim_id;  /* Keep first record per claim */
run;

/*==============================================================================
  STEP 6: Final adjudication and routing
==============================================================================*/

data claims.adjudicated_claims
     claims.medical_review_queue
     claims.claims_audit_log;

    set work.unique_claims;

    length adjudication_status $20 final_edit_reason $500;

    /* Initialize */
    adjudication_status = 'APPROVED';
    final_edit_reason = '';

    /* Business rule: Route to medical review if needed */
    if high_dollar_flag = 1 then do;
        adjudication_status = 'PENDING_REVIEW';
        final_edit_reason = catx('; ', final_edit_reason,
                                 'High dollar claim (>$50K)');
    end;

    if duplicate_flag = 1 then do;
        adjudication_status = 'DUPLICATE';
        final_edit_reason = catx('; ', final_edit_reason,
                                 cats('Duplicate of claim ', prior_claim_id));
    end;

    if missing(fee_schedule_allowed) then do;
        adjudication_status = 'PENDING_REVIEW';
        final_edit_reason = catx('; ', final_edit_reason,
                                 'Procedure code not in fee schedule');
    end;

    /* Calculate payment amount */
    if adjudication_status = 'APPROVED' then
        payment_amount = calculated_allowed_amount;
    else
        payment_amount = 0;

    /* Route to appropriate output */
    select (adjudication_status);
        when ('APPROVED')
            output claims.adjudicated_claims;
        when ('PENDING_REVIEW')
            output claims.medical_review_queue;
        when ('DUPLICATE')
            output claims.claims_audit_log;
        otherwise
            output claims.claims_audit_log;
    end;

    /* Audit trail for all */
    output claims.claims_audit_log;
run;

/*==============================================================================
  STEP 7: Summary reporting
==============================================================================*/

proc sql;
    title 'Claims Adjudication Summary';
    select
        adjudication_status,
        count(*) as claim_count,
        sum(billed_amount) as total_billed format=dollar18.2,
        sum(calculated_allowed_amount) as total_allowed format=dollar18.2,
        sum(payment_amount) as total_payment format=dollar18.2,
        (calculated total_payment / calculated total_billed) as payment_rate format=percent8.2
    from claims.adjudicated_claims
    group by adjudication_status
    union all
    select
        'TOTAL' as adjudication_status,
        count(*),
        sum(billed_amount),
        sum(calculated_allowed_amount),
        sum(payment_amount),
        (calculated total_payment / calculated total_billed)
    from claims.adjudicated_claims
    ;
quit;

/* Log completion */
data _null_;
    file log;
    put "========================================";
    put "Claims Adjudication Complete";
    put "Timestamp: " datetime19.;
    put "========================================";
run;
"""

dbutils.fs.put(f"{project_path}/sas/claims_adjudication.sas", sas_claims_adjudication, overwrite=True)
print(f"✅ Uploaded: claims_adjudication.sas ({len(sas_claims_adjudication)} bytes)")
print(f"   Lines of code: ~250")
print(f"   Complexity: HIGH")
print(f"   Business rules: 7 steps with validation, risk adjustment, duplicate detection")

# COMMAND ----------

# MAGIC %md
# MAGIC ## SAS Program: eligibility_validation.sas

# COMMAND ----------

# Second complex healthcare example - eligibility validation
sas_eligibility = """/*******************************************************************************
* Program: eligibility_validation.sas
* Purpose: Validate member eligibility and coverage for prior authorization requests
*
* Business Rules:
*   - Check active coverage on service date
*   - Validate benefit limits (visits, dollar caps)
*   - Check for exclusions and limitations
*   - Apply coordination of benefits (COB) rules
*******************************************************************************/

libname members '/sas/data/members';
libname benefits '/sas/data/benefits';

/* Step 1: Load prior authorization requests */
data work.pa_requests;
    set members.prior_auth_requests;
    where request_status = 'PENDING';

    /* Parse service dates */
    length coverage_period $20;
    service_month = month(service_date);
    service_year = year(service_date);
    coverage_period = cats(service_year, '-', put(service_month, z2.));
run;

/* Step 2: Check member eligibility on service date */
proc sql;
    create table work.pa_with_eligibility as
    select
        a.*,
        b.plan_id,
        b.coverage_type,
        b.effective_date,
        b.termination_date,
        case
            when a.service_date between b.effective_date and coalesce(b.termination_date, '31DEC9999'd)
            then 'ELIGIBLE'
            when a.service_date < b.effective_date
            then 'NOT_YET_EFFECTIVE'
            when a.service_date > b.termination_date
            then 'COVERAGE_TERMINATED'
            else 'NOT_FOUND'
        end as eligibility_status
    from work.pa_requests a
    left join members.eligibility b
        on a.member_id = b.member_id
    ;
quit;

/* Step 3: Check benefit limits */
proc sql;
    create table work.pa_benefit_check as
    select
        a.*,
        b.service_category,
        b.visits_allowed_per_year,
        b.dollar_limit_per_year,
        c.visits_used_ytd,
        c.dollars_used_ytd,
        case
            when c.visits_used_ytd >= b.visits_allowed_per_year
            then 'VISIT_LIMIT_EXCEEDED'
            when c.dollars_used_ytd >= b.dollar_limit_per_year
            then 'DOLLAR_LIMIT_EXCEEDED'
            else 'WITHIN_LIMITS'
        end as benefit_limit_status
    from work.pa_with_eligibility a
    inner join benefits.benefit_limits b
        on a.plan_id = b.plan_id
       and a.service_code = b.service_code
    left join benefits.utilization_ytd c
        on a.member_id = c.member_id
       and a.coverage_period = c.coverage_period
    where a.eligibility_status = 'ELIGIBLE'
    ;
quit;

/* Step 4: Final determination */
data members.pa_decisions
     members.pa_denials;

    set work.pa_benefit_check;

    length decision $20 denial_reason $200;

    /* Determine approval/denial */
    if eligibility_status = 'ELIGIBLE' and benefit_limit_status = 'WITHIN_LIMITS' then do;
        decision = 'APPROVED';
        denial_reason = '';
        output members.pa_decisions;
    end;
    else do;
        decision = 'DENIED';
        if eligibility_status ne 'ELIGIBLE' then
            denial_reason = eligibility_status;
        else
            denial_reason = benefit_limit_status;
        output members.pa_denials;
    end;

    /* Audit trail */
    decision_date = today();
    decision_timestamp = datetime();
run;

proc sql;
    title 'Prior Authorization Summary';
    select
        decision,
        count(*) as request_count,
        sum(estimated_cost) as total_cost format=dollar15.2
    from members.pa_decisions
    group by decision;
quit;
"""

dbutils.fs.put(f"{project_path}/sas/eligibility_validation.sas", sas_eligibility, overwrite=True)
print(f"✅ Uploaded: eligibility_validation.sas ({len(sas_eligibility)} bytes)")
print(f"   Lines of code: ~140")
print(f"   Complexity: MEDIUM-HIGH")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Config File

# COMMAND ----------

config_yaml = """project_name: hc_claims_adjudication
description: |
  Complex healthcare claims adjudication pipeline with:
  - Claims validation (completeness, date ranges, amounts)
  - Member eligibility verification
  - CMS-HCC V28 risk adjustment (RAF scoring)
  - Fee schedule pricing
  - Duplicate claim detection (7-day window)
  - Medical review routing
  - Prior authorization eligibility checks

sas_version: 9.4
execution_order:
  - claims_adjudication.sas
  - eligibility_validation.sas

dependencies:
  external_tables:
    - claims.raw_837
    - refdata.hcc_weights
    - refdata.fee_schedule
    - refdata.member_eligibility
    - members.prior_auth_requests
    - benefits.benefit_limits

target:
  pipeline_type: sdp
  medallion_layer: silver  # Business logic transformation
  compute: serverless
  schedule: "0 3 * * *"  # Daily at 3am

libname_mapping:
  claims:
    catalog: na-dbxtraining
    schema: healthcare_claims
  refdata:
    catalog: na-dbxtraining
    schema: reference_data
  members:
    catalog: na-dbxtraining
    schema: member_data
  benefits:
    catalog: na-dbxtraining
    schema: benefits

conversion:
  model: opus-4.8
  validate_output: true
  create_bundle: true
  preserve_comments: true
  include_original_sas: true  # ← Embed original SAS code in output

business_rules:
  - name: high_dollar_threshold
    value: 50000
    description: Claims >$50K route to medical review

  - name: duplicate_window_days
    value: 7
    description: Flag claims within 7 days as duplicates

  - name: hcc_model_version
    value: V28
    description: CMS-HCC risk adjustment model version
"""

dbutils.fs.put(f"{project_path}/config.yaml", config_yaml, overwrite=True)
print(f"✅ Created: config.yaml")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Metadata Files

# COMMAND ----------

# Create sample metadata
metadata_schemas = """table_name,column_name,data_type,length,format,label
raw_837,claim_id,char,20,,Claim Identifier
raw_837,member_id,char,15,,Member ID
raw_837,provider_npi,char,10,,Provider NPI
raw_837,claim_date,num,8,DATE9.,Claim Service Date
raw_837,diag_code1,char,7,,Primary Diagnosis (ICD-10)
raw_837,diag_code2,char,7,,Secondary Diagnosis
raw_837,procedure_code,char,5,,CPT-4 Procedure Code
raw_837,billed_amount,num,8,DOLLAR12.2,Billed Amount
"""

dbutils.fs.put(f"{project_path}/metadata/table_schemas.csv", metadata_schemas, overwrite=True)

# HCC mapping reference
hcc_reference = """hcc_category,hcc_description,coefficient
HCC001,HIV/AIDS,0.345
HCC002,Septicemia/Shock,0.512
HCC008,Metastatic Cancer,2.616
HCC009,Lung Other Severe Cancers,1.395
HCC010,Lymphoma Other Cancers,0.897
HCC011,Colorectal Breast Prostate Cancers,0.309
HCC017,Diabetes with Acute Complications,0.318
HCC018,Diabetes with Chronic Complications,0.318
HCC019,Diabetes without Complication,0.104
"""

dbutils.fs.put(f"{project_path}/metadata/hcc_reference.csv", hcc_reference, overwrite=True)

print(f"✅ Created metadata files:")
print(f"   - table_schemas.csv")
print(f"   - hcc_reference.csv")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("="*80)
print("📤 COMPLEX HEALTHCARE EXAMPLE UPLOADED!")
print("="*80)
print()
print("📁 Project: hc_claims_adjudication/")
print()
print("📄 SAS Programs:")
print("   1. claims_adjudication.sas (~250 lines)")
print("      - Claims validation")
print("      - HCC risk adjustment (RAF scoring)")
print("      - Fee schedule pricing")
print("      - Duplicate detection")
print("      - Medical review routing")
print()
print("   2. eligibility_validation.sas (~140 lines)")
print("      - Prior authorization requests")
print("      - Member eligibility checks")
print("      - Benefit limit validation")
print("      - Approval/denial workflow")
print()
print("📊 Complexity:")
print("   - Business rules: 10+ different rules")
print("   - Data sources: 7 input tables")
print("   - Outputs: 3 different tables")
print("   - Healthcare domain: Claims, eligibility, risk adjustment")
print()
print("🎯 Expected Conversion:")
print("   - Target: Spark Declarative Pipelines (SDP)")
print("   - Confidence: MEDIUM-HIGH (complex business logic)")
print("   - Review required: Yes (validate RAF calculations)")
print()
print("="*80)
print()
print("📋 Next: Run notebook 03_test_conversion.py to convert these files")
print()
print("="*80)
