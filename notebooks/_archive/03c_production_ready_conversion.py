# Databricks notebook source
# MAGIC %md
# MAGIC # 03c - Production-Ready SAS Conversion
# MAGIC
# MAGIC **Purpose:** Convert SAS files with production-ready templates
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC - ✅ Run any `02*` notebook to upload SAS files
# MAGIC
# MAGIC **What this adds:**
# MAGIC 1. Header comment block (name, purpose, author, change history)
# MAGIC 2. Parameter section (catalog, schema, paths)
# MAGIC 3. Bronze ingestion timestamp for audit trail
# MAGIC 4. Functional naming: `converted_{filename}.py`
# MAGIC 5. All in single `needs_review/` folder

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install sas2databricks

# COMMAND ----------

# MAGIC %pip install sas2databricks

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import and Configure

# COMMAND ----------

from sas2databricks import migrate
from datetime import datetime
import os
import re

# Base paths
input_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input"
staging_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging"

# Output to single directory
output_dir = f"{staging_base}/needs_review"
output_dir_local = output_dir.replace("/Volumes", "/dbfs/Volumes")
os.makedirs(output_dir_local, exist_ok=True)

print("✅ sas2databricks imported successfully")
print(f"📁 Input:   {input_base}")
print(f"📁 Output:  {output_dir}")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Template Generator

# COMMAND ----------

def generate_production_template(original_sas_filename, converted_code, sas_source_text, author="SAS Migration Team"):
    """
    Wraps converted code in production-ready template

    Args:
        original_sas_filename: Original .sas filename
        converted_code: Code from sas2databricks migrate()
        sas_source_text: Original SAS source code
        author: Author name for header

    Returns:
        Enhanced Python code with header, params, timestamps
    """

    base_name = original_sas_filename.replace('.sas', '')
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Build the template
    template = f'''# ==============================================================================
# CONVERTED SAS PIPELINE - PRODUCTION READY
# ==============================================================================
# Name:           converted_{base_name}.py
# Original File:  {original_sas_filename}
# Purpose:        Converted from SAS to Spark Declarative Pipeline (SDP)
# Author:         {author}
# Converted:      {current_date}
# Target:         Databricks SDP (Spark Declarative Pipelines)
# Model:          sas2databricks with opus-4.8
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# {current_date} | {author} | Initial conversion from SAS
# ------------------------------------------------------------------------------
#
# Notes:
# - This file was auto-generated using sas2databricks
# - Review business logic carefully before deploying to production
# - Test with sample data before running on full dataset
# - Verify data quality expectations are appropriate
#
# ==============================================================================

# ==============================================================================
# PARAMETERS
# ==============================================================================

# Unity Catalog configuration
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"

# Source paths (adjust for your environment)
SOURCE_VOLUME = f"/Volumes/{{CATALOG}}/{{SCHEMA}}/sas_migration"
INPUT_PATH = f"{{SOURCE_VOLUME}}/input"

# Data quality settings
ENABLE_EXPECTATIONS = True
EXPECTATION_ACTION = "drop"  # Options: "drop", "fail", "warn"

# ==============================================================================
# IMPORTS
# ==============================================================================

from pyspark.sql import functions as F
from pyspark.sql import types as T
from datetime import datetime

# ==============================================================================
# ORIGINAL SAS CODE (for reference)
# ==============================================================================
"""
{sas_source_text}
"""

# ==============================================================================
# CONVERTED PIPELINE CODE
# ==============================================================================

{converted_code}

# ==============================================================================
# HELPER: Add Bronze Metadata Columns
# ==============================================================================

def add_bronze_metadata(df, source_file="{original_sas_filename}"):
    """
    Adds standard bronze layer metadata columns for audit trail

    Args:
        df: Input DataFrame
        source_file: Name of source SAS file

    Returns:
        DataFrame with metadata columns
    """
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
    )

# ==============================================================================
# ENHANCED TABLES (with metadata)
# ==============================================================================

# NOTE: Uncomment and customize the tables below based on your converted code
#       Replace "example_table" with actual table names from conversion above

# Example pattern:
#
# @dlt.table(
#     name="bronze_example",
#     comment="Bronze layer with metadata - converted from {original_sas_filename}"
# )
# @dlt.expect_or_drop("valid_record", "id IS NOT NULL")
# def bronze_example():
#     # Get data from your converted table
#     df = spark.table("LIVE.example_table")  # Replace with actual table name
#
#     # Add bronze metadata
#     return add_bronze_metadata(df, source_file="{original_sas_filename}")

# ==============================================================================
# DATA QUALITY EXPECTATIONS
# ==============================================================================

# Add data quality checks based on SAS validation rules
# Example patterns:
#
# @dlt.expect_or_drop("valid_dates", "claim_date >= '2020-01-01'")
# @dlt.expect_or_drop("positive_amounts", "billed_amount > 0")
# @dlt.expect_or_warn("member_exists", "member_id IS NOT NULL")

# ==============================================================================
# END OF CONVERTED PIPELINE
# ==============================================================================
#
# Deployment checklist:
# □ Review business logic against original SAS
# □ Verify data quality expectations
# □ Test with sample data
# □ Validate output matches SAS results
# □ Update change history when modifying
# □ Deploy via DAB or pipeline UI
#
# ==============================================================================
'''

    return template

