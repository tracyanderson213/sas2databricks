# Databricks notebook source
# MAGIC %md
# MAGIC # 03a - Check Conversion Output
# MAGIC
# MAGIC **Purpose:** Diagnose output file naming and view converted code
# MAGIC
# MAGIC **Run this after notebook 03** to see what was created

# COMMAND ----------

# MAGIC %md
# MAGIC ## List All Staging Projects

# COMMAND ----------

staging_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging"

print("="*80)
print("📁 STAGING FOLDERS")
print("="*80)
print()

try:
    projects = dbutils.fs.ls(staging_base)

    for project in projects:
        if project.isDir():
            print(f"\n📂 {project.name}")
            print("-"*80)

            # List files in each project
            try:
                files = dbutils.fs.ls(project.path)
                for file in files:
                    icon = "📁" if file.isDir() else "📄"
                    size_kb = file.size / 1024 if file.size > 0 else 0
                    print(f"  {icon} {file.name:50} ({size_kb:.1f} KB)")
            except Exception as e:
                print(f"  ⚠️  Error listing: {e}")

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure you've run notebook 03 first!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Converted Code (First Project)

# COMMAND ----------

# Find first .py file in staging
import os

staging_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging"
staging_base_local = staging_base.replace("/Volumes", "/dbfs/Volumes")

print("="*80)
print("🔍 SEARCHING FOR CONVERTED PYTHON FILES")
print("="*80)
print()

found_files = []

try:
    for project_dir in os.listdir(staging_base_local):
        project_path = os.path.join(staging_base_local, project_dir)

        if os.path.isdir(project_path):
            print(f"📂 Checking: {project_dir}")

            for file in os.listdir(project_path):
                if file.endswith('.py'):
                    file_path = os.path.join(project_path, file)
                    file_size = os.path.getsize(file_path)
                    found_files.append({
                        'project': project_dir,
                        'filename': file,
                        'path': file_path,
                        'size': file_size
                    })
                    print(f"  ✅ Found: {file} ({file_size} bytes)")

            if not any(f['project'] == project_dir for f in found_files):
                print(f"  ⚠️  No .py files found")

    print()
    print("="*80)
    print(f"Total Python files found: {len(found_files)}")
    print("="*80)

except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read First Converted File

# COMMAND ----------

if found_files:
    first_file = found_files[0]

    print("="*80)
    print(f"📄 CONVERTED CODE: {first_file['project']}/{first_file['filename']}")
    print("="*80)
    print()

    try:
        with open(first_file['path'], 'r') as f:
            code = f.read()

        print(code)

        print()
        print("="*80)
        print(f"File size: {len(code)} characters")
        print("="*80)

    except Exception as e:
        print(f"❌ Error reading file: {e}")
else:
    print("❌ No Python files found in staging!")
    print()
    print("Make sure you've run notebook 03_test_conversion.py first.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check for Original SAS Reference

# COMMAND ----------

if found_files:
    first_file = found_files[0]

    print("="*80)
    print("🔍 CHECKING FOR ORIGINAL SAS FILENAME REFERENCE")
    print("="*80)
    print()

    try:
        with open(first_file['path'], 'r') as f:
            code = f.read()

        # Look for original filename references
        lines = code.split('\n')

        print("Searching for original SAS filename in converted code...")
        print()

        found_reference = False
        for i, line in enumerate(lines[:50], 1):  # Check first 50 lines
            if 'claims_adjudication' in line.lower() or 'original' in line.lower() or 'source' in line.lower():
                print(f"Line {i}: {line}")
                found_reference = True

        if not found_reference:
            print("⚠️  WARNING: No reference to original SAS filename found!")
            print()
            print("This means you can't trace this Python file back to the original SAS.")
            print()
            print("Issue: sas2databricks created generic 'dlt_pipeline.py' name")
            print("Fix: Need to rename output files to match input SAS names")
        else:
            print()
            print("✅ Found references to original SAS file")

    except Exception as e:
        print(f"❌ Error: {e}")
else:
    print("❌ No files to check")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Problem Diagnosis

# COMMAND ----------

print("="*80)
print("🔧 FILE NAMING DIAGNOSIS")
print("="*80)
print()

if found_files:
    print("📊 Current Output Files:")
    print()
    for f in found_files:
        print(f"  Project: {f['project']}")
        print(f"  Output:  {f['filename']}")
        print()

    # Check if all are named dlt_pipeline.py
    dlt_count = sum(1 for f in found_files if f['filename'] == 'dlt_pipeline.py')

    if dlt_count > 1:
        print("❌ PROBLEM DETECTED:")
        print(f"   {dlt_count} projects all created 'dlt_pipeline.py'")
        print()
        print("   This means:")
        print("   - Files have generic names (no traceability)")
        print("   - Multiple conversions overwrite each other")
        print("   - Can't tell which .py came from which .sas")
        print()
        print("✅ SOLUTION:")
        print("   Notebook 03 should rename outputs to match input SAS files:")
        print()
        print("   Input:  claims_adjudication_comprehensive.sas")
        print("   Output: claims_adjudication_comprehensive.py")
        print()
        print("   See: FILE_NAMING_STRATEGY.md for details")
    elif dlt_count == 1:
        print("⚠️  POTENTIAL ISSUE:")
        print("   Output named 'dlt_pipeline.py' (generic)")
        print()
        print("   Consider renaming to match input SAS filename")
        print("   for better traceability")
    else:
        print("✅ Output files have custom names")
        print("   (Not all named dlt_pipeline.py)")

print()
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Recommended Fix

# COMMAND ----------

print("="*80)
print("📋 RECOMMENDED FIX")
print("="*80)
print()
print("Update notebook 03_test_conversion.py to rename output files:")
print()
print("CURRENT APPROACH:")
print("  result = migrate(sas_text, ...)")
print("  output_file = result.filename  # ← Returns 'dlt_pipeline.py'")
print()
print("FIXED APPROACH:")
print("  result = migrate(sas_text, ...)")
print("  ")
print("  # Use original SAS filename (not result.filename)")
print("  output_basename = sas_file.replace('.sas', '.py')")
print("  output_file = f'{staging_dir}/{output_basename}'")
print()
print("RESULT:")
print("  Input:  claims_adjudication_comprehensive.sas")
print("  Output: claims_adjudication_comprehensive.py  ← Matches!")
print()
print("="*80)
print()
print("See FILE_NAMING_STRATEGY.md for complete solution")
print()
print("="*80)
