# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Upload SAS Files to Inbound
# MAGIC
# MAGIC **Purpose:** Upload SAS files to the inbound landing zone
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first to create volume structure
# MAGIC
# MAGIC **What this does:**
# MAGIC - Uploads SAS files to `00_inbound/manual_uploads/`
# MAGIC - Files will be validated and converted by orchestration pipeline
# MAGIC
# MAGIC **Next step:** Run `00_orchestrate_conversion_pipeline.py` to process files

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Upload destination
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"
VOLUME = "sas_migration"

# Upload to inbound landing zone
inbound_base = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/00_inbound"
upload_folder = "manual_uploads"  # or "claims_mainframe" for automated feeds
upload_path = f"{inbound_base}/{upload_folder}"

print("="*80)
print("📤 SAS FILE UPLOAD")
print("="*80)
print(f"📁 Upload to: {upload_path}")
print("="*80)
print()

# Ensure upload path exists
dbutils.fs.mkdirs(upload_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 1: Simple SELECT Query

# COMMAND ----------

simple_select = """/* Simple SELECT from SASHELP.CLASS */
proc sql;
    select Name, Age, Height, Weight
    from sashelp.class
    where Age >= 14
    order by Age desc;
quit;
"""

dbutils.fs.put(f"{upload_path}/simple_select.sas", simple_select, overwrite=True)
print("✅ Uploaded: simple_select.sas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 2: PROC FORMAT with DATALINES

# COMMAND ----------

format_example = """/* Car origin classification with formatting */
proc format;
    value $origin
        'USA'  = 'DOMESTIC'
        'Japan' = 'IMPORT'
        'Europe' = 'IMPORT'
        other = 'UNKNOWN';
run;

data work.cars_classified;
    set sashelp.cars;
    origin_category = put(origin, $origin.);
run;

proc sql;
    select origin_category, count(*) as car_count, avg(msrp) as avg_price
    from work.cars_classified
    group by origin_category;
quit;
"""

dbutils.fs.put(f"{upload_path}/car_classification.sas", format_example, overwrite=True)
print("✅ Uploaded: car_classification.sas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example 3: Claims Adjudication (Comprehensive)

# COMMAND ----------

claims_comprehensive = """/*******************************************************************
  CLAIMS ADJUDICATION - COMPREHENSIVE EXAMPLE
  Purpose: Test all major SAS features for conversion
  Covers:  PROC FORMAT, DATALINES, macros, MERGE, PROC SQL,
           RETAIN, FIRST./LAST., complex IF/THEN/ELSE
********************************************************************/

options mprint mlogic symbolgen;

/* Custom format */
proc format;
    value $diagcat
        'E11'  = 'DIABETES'
        'I10'  = 'HYPERTENSION'
        'J45'  = 'ASTHMA'
        'M54'  = 'BACK_PAIN'
        other  = 'OTHER';
run;

/* Member eligibility */
data work.members;
    length member_id $10 plan_id $6;
    input member_id $ plan_id $ eff_date :mmddyy10. term_date :mmddyy10.;
    format eff_date term_date mmddyy10.;
    datalines;
M00001 PLNA01 01/01/2025 12/31/2025
M00002 PLNA01 01/01/2025 06/30/2025
M00003 PLNB02 03/01/2025 12/31/2025
M00004 PLNB02 01/01/2025 12/31/2025
;
run;

/* Providers */
data work.providers;
    length provider_id $10 specialty $20 network_status $12;
    input provider_id $ specialty $ network_status $;
    datalines;
P1001 CARDIOLOGY  INNETWORK
P1002 PRIMARYCARE INNETWORK
P1003 ORTHOPEDIC  OUTOFNETWORK
P1004 ENDOCRINOLOGY INNETWORK
;
run;

/* Claims */
data work.claims_in;
    length claim_id $10 member_id $10 provider_id $10 diag_code $5;
    input claim_id $ member_id $ provider_id $ service_date :mmddyy10. diag_code $ billed_amount;
    format service_date mmddyy10.;
    datalines;
C90001 M00001 P1001 03/15/2025 I10 120.00
C90002 M00002 P1002 07/10/2025 E11 150.00
C90003 M00003 P1003 04/02/2025 M54 200.00
C90004 M00004 P1004 05/20/2025 E11 180.00
;
run;

/* Macro for eligibility check */
%macro check_elig(dsin=, dsout=);
    data &dsout;
        set &dsin;
        if eff_date <= service_date <= term_date then elig_flag = 'Y';
        else elig_flag = 'N';
    run;
%mend;

/* Merge claims with members */
proc sort data=work.claims_in; by member_id; run;
proc sort data=work.members; by member_id; run;

data work.claims_elig;
    merge work.claims_in (in=inclaim)
          work.members (in=inmember);
    by member_id;
    if inclaim;
    if inmember = 0 then elig_flag = 'N';
run;

%check_elig(dsin=work.claims_elig, dsout=work.claims_elig2);

/* Join with providers */
proc sql;
    create table work.claims_network as
    select a.*, b.network_status, b.specialty
    from work.claims_elig2 as a
    left join work.providers as b
        on a.provider_id = b.provider_id;
quit;

/* Adjudication logic */
data work.claims_adjudicated;
    set work.claims_network;
    length adj_status $8 deny_reason $40 diag_category $12;

    diag_category = put(diag_code, $diagcat.);

    if elig_flag = 'N' then do;
        adj_status = 'DENIED';
        deny_reason = 'NOT ELIGIBLE';
    end;
    else if network_status = 'OUTOFNETWORK' then do;
        adj_status = 'PENDED';
        deny_reason = 'OUT OF NETWORK';
    end;
    else do;
        adj_status = 'APPROVED';
        deny_reason = '';
        paid_amount = billed_amount - 25;  /* $25 copay */
    end;
run;

/* Summary report */
proc sql;
    select adj_status, count(*) as claim_count, sum(billed_amount) as total_billed
    from work.claims_adjudicated
    group by adj_status;
quit;
"""

dbutils.fs.put(f"{upload_path}/claims_adjudication_comprehensive.sas", claims_comprehensive, overwrite=True)
print("✅ Uploaded: claims_adjudication_comprehensive.sas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("="*80)
print("📤 UPLOAD COMPLETE")
print("="*80)
print()
print(f"📁 Location: {upload_path}")
print()
print("📄 Files uploaded:")

try:
    files = dbutils.fs.ls(upload_path)
    sas_files = [f for f in files if f.name.endswith('.sas')]

    for f in sas_files:
        size_kb = f.size / 1024
        print(f"   ✅ {f.name:50} ({size_kb:>7.1f} KB)")

    print()
    print(f"Total: {len(sas_files)} SAS files")

except Exception as e:
    print(f"⚠️  Error listing files: {e}")

print()
print("="*80)
print("📋 NEXT STEPS")
print("="*80)
print()
print("Option 1 (Recommended):")
print("   Run: 00_orchestrate_conversion_pipeline.py")
print("   → Full pipeline: validate → convert → archive → manifest")
print()
print("Option 2 (Direct conversion):")
print("   Run: 03d_convert_sas.py")
print("   → Direct conversion only")
print()
print("="*80)