print("✅ Template generator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Find All SAS Files

# COMMAND ----------

input_base_local = input_base.replace("/Volumes", "/dbfs/Volumes")

# Find all .sas files recursively
sas_files = []
for root, dirs, files in os.walk(input_base_local):
    for file in files:
        if file.endswith('.sas'):
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, input_base_local)
            sas_files.append({
                'filename': file,
                'full_path': full_path,
                'rel_path': rel_path,
                'project': os.path.basename(os.path.dirname(os.path.dirname(full_path)))
            })

print("="*80)
print(f"🔍 FOUND {len(sas_files)} SAS FILES")
print("="*80)
print()

for i, f in enumerate(sas_files, 1):
    print(f"{i}. {f['filename']:45} (project: {f['project']})")

print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Convert with Production Template

# COMMAND ----------

print("="*80)
print("🔄 CONVERTING WITH PRODUCTION TEMPLATE")
print("="*80)
print()

results = []

for i, sas_file in enumerate(sas_files, 1):
    print(f"\n[{i}/{len(sas_files)}] Processing: {sas_file['filename']}")
    print("-"*80)

    try:
        # Read SAS source
        with open(sas_file['full_path'], 'r') as f:
            sas_text = f.read()

        print(f"📄 Size: {len(sas_text)} bytes")

        # Convert with sas2databricks
        result = migrate(
            sas_text,
            target="sdp",
            model="opus-4.8",
            source_path=sas_file['filename']
        )

        print(f"✅ Conversion complete")

        # Wrap in production template
        production_code = generate_production_template(
            original_sas_filename=sas_file['filename'],
            converted_code=result.code,
            sas_source_text=sas_text,
            author="SAS Migration Team"  # Customize this
        )

        # Create output filename with prefix
        base_name = sas_file['filename'].replace('.sas', '')
        output_filename = f"converted_{base_name}.py"
        output_path = os.path.join(output_dir_local, output_filename)

        # Write enhanced code
        with open(output_path, 'w') as f:
            f.write(production_code)

        print(f"📄 Input:  {sas_file['filename']}")
        print(f"📄 Output: {output_filename}")
        print(f"✨ Enhanced with:")
        print(f"   - Header comment block")
        print(f"   - Parameter section (CATALOG, SCHEMA)")
        print(f"   - Bronze metadata helper")
        print(f"   - Original SAS code reference")

        results.append({
            'input': sas_file['filename'],
            'output': output_filename,
            'status': 'success',
            'project': sas_file['project']
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'input': sas_file['filename'],
            'output': None,
            'status': 'failed',
            'error': str(e),
            'project': sas_file['project']
        })

print()
print("="*80)
print("✅ CONVERSION COMPLETE!")
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Report

# COMMAND ----------

print("="*80)
print("📊 CONVERSION SUMMARY")
print("="*80)
print()

success_count = sum(1 for r in results if r['status'] == 'success')
failed_count = sum(1 for r in results if r['status'] == 'failed')

print(f"Total files:     {len(results)}")
print(f"✅ Successful:   {success_count}")
print(f"❌ Failed:       {failed_count}")
print()

if success_count > 0:
    print("="*80)
    print("✅ SUCCESSFUL CONVERSIONS (with production template)")
    print("="*80)
    print()

    for r in results:
        if r['status'] == 'success':
            print(f"  {r['input']:40} → {r['output']}")
    print()

if failed_count > 0:
    print("="*80)
    print("❌ FAILED CONVERSIONS")
    print("="*80)
    print()

    for r in results:
        if r['status'] == 'failed':
            print(f"  {r['input']:40} - {r['error']}")
    print()

print("="*80)
print(f"📁 All converted files saved to:")
print(f"   {output_dir}")
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Output Files

# COMMAND ----------

print("="*80)
print("📂 OUTPUT FILES (Production-Ready)")
print("="*80)
print()

try:
    files = dbutils.fs.ls(output_dir)

    for file in sorted(files, key=lambda x: x.name):
        if file.name.endswith('.py'):
            size_kb = file.size / 1024
            print(f"  📄 {file.name:50} ({size_kb:.1f} KB)")

    print()
    print(f"Total: {len([f for f in files if f.name.endswith('.py')])} Python files")

