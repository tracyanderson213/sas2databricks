# SAS to Databricks Migration - Manual Upload Guide

**Complete walkthrough for setting up and running the SAS converter via manual upload.**

This guide assumes you have NO existing infrastructure and walks you through creating everything from scratch.

---

## Prerequisites

✅ Databricks workspace access  
✅ Permissions to create catalogs, schemas, and volumes  
✅ Ability to upload and run notebooks  

---

## Part 1: Create Infrastructure (One-Time Setup)

**Note:** We'll use the existing `na-dbxtraining` catalog (you don't have CREATE CATALOG permissions).

**Important:** The catalog name has a **hyphen** (`na-dbxtraining`), which requires backticks in SQL:
```sql
-- With backticks (safe)
SELECT * FROM `na-dbxtraining`.sas_bronze.table;

-- Without backticks (fails - hyphen interpreted as minus)
SELECT * FROM na-dbxtraining.sas_bronze.table;  -- ❌
```

---

### Step 1.1: Verify Catalog Access

Open a **SQL Editor** in Databricks and verify you can access the catalog:

```sql
-- Check catalog exists
SHOW CATALOGS LIKE 'na-dbxtraining';

-- Check your permissions
SHOW GRANTS ON CATALOG `na-dbxtraining`;

-- List existing schemas
SHOW SCHEMAS IN `na-dbxtraining`;
```

You should see `na-dbxtraining` and have at least `USE CATALOG` permission.

---

### Step 1.2: Create the Schemas

**Note:** Replace `NADBXTrainingGroup1` with your actual group name.

```sql
-- Configuration schema (shared)
CREATE SCHEMA IF NOT EXISTS `na-dbxtraining`.sas2dbx_migrate
COMMENT '3Cloud SAS Migration — Configuration and metadata (shared)';

-- Bronze layer (raw data)
CREATE SCHEMA IF NOT EXISTS `na-dbxtraining`.sas_bronze
COMMENT '3Cloud SAS Migration — Bronze layer (raw SAS data)';

-- Silver layer (transformations)
CREATE SCHEMA IF NOT EXISTS `na-dbxtraining`.sas_silver
COMMENT '3Cloud SAS Migration — Silver layer (business logic and transforms)';

-- Gold layer (analytics-ready)
CREATE SCHEMA IF NOT EXISTS `na-dbxtraining`.sas_gold
COMMENT '3Cloud SAS Migration — Gold layer (analytics-ready aggregations)';

-- Grant permissions to your group (optional - may already have via catalog grants)
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas2dbx_migrate TO `NADBXTrainingGroup1`;
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas_bronze TO `NADBXTrainingGroup1`;
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas_silver TO `NADBXTrainingGroup1`;
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas_gold TO `NADBXTrainingGroup1`;
```

**Verify:**
```sql
SHOW SCHEMAS IN `na-dbxtraining` LIKE 'sas%';
```

You should see 4 schemas:
- `sas2dbx_migrate`
- `sas_bronze`
- `sas_silver`
- `sas_gold`

---

### Step 1.3: Create the Volume

```sql
-- Create managed volume for SAS files and conversion output
CREATE VOLUME IF NOT EXISTS `na-dbxtraining`.sas2dbx_migrate.sas_migration
COMMENT 'SAS source files + converted Python pipelines + conversion logs';
```

**Verify:**
```sql
SHOW VOLUMES IN `na-dbxtraining`.sas2dbx_migrate;
```

You should see `sas_migration`.

---

### Step 1.4: Create Volume Folder Structure

Open a **new Python notebook** in Databricks and run:

```python
# Create folder structure in volume
volume_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"

folders = [
    f"{volume_base}/staging",              # Put SAS files here
    f"{volume_base}/converted",            # Converter output
    f"{volume_base}/archive",              # Archived originals (optional)
]

for folder in folders:
    dbutils.fs.mkdirs(folder)
    print(f"✅ Created: {folder}")

print("\n✅ Volume structure ready!")
```

**Verify:**
```python
dbutils.fs.ls(volume_base)
```

You should see 3 folders:
- `staging/` ← SAS source files
- `converted/` ← Python output
- `archive/` ← Backup (optional)

---

## Part 2: Upload the Converter Notebook

### Step 2.1: Get the Converter File

The converter is located at:
```
src/converter/sas_to_dbx_pipeline_converter.py
```

**I'll provide this file to you in the next message** (it's 90KB, so I'll show you how to access it).

---

### Step 2.2: Upload to Databricks

1. **Navigate to Workspace:**
   - Click **Workspace** in the left sidebar
   - Navigate to **Users → your_email@3cloudsolutions.com**

2. **Import the Notebook:**
   - Click the **⋮** (three dots) next to your user folder
   - Select **Import**
   - Click **Browse** and select `sas_dbx.py`
   - OR paste the URL if provided
   - Click **Import**

3. **The notebook will appear as:**
   ```
   /Workspace/Users/your_email@3cloudsolutions.com/sas_dbx
   ```

---

## Part 3: Add Your SAS Files

### Step 3.1: Upload SAS Files to Volume

You have **two options**:

**Option A: Via Databricks UI**

