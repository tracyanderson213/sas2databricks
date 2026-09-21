# Quick Start Guide

**Get your SAS to Databricks migration running in 10 minutes.**

This guide walks through first-time deployment and your first SAS conversion.

---

## Prerequisites

✅ Databricks workspace access  
✅ Python 3.10+  
✅ Databricks CLI installed (`pip install databricks-cli`)  
✅ Valid `.databrickscfg` file (OAuth credentials pre-configured)  

---

## Step 1: Verify Connection

Test that authentication works and the workspace is accessible.

```bash
cd /path/to/sas_dbx_migration
python scripts/setup/test_connection.py
```

**Expected output:**
```
================================================================================
🔌 Testing Databricks Connection
================================================================================

1️⃣  Authenticating...
2️⃣  Testing workspace access...
   ✅ Authenticated as: tracy.anderson@3cloudsolutions.com
   ✅ Active: True
3️⃣  Testing Unity Catalog access...
   ✅ Visible catalogs: 3
   ✅ Target catalog 'na-dbxtraining' is accessible
4️⃣  Testing SQL Warehouse access...
   ✅ Target warehouse '2f51df324d05e45d' is accessible

================================================================================
✅ CONNECTION TEST PASSED
================================================================================
```

**If this fails:**
- Verify `.databrickscfg` exists and contains valid OAuth token
- Check `DATABRICKS_CONFIG_FILE` environment variable is set
- Contact your Databricks admin for service principal access

---

## Step 2: Deploy the Bundle

Deploy the DAB bundle to create schemas, volumes, and jobs.

```bash
databricks bundle deploy -t dev --var developer_id=yourname
```

**Replace `yourname` with your identifier** (e.g., `tanderson`, `jsmith`).

**What this creates:**

| Resource | Name | Purpose |
|----------|------|---------|
| Schema | `sas_yourname_bronze` | Raw data layer |
| Schema | `sas_yourname_silver` | Transformation layer |
| Schema | `sas_yourname_gold` | Analytics layer |
| Schema | `sas2dbx_migrate` | Config/metadata (shared) |
| Volume | `sas_migration` | SAS files + conversion logs |
| Job | `sas_code_translator_yourname` | Converter notebook |

**Expected output:**
```
Deploying bundle...
Creating schemas...
Creating volumes...
Creating jobs...
✅ Deployment complete!

Workspace path:
/Workspace/Users/57755c23-5f4c-45ac-b2a2-118523d0c1b5/.bundle/sas_dbx_migration/dev
```

---

## Step 3: Add Your SAS Files

Place SAS programs in the `specifications/` directory.

### Option A: Copy Local Files

```bash
cp /path/to/your_program.sas specifications/
```

### Option B: Upload to Volume (if remote)

```bash
# Via Databricks CLI
databricks fs cp your_program.sas \
  dbfs:/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input/

# Then sync to specifications/
# (converter can read from Volume paths)
```

### Example: Sample SAS File

Create `specifications/sample_claims.sas`:

```sas
/* Sample Claims Processing */

data work.claims_raw;
    set mylib.raw_claims;
    where claim_date >= '01JAN2024'd;
run;

proc sql;
    create table work.claims_summary as
    select 
        region,
        count(*) as claim_count,
        sum(claim_amount) as total_amount
    from work.claims_raw
    group by region;
quit;
```

---

## Step 4: Run the Converter

Execute the code translator job to convert SAS → Python.

```bash
databricks bundle run sas_dbx_code_translator -t dev
```

**What happens:**
1. Reads all `.sas` files from `specifications/`
2. Converts each to Spark Declarative Pipeline Python
3. Applies V7 bug fixes (INT/DOUBLE, DATE, qualified names, etc.)
4. Detects Bronze/Silver/Gold layers
5. Generates pipeline YAML files
6. Writes output to `transformations/`

**Expected output (in Databricks job logs):**
```
================================================================================
📄 Converting SAS Files to Databricks Pipelines
================================================================================

Found 1 file(s) to convert:
  - sample_claims.sas

Converting: sample_claims.sas
📄 Input:  sample_claims.sas
📄 Output: converted_sample_claims.py
📋 Pipeline YAML: pipeline_sampleclaims.yml
✨ Enhanced with:
   - Intelligent layer detection (Bronze/Silver/Gold)
   - Three schema variables
   - View optimization for intermediate tables
   - Bronze metadata helper
   - ✅ ALL 5 BUG FIXES APPLIED

================================================================================
✅ INTELLIGENT CONVERSION COMPLETE (WITH BUG FIXES)!
================================================================================

📊 CONVERSION SUMMARY
Successful: 1
Failed: 0
```