except Exception as e:
    print(f"⚠️  Error listing files: {e}")

print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview First Converted File

# COMMAND ----------

if success_count > 0:
    first_success = next(r for r in results if r['status'] == 'success')

    print("="*80)
    print(f"📄 PREVIEW: {first_success['output']}")
    print("="*80)
    print()

    try:
        file_path = os.path.join(output_dir_local, first_success['output'])
        with open(file_path, 'r') as f:
            code = f.read()

        # Show first 150 lines (includes header + params + some code)
        lines = code.split('\n')
        preview_lines = lines[:150]

        print('\n'.join(preview_lines))

        if len(lines) > 150:
            print()
            print("...")
            print(f"[{len(lines) - 150} more lines]")

        print()
        print("="*80)
        print(f"Total: {len(lines)} lines")
        print("="*80)

    except Exception as e:
        print(f"❌ Error reading file: {e}")
else:
    print("⚠️  No successful conversions to preview")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Example: How to Use Bronze Metadata Helper

# COMMAND ----------

print("="*80)
print("💡 USING THE BRONZE METADATA HELPER")
print("="*80)
print()
print("Each converted file includes an add_bronze_metadata() helper function.")
print()
print("USAGE EXAMPLE:")
print("-"*80)
print("""
from pyspark.sql import functions as F

@dlt.table(
    name="bronze_claims",
    comment="Bronze layer claims with audit trail"
)
@dlt.expect_or_drop("valid_claim_id", "claim_id IS NOT NULL")
def bronze_claims():
    # Read your source data
    df = spark.read.parquet("/path/to/source")

    # Add bronze metadata columns
    return add_bronze_metadata(df, source_file="claims_raw.csv")

# Result includes these columns:
# - bronze_ingestion_timestamp (current_timestamp)
# - bronze_source_file (source filename)
# - bronze_ingestion_date (current_date)
""")
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customization Guide

# COMMAND ----------

print("="*80)
print("🎨 CUSTOMIZATION GUIDE")
print("="*80)
print()
print("Each converted file can be customized:")
print()
print("1️⃣  UPDATE PARAMETERS (lines 30-40):")
print("   - Change CATALOG, SCHEMA to your values")
print("   - Update SOURCE_VOLUME path")
print("   - Adjust EXPECTATION_ACTION")
print()
print("2️⃣  ADD YOUR NAME (line 15):")
print("   Author: [Your Name Here]")
print()
print("3️⃣  UPDATE CHANGE HISTORY (lines 18-22):")
print("   Add new entries when you modify the code")
print()
print("4️⃣  CUSTOMIZE BRONZE METADATA (lines 90-105):")
print("   Add more columns as needed:")
print("   - .withColumn('processing_date', F.current_date())")
print("   - .withColumn('pipeline_version', F.lit('v1.0'))")
print()
print("5️⃣  ADD DATA QUALITY EXPECTATIONS (lines 120-130):")
print("   Uncomment and add your rules:")
print("   - @dlt.expect_or_drop('valid_dates', 'date_col IS NOT NULL')")
print("   - @dlt.expect_or_warn('in_range', 'amount BETWEEN 0 AND 1000000')")
print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps

# COMMAND ----------

print("="*80)
print("✅ PRODUCTION-READY CONVERSION COMPLETE!")
print("="*80)
print()
print("📋 What you have now:")
print(f"  ✅ {success_count} SAS files converted with production template")
print(f"  ✅ Header comments (name, purpose, author, change history)")
print(f"  ✅ Parameter section (catalog, schema, paths)")
print(f"  ✅ Bronze metadata helper (ingestion timestamp)")
print(f"  ✅ Original SAS code embedded for reference")
print(f"  ✅ All saved to: {output_dir}")
print()
print("="*80)
print("🎯 NEXT STEPS")
print("="*80)
print()
print("1️⃣  Review and Customize")
print("   - Open each converted file")
print("   - Update CATALOG, SCHEMA parameters")
print("   - Add your name as author")
print("   - Review business logic")
print()
print("2️⃣  Test One File")
print("   - Copy converted code to new notebook")
print("   - Run it with sample data")
print("   - Verify output matches SAS")
print()
print("3️⃣  Add Data Quality Expectations")
print("   - Based on SAS validation rules")
print("   - Add @dlt.expect_or_drop() decorators")
print("   - Test with bad data to verify")
print()
print("4️⃣  Deploy to Production")
print("   - Move reviewed files to approved/")
print("   - Create SDP pipeline")
print("   - Deploy via DAB or UI")
print()
print("="*80)
print()
print("💡 TIP: All files include add_bronze_metadata() helper")
print("   Use it to add audit trail columns to your tables!")
print()
print("="*80)
