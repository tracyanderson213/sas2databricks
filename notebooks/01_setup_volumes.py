# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - Setup Unity Catalog Volumes for SAS Migration
# MAGIC
# MAGIC This notebook sets up the required Unity Catalog schema and production-grade volume structure for the SAS-to-Databricks migration project.
# MAGIC
# MAGIC **What this creates:**
# MAGIC - Unity Catalog schema: `na-dbxtraining.sas2dbx_migrate`
# MAGIC - Volume: `sas_migration` with production folder structure:
# MAGIC   - `00_inbound/` - Drop zone for raw SAS files (read-only after write)
# MAGIC   - `01_staging/` - Validated files ready for conversion
# MAGIC   - `02_processing/` - In-flight conversions (crash recovery zone)
# MAGIC   - `03_converted/` - Successful conversion output (needs_review, approved, deployed)
# MAGIC   - `04_archive/` - Archived source files (date-partitioned)
# MAGIC   - `05_reject/` - Failed conversions with error logs
# MAGIC   - `06_logs_manifest/` - Run metadata and audit trail

# COMMAND ----------

# Configuration
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"
VOLUME_NAME = "sas_migration"

print(f"📋 Configuration:")
print(f"  Catalog: {CATALOG}")
print(f"  Schema:  {SCHEMA}")
print(f"  Volume:  {VOLUME_NAME}")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Schema

# COMMAND ----------

# Create schema if it doesn't exist
spark.sql(f"""
    CREATE SCHEMA IF NOT EXISTS `{CATALOG}`.{SCHEMA}
    COMMENT 'Schema for SAS to Databricks migration project'
""")

print(f"✅ Schema created: `{CATALOG}`.{SCHEMA}")

# COMMAND ----------

# Verify schema exists
spark.sql(f"DESCRIBE SCHEMA `{CATALOG}`.{SCHEMA}").show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Volume

# COMMAND ----------

# Create volume for SAS migration files
spark.sql(f"""
    CREATE VOLUME IF NOT EXISTS `{CATALOG}`.{SCHEMA}.{VOLUME_NAME}
    COMMENT 'Volume for SAS migration: production-grade pipeline with audit trail'
""")

print(f"✅ Volume created: `{CATALOG}`.{SCHEMA}.{VOLUME_NAME}")

# COMMAND ----------

# Verify volume exists
spark.sql(f"DESCRIBE VOLUME `{CATALOG}`.{SCHEMA}.{VOLUME_NAME}").show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Production Folder Structure

# COMMAND ----------

# Create production-grade folder structure
volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}"

folders = [
    # Stage 0: Landing zone (read-only after write)
    "00_inbound",
    "00_inbound/claims_mainframe",
    "00_inbound/manual_uploads",

    # Stage 1: Validated, ready for conversion
    "01_staging",

    # Stage 2: In-flight conversion (crash recovery)
    "02_processing",

    # Stage 3: Conversion output
    "03_converted",
    "03_converted/needs_review",     # New conversions
    "03_converted/approved",          # Human-reviewed, ready to deploy
    "03_converted/deployed",          # Actually deployed to production

    # Stage 4: Archive (moved, not copied)
    "04_archive",

    # Stage 5: Failures with error logs
    "05_reject",

    # Stage 6: Run metadata and audit trail
    "06_logs_manifest",
]

print("="*80)
print("🏗️  Creating Production Folder Structure")
print("="*80)
print()

for folder in folders:
    folder_path = f"{volume_path}/{folder}"
    dbutils.fs.mkdirs(folder_path)
    indent = "  " * folder.count("/")
    print(f"{indent}✅ {folder}")

print()
print("="*80)
print("✅ Setup Complete!")
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Structure

# COMMAND ----------

print("="*80)
print("📂 Volume Root Structure:")
print("="*80)
print()

# List top-level folders
display(dbutils.fs.ls(volume_path))

# COMMAND ----------

print("="*80)
print("📂 Stage 0: Inbound (Landing Zone)")
print("="*80)
display(dbutils.fs.ls(f"{volume_path}/00_inbound"))

# COMMAND ----------

print("="*80)
print("📂 Stage 3: Converted (Output)")
print("="*80)
display(dbutils.fs.ls(f"{volume_path}/03_converted"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Flow Diagram

# COMMAND ----------

print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        SAS MIGRATION PIPELINE FLOW                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

    ┌─────────────────┐
    │  00_inbound/    │  ← Raw SAS files land here (read-only after write)
    └────────┬────────┘
             │ Validate: file exists, non-zero size, expected format
             ↓
    ┌─────────────────┐
    │  01_staging/    │  ← Validated, ready for conversion
    └────────┬────────┘
             │ Convert: sas2databricks processing
             ↓
    ┌─────────────────┐
    │ 02_processing/  │  ← In-flight (crash recovery zone)
    └────────┬────────┘
             │
             ├─ Success ─→ ┌──────────────────────┐
             │             │ 03_converted/        │
             │             │  ├─ needs_review/    │
             │             │  ├─ approved/        │
             │             │  └─ deployed/        │
             │             └──────────────────────┘
             │                      │
             │                      ↓
             │             ┌──────────────────────┐
             │             │ 04_archive/          │  ← Source files (date-partitioned)
             │             │  └─ YYYY/MM/DD/      │
             │             │     └─ run_XXXXX/    │
             │             └──────────────────────┘
             │
             └─ Failure ─→ ┌──────────────────────┐
                           │ 05_reject/           │  ← Failed + .err logs
                           └──────────────────────┘

    All runs logged to:
    ┌─────────────────┐
    │06_logs_manifest/│  ← Run metadata, checksums, audit trail
    └─────────────────┘
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC 1. ✅ Schema and volume structure are ready
# MAGIC 2. 📄 Upload SAS files to `00_inbound/` (manual or via notebook)
# MAGIC 3. 🔄 Run orchestration: `00_orchestrate_conversion_pipeline.py`
# MAGIC 4. ✅ Or run conversion directly: `03d_convert_sas.py`
# MAGIC
# MAGIC **Folder Purposes:**
# MAGIC - `00_inbound/` - Landing zone (treat as read-only)
# MAGIC - `01_staging/` - Validated files ready for processing
# MAGIC - `02_processing/` - Active conversion (detect crashed runs)
# MAGIC - `03_converted/needs_review/` - New conversions (quality gate)
# MAGIC - `03_converted/approved/` - Human-reviewed, ready to deploy
# MAGIC - `03_converted/deployed/` - Actually deployed to production
# MAGIC - `04_archive/` - Source files that completed successfully
# MAGIC - `05_reject/` - Failed files with `.err` logs
# MAGIC - `06_logs_manifest/` - Audit trail (checksums, timestamps, lineage)
