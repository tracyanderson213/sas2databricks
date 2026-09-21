# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - Test SAS Conversion
# MAGIC
# MAGIC **Purpose:** Run sas2databricks converter on sample SAS code
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC - ✅ Run `02_upload_sample_sas.py` second
# MAGIC - ⏳ sas2databricks will be installed automatically below
# MAGIC
# MAGIC **What this does:**
# MAGIC 1. Install sas2databricks package
# MAGIC 2. Convert 3 sample SAS projects
# MAGIC 3. Generate conversion reports
# MAGIC 4. Show results
# MAGIC
# MAGIC **After this notebook:** Review conversion reports and deploy test pipelines

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Install sas2databricks

# COMMAND ----------

# MAGIC %pip install sas2databricks

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Import and Configure

# COMMAND ----------

from sas2databricks import migrate
import os

# Base paths
input_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input"
staging_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging"

print("✅ sas2databricks imported successfully")
print(f"📁 Input:   {input_base}")
print(f"📁 Staging: {staging_base}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Convert Sample 1 (Simple SQL)

# COMMAND ----------

print("="*80)
print("🔄 Converting: test_simple_sql")
print("="*80)
print()

try:
    # Read SAS source file
    sas_filename = "simple_select.sas"
    sas_path = f"{input_base}/test_simple_sql/sas/{sas_filename}"
    with open(sas_path.replace("/Volumes", "/dbfs/Volumes"), 'r') as f:
        sas_text = f.read()
    print(f"📄 Source: {sas_filename} ({len(sas_text)} bytes)")
    print()

    # Convert using migrate()
    result1 = migrate(
        sas_text,
        target="sdp",
        model="opus-4.8",
        source_path=sas_filename
    )

    # Write converted code to staging
    staging_dir = f"{staging_base}/test_simple_sql"
    staging_dir_local = staging_dir.replace("/Volumes", "/dbfs/Volumes")
    os.makedirs(staging_dir_local, exist_ok=True)

    # ✅ PRESERVE ORIGINAL FILENAME (don't use result1.filename which is generic)
    output_basename = sas_filename.replace('.sas', '.py')
    output_file = f"{staging_dir_local}/{output_basename}"

    with open(output_file, 'w') as f:
        f.write(result1.code)

    print("✅ Conversion complete!")
    print(f"📄 Input:   {sas_filename}")
    print(f"📄 Output:  {output_basename}  ← Matches input name!")
    print(f"🎯 Target:  {result1.target}")
    print(f"🤖 Model:   {result1.model}")
    print()

    # Show step reports
    if result1.reports:
        print("📊 Step Reports:")
        for rpt in result1.reports:
            print(f"  {rpt}")
    print()
    print(f"📁 Saved to: {staging_dir}/{output_basename}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Review Output

# COMMAND ----------

# List generated files
print("📂 Generated files for test_simple_sql:")
print("="*80)

try:
    files = dbutils.fs.ls(f"{staging_base}/test_simple_sql")
    for file in files:
        print(f"  {'📁' if file.isDir() else '📄'} {file.name}")
except Exception as e:
    print(f"⚠️  Output not yet generated: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Read Converted Code

# COMMAND ----------

# Read the converted SDP pipeline (output from previous cell)
try:
    # Use the preserved filename (matches original SAS name)
    output_filename = "simple_select.py"
    converted_file = f"{staging_base}/test_simple_sql/{output_filename}"
    converted_file_local = converted_file.replace("/Volumes", "/dbfs/Volumes")

    with open(converted_file_local, 'r') as f:
        code = f.read()

    print(f"📄 Converted Pipeline ({output_filename}):")
    print("="*80)
    print(code)
    print("="*80)

except Exception as e:
    print(f"⚠️  Could not read converted file: {e}")
    print("\nMake sure previous cell has been run first.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Convert Sample 2 (Format + DATA)

# COMMAND ----------

print("="*80)
print("🔄 Converting: test_format_data")
print("="*80)
print()

try:
    # Read SAS source file
    sas_filename = "format_cars.sas"
    sas_path = f"{input_base}/test_format_data/sas/{sas_filename}"
    with open(sas_path.replace("/Volumes", "/dbfs/Volumes"), 'r') as f:
        sas_text = f.read()
    print(f"📄 Source: {sas_filename} ({len(sas_text)} bytes)")
    print()

    # Convert using migrate()
    result2 = migrate(
        sas_text,
        target="sdp",
        model="opus-4.8",
        source_path=sas_filename
    )

    # Write converted code to staging
    staging_dir = f"{staging_base}/test_format_data"
    staging_dir_local = staging_dir.replace("/Volumes", "/dbfs/Volumes")
    os.makedirs(staging_dir_local, exist_ok=True)

    # ✅ PRESERVE ORIGINAL FILENAME
    output_basename = sas_filename.replace('.sas', '.py')
    output_file = f"{staging_dir_local}/{output_basename}"

    with open(output_file, 'w') as f:
        f.write(result2.code)

    print("✅ Conversion complete!")
    print(f"📄 Input:   {sas_filename}")
    print(f"📄 Output:  {output_basename}  ← Matches input name!")
    print(f"🎯 Target:  {result2.target}")
    print(f"🤖 Model:   {result2.model}")
    print()

    if result2.reports:
        print("📊 Step Reports:")
        for rpt in result2.reports:
            print(f"  {rpt}")
    print()
    print(f"📁 Saved to: {staging_dir}/{output_basename}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Convert Sample 3 (SELECT/WHEN)

# COMMAND ----------

print("="*80)
print("🔄 Converting: test_select_when")
print("="*80)
print()

try:
    # Read SAS source file
    sas_filename = "car_origin.sas"
    sas_path = f"{input_base}/test_select_when/sas/{sas_filename}"
    with open(sas_path.replace("/Volumes", "/dbfs/Volumes"), 'r') as f:
        sas_text = f.read()
    print(f"📄 Source: {sas_filename} ({len(sas_text)} bytes)")
    print()

    # Convert using migrate()
    result3 = migrate(
        sas_text,
        target="sdp",
        model="opus-4.8",
        source_path=sas_filename
    )

    # Write converted code to staging
    staging_dir = f"{staging_base}/test_select_when"
    staging_dir_local = staging_dir.replace("/Volumes", "/dbfs/Volumes")
    os.makedirs(staging_dir_local, exist_ok=True)

    # ✅ PRESERVE ORIGINAL FILENAME
    output_basename = sas_filename.replace('.sas', '.py')
    output_file = f"{staging_dir_local}/{output_basename}"

    with open(output_file, 'w') as f:
        f.write(result3.code)

    print("✅ Conversion complete!")
    print(f"📄 Input:   {sas_filename}")
    print(f"📄 Output:  {output_basename}  ← Matches input name!")
    print(f"🎯 Target:  {result3.target}")
    print(f"🤖 Model:   {result3.model}")
    print()

    if result3.reports:
        print("📊 Step Reports:")
        for rpt in result3.reports:
            print(f"  {rpt}")
    print()
    print(f"📁 Saved to: {staging_dir}/{output_basename}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Summary Report

# COMMAND ----------

print("="*80)
print("📊 CONVERSION SUMMARY")
print("="*80)
print()

projects = ["test_simple_sql", "test_format_data", "test_select_when"]

for project in projects:
    print(f"\n{'='*80}")
    print(f"Project: {project}")
    print(f"{'='*80}")

    try:
        # Check if staging output exists
        staging_path = f"{staging_base}/{project}"
        files = dbutils.fs.ls(staging_path)

        print(f"✅ Output generated: {len(files)} items")

        # List all files
        for file in files:
            icon = "📁" if file.isDir() else "📄"
            print(f"  {icon} {file.name}")

        print(f"\n📁 Location: {staging_path}")

    except Exception as e:
        print(f"❌ Not converted: {e}")

print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 9: Next Steps

# COMMAND ----------

print("="*80)
print("✅ CONVERSION TESTING COMPLETE!")
print("="*80)
print()
print("📋 What you have now:")
print("  ✅ 3 SAS projects converted to SDP")
print("  ✅ Converted Python code saved to staging/")
print("  ✅ Ready for review and deployment")
print()
print("="*80)
print("🎯 NEXT STEPS")
print("="*80)
print()
print("1️⃣  Review Converted Code")
print("   - Read: staging/{project}/*.py files")
print("   - Verify: Business logic looks correct")
print("   - Check: Target is 'sdp' (Spark Declarative Pipelines)")
print()
print("2️⃣  Test the Converted Pipeline")
print("   - Copy converted code to a new notebook")
print("   - Run it to verify it works")
print("   - Check data output")
print()
print("3️⃣  Convert Your Real SAS Code")
print("   - Upload to: input/your_project/sas/*.sas")
print("   - Create: input/your_project/config.yaml")
print("   - Run conversion using same pattern")
print()
print("4️⃣  Deploy to Production")
print("   - Review converted code")
print("   - Create proper SDP pipeline")
print("   - Deploy via DAB or manually")
print()
print("="*80)
print()
print("✅ COMPLETED: Notebooks 01, 02, 03")
print("➡️  NEXT: Review converted code and test")
print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification Checklist

# COMMAND ----------

print("="*80)
print("✅ VERIFICATION CHECKLIST")
print("="*80)
print()

# Check volumes exist
print("Checking infrastructure...")
try:
    dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration")
    print("  ✅ Volume structure exists")
except:
    print("  ❌ Volume structure not found - run 01_setup_volumes.py")

# Check sample SAS uploaded
print("\nChecking sample SAS...")
try:
    projects = dbutils.fs.ls(f"{input_base}")
    if len(projects) >= 3:
        print(f"  ✅ {len(projects)} projects in input/")
    else:
        print(f"  ⚠️  Only {len(projects)} projects - run 02_upload_sample_sas.py")
except:
    print("  ❌ No projects found - run 02_upload_sample_sas.py")

# Check conversions completed
print("\nChecking conversions...")
try:
    staging_projects = dbutils.fs.ls(f"{staging_base}")
    if len(staging_projects) >= 3:
        print(f"  ✅ {len(staging_projects)} projects converted")
        print()
        # Show what was converted
        for project in projects:
            try:
                files = dbutils.fs.ls(f"{staging_base}/{project}")
                py_files = [f.name for f in files if f.name.endswith('.py')]
                if py_files:
                    print(f"    {project}: {', '.join(py_files)}")
            except:
                pass
    else:
        print(f"  ⚠️  Only {len(staging_projects)} converted - check for errors above")
except:
    print("  ❌ No conversions found - check for errors above")

print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting

# COMMAND ----------

print("🔧 Troubleshooting Guide")
print("="*80)
print()
print("❌ sas2databricks not found:")
print("   → Re-run: %pip install sas2databricks")
print("   → Restart kernel if needed")
print()
print("❌ Conversion fails with 'migrate not found':")
print("   → Verify sas2databricks installed: %pip show sas2databricks")
print("   → Try: %pip install --upgrade sas2databricks")
print()
print("❌ Cannot read SAS files:")
print("   → Check file paths use /dbfs/Volumes prefix for local operations")
print("   → Verify files uploaded by notebook 02")
print()
print("❌ Cannot write output files:")
print("   → Check permissions on staging/ folder")
print("   → Verify os.makedirs() succeeded")
print()
print("❌ Conversion fails with API errors:")
print("   → Check if LLM API credentials needed")
print("   → For opus-4.8: May need Anthropic API key")
print("   → Try alternative: model='auto'")
print()
print("="*80)