---

## Step 5: Review Converted Files

Check what was generated.

```bash
python scripts/utilities/list_conversions.py
```

**Expected output:**
```
============================================================
📊 SAS to Databricks Conversion Results
============================================================

Found 1 converted file(s)

Python File                         SAS Source              Size    Pipeline
----------------------------------------------------------------------
converted_sample_claims.py          sample_claims.sas       12.3 KB  ✅ Yes

============================================================

Pipeline YAMLs: 1/1

Next steps:
  1. Review converted files in ./transformations/
  2. Check pipeline YAMLs in ./resources/pipelines/
  3. Deploy: databricks bundle deploy -t dev
```

### Inspect Converted Python

```bash
cat transformations/converted_sample_claims.py
```

Look for:
- ✅ Header with configuration variables (`CATALOG`, `SCHEMA_BRONZE`, etc.)
- ✅ Spark Declarative Pipeline decorators (`@dp.table`, `@dp.view`)
- ✅ Schema assignments (Bronze tables → `sas_yourname_bronze`)
- ✅ Bronze metadata columns (`bronze_ingestion_timestamp`, etc.)
- ✅ Data quality expectations (if applicable)

### Inspect Pipeline YAML

```bash
cat resources/pipelines/pipeline_sampleclaims.yml
```

Look for:
- ✅ Pipeline name with developer ID: `sas_sampleclaims_yourname_pipeline`
- ✅ Configuration variables (`schema_bronze`, `schema_silver`, `schema_gold`)
- ✅ Library path: `./transformations/converted_sample_claims.py`
- ✅ Serverless and Photon enabled
- ✅ Tags (project, source_file, developer_id)

---

## Step 6: Deploy Pipeline

### Option A: Merge YAML into databricks.yml

Edit `databricks.yml` and add the new pipeline definition under `resources.pipelines`:

```yaml
resources:
  pipelines:
    pipeline_sampleclaims:
      name: "sas_sampleclaims_${var.developer_id}_pipeline"
      # ... (copy from pipeline_sampleclaims.yml)
```

Then redeploy:

```bash
databricks bundle deploy -t dev --var developer_id=yourname
```

### Option B: Use Include Pattern

Edit `databricks.yml` and add at the top:

```yaml
include:
  - ./resources/pipelines/*.yml
```

Then redeploy:

```bash
databricks bundle deploy -t dev --var developer_id=yourname
```

---

## Step 7: Validate Pipeline

Run a dry-run validation to check configuration.

```bash
python scripts/validation/dry_run_pipeline.py sas_sampleclaims_yourname_pipeline
```

**Expected output:**
```
================================================================================
🔍 Dry-Run Validation: sas_sampleclaims_yourname_pipeline
================================================================================

1️⃣  Searching for pipeline...
   ✅ Found pipeline: abc123def456
2️⃣  Fetching pipeline configuration...
   ✅ Catalog: na-dbxtraining
   ✅ Target: default
   ✅ Serverless: True
3️⃣  Validating configuration...
   ✅ schema_bronze: sas_yourname_bronze
   ✅ schema_silver: sas_yourname_silver
   ✅ schema_gold: sas_yourname_gold
4️⃣  Checking libraries...
   📄 File: ./transformations/converted_sample_claims.py

================================================================================
✅ DRY-RUN VALIDATION PASSED
================================================================================
```

---

## Step 8: Run the Pipeline

Start the pipeline to execute the converted code.

```bash
databricks pipelines start --pipeline-name sas_sampleclaims_yourname_pipeline
```

**Or via Databricks UI:**
1. Navigate to **Workflows → Pipelines**
2. Find `sas_sampleclaims_yourname_pipeline`
3. Click **Start**

**Monitor progress:**
- Watch the DAG (Directed Acyclic Graph) visualization
- Check table lineage (Bronze → Silver → Gold)
- Review data quality metrics (if expectations are defined)

**Expected result:**
- ✅ All tables created in appropriate schemas
- ✅ Data flows through Bronze → Silver → Gold
- ✅ No schema errors (qualified table names work)
- ✅ Audit columns present in Bronze tables