1. Navigate to **Catalog** in left sidebar
2. Browse to: `na-dbxtraining` → `sas2dbx_migrate` → `sas_migration` → `staging`
3. Click **Upload files**
4. Select your `.sas` files
5. Click **Upload**

**Option B: Via Notebook**

```python
# Copy from DBFS or other location
dbutils.fs.cp(
    "dbfs:/FileStore/your_file.sas",
    "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/your_file.sas"
)
```

---

### Step 3.2: Verify Files Are There

```python
volume_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"
staging_dir = f"{volume_base}/staging"

files = dbutils.fs.ls(staging_dir)
for file in files:
    if file.name.endswith('.sas'):
        print(f"✅ Found: {file.name}")
```

---

## Part 4: Run the Converter

### Step 4.1: Open the Converter Notebook

Navigate to:
```
/Workspace/Users/your_email@3cloudsolutions.com/sas_dbx
```

---

### Step 4.2: Configure Widgets (Top of Notebook)

You'll see 4 widgets at the top:

| Widget | Default Value | What It Does |
|--------|---------------|--------------|
| **catalog** | `na-dbxtraining` | Target catalog (with hyphen - requires backticks in SQL) |
| **schema_prefix** | `sas` | Creates `sas_bronze`, `sas_silver`, `sas_gold` |
| **enable_views** | `true` | Convert intermediate tables to views |
| **api_style** | `dp` | Use Spark Declarative Pipeline API |

**For your setup, use the defaults** (no changes needed).

**Note:** The catalog has a hyphen (`na-dbxtraining`), but the converter handles this automatically.

---

### Step 4.3: Run the Notebook

Click **Run all** or run cells one by one:

1. **Cell 1-2:** Widget configuration
2. **Cell 3:** Install `sas2databricks` package (takes ~30 seconds)
3. **Cell 4:** Python restart (automatic)
4. **Cells 5-30:** Conversion logic and helper functions
5. **Cell 31:** Main conversion loop

**Expected output:**
```
================================================================================
📄 Converting SAS Files to Databricks Pipelines
================================================================================

Found 2 file(s) to convert:
  - claims_adjudication.sas
  - risk_scoring.sas

Converting: claims_adjudication.sas
📄 Input:  claims_adjudication.sas
📄 Output: converted_claims_adjudication.py
📋 Pipeline YAML: pipeline_claimsadjudication.yml
✨ Enhanced with:
   - Intelligent layer detection (Bronze/Silver/Gold)
   - Three schema variables
   - View optimization for intermediate tables
   - Bronze metadata helper
   - ✅ ALL 5 BUG FIXES APPLIED

Converting: risk_scoring.sas
📄 Input:  risk_scoring.sas
📄 Output: converted_risk_scoring.py
📋 Pipeline YAML: pipeline_riskscoring.yml
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
Successful: 2
Failed: 0
```

---

## Part 5: Review the Results

### Step 5.1: Check Converted Python Files

```python
output_dir = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/converted"
files = dbutils.fs.ls(output_dir)

for file in files:
    if file.name.endswith('.py'):
        print(f"✅ {file.name}")
```

### Step 5.2: View a Converted File

```python
# Read one of the converted files
file_path = f"{output_dir}/converted_claims_adjudication.py"
with open(file_path.replace("/Volumes", "/dbfs/Volumes"), 'r') as f:
    content = f.read()
    print(content[:2000])  # Show first 2000 characters
```

Look for:
- ✅ `CATALOG = "na-dbxtraining"` (with hyphen)
- ✅ `SCHEMA_BRONZE = "sas_bronze"`
- ✅ `SCHEMA_SILVER = "sas_silver"`
- ✅ `SCHEMA_GOLD = "sas_gold"`
- ✅ `@dp.table` decorators
- ✅ Bronze metadata helpers
- ✅ Table references use backticks for catalog: `` `{CATALOG}`.{schema}.{table} ``

---

### Step 5.3: Check Pipeline YAMLs

```python
# Pipeline YAMLs are in the same directory
yaml_files = [f for f in dbutils.fs.ls(output_dir) if f.name.endswith('.yml')]

for yaml_file in yaml_files:
    print(f"✅ {yaml_file.name}")
```

---

## Part 6: Deploy and Run Pipelines

### Step 6.1: Import Converted Python Files

For each converted Python file:

1. **Navigate to Workspace**
2. **Import** the Python file from the volume:
   ```
   /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/converted/converted_claims_adjudication.py
   ```
3. Place it in a pipelines folder like:
   ```
   /Workspace/Users/your_email/sas_pipelines/converted_claims_adjudication
   ```

---

### Step 6.2: Create Pipeline via UI

1. Navigate to **Workflows → Delta Live Tables**
2. Click **Create pipeline**
3. Configure:
   - **Name:** `sas_claims_adjudication_pipeline`
   - **Product edition:** Pro or Advanced
   - **Notebook libraries:**
     - Add: `/Workspace/Users/your_email/sas_pipelines/converted_claims_adjudication`
   - **Configuration:**
     ```
     catalog_name: na-dbxtraining
     schema_bronze: sas_bronze
     schema_silver: sas_silver
     schema_gold: sas_gold
     enable_views: true
     ```
     **Note:** The pipeline framework handles the hyphenated catalog name automatically.
   - **Target:** `default`
   - **Storage location:** (leave default)
   - **Cluster mode:** `Serverless` ✅
