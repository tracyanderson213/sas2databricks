# Pipeline Testing Guide

## Overview

Two pipelines for different testing purposes:

### 1️⃣ **Template Pipeline** (Configuration Validation)
- **Purpose:** Validate pipeline configuration and parameter passing
- **Pipeline:** `sas_dbx_TEMPLATE_tanderson_pipeline`
- **File:** `transformations/current_transformation.py` (simple placeholder)
- **What it does:** Creates a small test table with configuration values
- **Use case:** Verify widgets, schemas, and catalog settings work correctly

### 2️⃣ **Test Pipeline** (End-to-End Converter Validation)
- **Purpose:** Test complete converter output with actual transformation logic
- **Pipeline:** `sas_dbx_TEST_tanderson_pipeline` (to be created)
- **File:** `transformed_claims_adjudication_FIXED.py` (converter output + manual fixes)
- **What it does:** Full claims adjudication transformation (Bronze → Silver → Gold)
- **Use case:** Validate end-to-end SAS→Databricks conversion process

---

## Setup Instructions

### Step 1: Template Pipeline (Already Done ✅)

The template pipeline has been updated with a simple placeholder file that:
- Prints configuration parameters
- Creates one small test table
- Validates pipeline syntax

**To test:**
```bash
# Run in Databricks UI:
Workflows → Delta Live Tables → sas_dbx_TEMPLATE_tanderson_pipeline → Start
```

**Expected output:**
- Creates: `na-dbxtraining.sas_tanderson_bronze.pipeline_config_test`
- Contains: Configuration key-value pairs (CATALOG, SCHEMA_BRONZE, etc.)

---

### Step 2: Create Test Pipeline

Run the helper script to create a separate test pipeline:

```bash
python create_test_pipeline.py
```

**This will:**
1. Upload `transformed_claims_adjudication_FIXED.py` to workspace
2. Create new pipeline: `sas_dbx_TEST_tanderson_pipeline`
3. Configure it to use the fixed transformation file

**To test:**
```bash
# Run in Databricks UI:
Workflows → Delta Live Tables → sas_dbx_TEST_tanderson_pipeline → Start
```

**Expected output:**
- **Bronze:** 4 tables (work_members, work_providers, work_benefit_plans, work_claims_in)
- **Silver:** 6 views (work_claims_elig, work_claims_elig2, work_claims_network, work_claims_dupflag, work_claims_benefit, work_claims_running)
- **Gold:** 2 tables (clm_claims_adjudicated, result)

---

## Differences Between Pipelines

| Feature | Template Pipeline | Test Pipeline |
|---------|------------------|---------------|
| **Purpose** | Config validation | Full transformation test |
| **File** | Simple placeholder | Converter output (fixed) |
| **Tables created** | 1 (config test) | 12 (full pipeline) |
| **Runtime** | ~1 min | ~3-5 min |
| **Use for** | Pre-flight checks | Conversion validation |

---

## Known Issues Fixed in Test Pipeline

The converter output required 4 manual fixes:

1. ✅ **Empty Placeholder Removed**
   - `clm_claims_adjudicated_report` (PROC PRINT output, not a table)

2. ✅ **Missing Column Added**
   - `limit_exceeded` column in `work_claims_running`

3. ✅ **Duplicate Columns Fixed**
   - Nested IF/THEN/ELSE converted to proper CASE statements

4. ✅ **Missing ELSE Clause**
   - `dup_flag` CASE now has `ELSE 'N'`

---

## Future Workflow

Once converter is fully fixed:

1. **Upload SAS file** → `/Volumes/.../staging/`
2. **Run converter job** → Generates `transformed_*.py`
3. **Clone template pipeline** → Create new pipeline for the transformation
4. **Update cloned pipeline** → Point to generated file
5. **Run and validate** → Test the transformation

**No manual fixes needed!** (Once we add the 4 fixes to the converter)

---

## Schema Isolation

Both pipelines use the same schemas:
- `na-dbxtraining.sas_tanderson_bronze`
- `na-dbxtraining.sas_tanderson_silver`
- `na-dbxtraining.sas_tanderson_gold`

**⚠️ Important:** Don't run both pipelines simultaneously!

The template pipeline only creates 1 test table, so it won't interfere with the test pipeline's full transformation.

---

## Troubleshooting

### Template Pipeline Issues

If the template fails, check:
- Schemas exist and you have write permissions
- Catalog `na-dbxtraining` is accessible
- Pipeline configuration is correct

### Test Pipeline Issues

If the test fails, check:
- All manual fixes were applied (run `apply_fixes.py` again)
- Bronze tables are created first
- Columns flow through: `elig_flag`, `dup_flag`, `network_status`, `limit_exceeded`

---

## Files Reference

```
transformations/
├── current_transformation.py          # Template placeholder (simple)
└── transformed_claims_adjudication_FIXED.py  # Converter output (fixed)

Scripts:
├── apply_fixes.py                     # Apply 4 manual fixes
├── create_test_pipeline.py            # Create test pipeline
└── copy_transformed_file.py           # Download converter output
```