---

## Step 9: Query Results

Verify data was created correctly.

```sql
-- Check Bronze table
SELECT * FROM sas_yourname_bronze.claims_raw LIMIT 10;

-- Check Silver table (if applicable)
SELECT * FROM sas_yourname_silver.claims_enriched LIMIT 10;

-- Check Gold table
SELECT * FROM sas_yourname_gold.claims_summary;
```

**Validate Bronze metadata:**
```sql
SELECT 
    bronze_source_file,
    bronze_ingestion_timestamp,
    count(*) as record_count
FROM sas_yourname_bronze.claims_raw
GROUP BY bronze_source_file, bronze_ingestion_timestamp;
```

---

## Next Steps

### Add More SAS Files

1. Copy additional `.sas` files to `specifications/`
2. Re-run converter:
   ```bash
   databricks bundle run sas_dbx_code_translator -t dev
   ```
3. List new conversions:
   ```bash
   python scripts/utilities/list_conversions.py
   ```
4. Deploy new pipelines:
   ```bash
   databricks bundle deploy -t dev --var developer_id=yourname
   ```

### Customize Conversion

Edit converter widgets in `src/converter/sas_dbx.py`:

- `enable_views`: Toggle view vs table for intermediate transformations
- `api_style`: Change output API (`dp` vs `dlt`)
- `schema_prefix`: Change schema naming pattern

Re-run after changes:
```bash
databricks bundle run sas_dbx_code_translator -t dev
```

### Clean Restart

If something goes wrong:

```bash
# Drop and recreate schemas
python scripts/utilities/reset_schemas.py --developer-id yourname --confirm

# Re-deploy
databricks bundle deploy -t dev --var developer_id=yourname

# Re-run converter
databricks bundle run sas_dbx_code_translator -t dev
```

---

## Troubleshooting

### "No SAS files found"

**Cause:** `specifications/` directory is empty.

**Fix:** Add `.sas` files to `specifications/` directory.

### "Schema does not exist"

**Cause:** Schemas not created by bundle deployment.

**Fix:**
```bash
python scripts/setup/create_schemas.py --developer-id yourname
```

### "Pipeline not found"

**Cause:** Pipeline YAML not merged into `databricks.yml`, or deployment didn't run.

**Fix:**
```bash
# Merge YAML into databricks.yml or use include pattern
# Then redeploy
databricks bundle deploy -t dev --var developer_id=yourname
```

### "Table or view not found" (in pipeline execution)

**Cause:** Upstream table missing (dependency issue).

**Fix:**
1. Check which tables the pipeline reads
2. Run upstream pipelines first (Bronze before Silver before Gold)
3. Verify tables exist via SQL query

### Conversion Errors

**Cause:** Unsupported SAS syntax or edge case.

**Fix:**
1. Check `V7_PRODUCTION_FIXES.md` for known issues
2. Review SAS file for problematic patterns
3. Simplify SAS code or split into multiple files
4. Check converter logs in Databricks job run

---

## Summary

**You just:**
✅ Deployed a production-ready DAB bundle  
✅ Converted SAS code to Spark Declarative Pipelines  
✅ Auto-generated pipeline YAML files  
✅ Validated and executed your first pipeline  
✅ Queried results in Unity Catalog  

**Total time:** ~10 minutes

---

## What's Next?

- **Scale up:** Add more SAS files and convert in bulk
- **Customize:** Tweak converter settings for your use case
- **Validate:** Compare Databricks output vs SAS output (data parity)
- **Deploy to prod:** Use `-t prod` and production catalog
- **Schedule:** Add cron schedules to pipeline YAMLs
- **Monitor:** Set up alerts for pipeline failures

---

## Support

**Issues?**
- Connection: `python scripts/setup/test_connection.py`
- Validation: `python scripts/validation/dry_run_pipeline.py <pipeline>`
- Conversions: `python scripts/utilities/list_conversions.py`
- Documentation: See [README.md](README.md) and [scripts/README.md](scripts/README.md)

**Deep dive:**
- V7 fixes: [V7_PRODUCTION_FIXES.md](V7_PRODUCTION_FIXES.md)
- Script details: [scripts/README.md](scripts/README.md)
- Architecture: [README.md](README.md)

---

**Happy migrating! 🚀**