4. Click **Create**

---

### Step 6.3: Run the Pipeline

1. Click **Start** on your pipeline
2. Watch the DAG execute
3. Tables will be created in:
   - `` `na-dbxtraining`.sas_bronze.* ``
   - `` `na-dbxtraining`.sas_silver.* ``
   - `` `na-dbxtraining`.sas_gold.* ``

---

## Part 7: Verify Data

### Step 7.1: Query Bronze Tables

```sql
-- Check what tables were created
SHOW TABLES IN `na-dbxtraining`.sas_bronze;

-- Query a bronze table
SELECT * FROM `na-dbxtraining`.sas_bronze.raw_claims LIMIT 10;

-- Check bronze metadata
SELECT 
    bronze_source_file,
    bronze_ingestion_timestamp,
    count(*) as row_count
FROM `na-dbxtraining`.sas_bronze.raw_claims
GROUP BY bronze_source_file, bronze_ingestion_timestamp;
```

---

### Step 7.2: Query Silver Tables

```sql
SHOW TABLES IN `na-dbxtraining`.sas_silver;

SELECT * FROM `na-dbxtraining`.sas_silver.enriched_claims LIMIT 10;
```

---

### Step 7.3: Query Gold Tables

```sql
SHOW TABLES IN `na-dbxtraining`.sas_gold;

SELECT * FROM `na-dbxtraining`.sas_gold.claims_summary;
```

---

## Part 8: Adding More SAS Files (Ongoing)

### Step 8.1: Upload New SAS File

```python
# Copy to staging
dbutils.fs.cp(
    "dbfs:/path/to/new_program.sas",
    "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/new_program.sas"
)
```

### Step 8.2: Re-Run Converter

Just open the `sas_dbx` notebook and click **Run all** again.

It will:
- ✅ Convert all files in staging (including new ones)
- ✅ Overwrite existing converted files (in case you fixed bugs)
- ✅ Generate new pipeline YAMLs

### Step 8.3: Deploy New Pipeline

Repeat Part 6 for the new converted file.

---

## Troubleshooting

### "Schema does not exist"

**Fix:**
```sql
-- Make sure all schemas exist
SHOW SCHEMAS IN `na-dbxtraining`;

-- Create missing schema
CREATE SCHEMA IF NOT EXISTS `na-dbxtraining`.sas_bronze;
```

---

### "Volume not found"

**Fix:**
```sql
-- Check volume exists
SHOW VOLUMES IN `na-dbxtraining`.sas2dbx_migrate;

-- Create if missing
CREATE VOLUME IF NOT EXISTS `na-dbxtraining`.sas2dbx_migrate.sas_migration;
```

---

### "No SAS files found"

**Fix:**
```python
# Check staging directory
volume_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"
files = dbutils.fs.ls(f"{volume_base}/staging")
print([f.name for f in files if f.name.endswith('.sas')])
```

Make sure `.sas` files are in `staging/` folder.

---

### "sas2databricks not found"

**Fix:**
```python
# Re-install package
%pip install sas2databricks
dbutils.library.restartPython()
```

---

### "Permission denied"

**Fix:**
```sql
-- You should already have catalog permissions via your group
-- Check current permissions
SHOW GRANTS ON CATALOG `na-dbxtraining`;

-- If needed, request your admin grant schema permissions:
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas_bronze TO `NADBXTrainingGroup1`;
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas_silver TO `NADBXTrainingGroup1`;
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas_gold TO `NADBXTrainingGroup1`;
GRANT ALL PRIVILEGES ON SCHEMA `na-dbxtraining`.sas2dbx_migrate TO `NADBXTrainingGroup1`;
```

---

## Summary

**You just:**
✅ Created bronze/silver/gold schemas in existing `na-dbxtraining` catalog  
✅ Created volume for SAS files and conversion output  
✅ Uploaded and ran the converter notebook  
✅ Converted SAS → Python with intelligent layer detection  
✅ Created and ran Spark Declarative Pipelines  
✅ Queried data in Unity Catalog  

**Total time:** ~30 minutes (including first-time setup)

**Ongoing workflow:**
1. Upload new SAS file to `staging/`
2. Run `sas_dbx` notebook
3. Import converted Python file
4. Create pipeline in UI
5. Run pipeline

---

## Next Steps

- **Add more SAS files:** Upload to staging and re-run converter
- **Schedule pipelines:** Add cron schedules to pipelines
- **Monitor:** Set up alerts for pipeline failures
- **Validate:** Compare Databricks output vs SAS output
- **Optimize:** Tune pipeline settings (cluster size, retries, etc.)

---

**Need help?** Check:
- `README.md` — Architecture and features
- `V7_PRODUCTION_FIXES.md` — Bug fixes documentation
- `scripts/README.md` — Utility scripts (when you move to bundle deployment)

---

**Happy migrating! 🚀**
