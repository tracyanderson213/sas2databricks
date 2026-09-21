# Databricks notebook source
# MAGIC %md
# MAGIC # 03b - Simplified SAS Conversion (Flat Structure)
# MAGIC
# MAGIC **Purpose:** Convert SAS files with simplified output structure
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC - ✅ Run `02b_upload_comprehensive_claims.py` (or any 02* notebook)
# MAGIC
# MAGIC **What this does:**
# MAGIC - Converts ALL SAS files found in input/
# MAGIC - Saves to flat structure: `staging/needs_review/`
# MAGIC - Uses functional naming: `converted_{filename}.py`
# MAGIC
# MAGIC **Output structure:**
# MAGIC ```
# MAGIC staging/
# MAGIC └── needs_review/
# MAGIC     ├── converted_claims_adjudication_comprehensive.py
# MAGIC     ├── converted_simple_select.py
# MAGIC     └── converted_format_cars.py
# MAGIC ```

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
import os
import glob

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
# MAGIC ## Convert All Files

# COMMAND ----------

print("="*80)
print("🔄 CONVERTING ALL SAS FILES")
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

        # Convert
        result = migrate(
            sas_text,
            target="sdp",
            model="opus-4.8",
            source_path=sas_file['filename']
        )

        # Create output filename with prefix
        base_name = sas_file['filename'].replace('.sas', '')
        output_filename = f"converted_{base_name}.py"
        output_path = os.path.join(output_dir_local, output_filename)

        # Write converted code
        with open(output_path, 'w') as f:
            f.write(result.code)

        print(f"✅ Converted!")
        print(f"   Input:  {sas_file['filename']}")
        print(f"   Output: {output_filename}")
        print(f"   Target: {result.target}")

        results.append({
            'input': sas_file['filename'],
            'output': output_filename,
            'status': 'success',
            'project': sas_file['project']
        })

    except Exception as e:
        print(f"❌ Error: {e}")
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
    print("✅ SUCCESSFUL CONVERSIONS")
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
print("📂 OUTPUT FILES")
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
# MAGIC ## Read First Converted File

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

        # Show first 100 lines
        lines = code.split('\n')
        preview_lines = lines[:100]

        print('\n'.join(preview_lines))

        if len(lines) > 100:
            print()
            print("...")
            print(f"[{len(lines) - 100} more lines]")

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
# MAGIC ## Move to Approved (Optional)

# COMMAND ----------

# Uncomment and run this cell to move files to "approved" folder after review

# approved_dir = f"{staging_base}/approved"
# approved_dir_local = approved_dir.replace("/Volumes", "/dbfs/Volumes")
# os.makedirs(approved_dir_local, exist_ok=True)

# # Move all files from needs_review to approved
# for r in results:
#     if r['status'] == 'success':
#         src = os.path.join(output_dir_local, r['output'])
#         dst = os.path.join(approved_dir_local, r['output'])

#         if os.path.exists(src):
#             os.rename(src, dst)
#             print(f"✅ Moved: {r['output']} → approved/")

# print("\n✅ All files moved to approved/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps

# COMMAND ----------

print("="*80)
print("✅ CONVERSION COMPLETE!")
print("="*80)
print()
print("📋 What you have now:")
print(f"  ✅ {success_count} SAS files converted to Python")
print(f"  ✅ All saved to: {output_dir}")
print("  ✅ Files prefixed with 'converted_' for clarity")
print()
print("="*80)
print("🎯 NEXT STEPS")
print("="*80)
print()
print("1️⃣  Review Converted Files")
print(f"   Location: {output_dir}")
print("   Check: Business logic, data transformations")
print()
print("2️⃣  Test One File")
print("   - Copy converted code to new notebook")
print("   - Run it to verify it works")
print("   - Check output data")
print()
print("3️⃣  Approve Good Conversions")
print("   - Run the 'Move to Approved' cell above")
print("   - Or manually move files you've reviewed")
print()
print("4️⃣  Deploy")
print("   - Create SDP pipeline from approved code")
print("   - Deploy via DAB or manually")
print()
print("="*80)
print()
print("💡 TIP: All files in single 'needs_review/' folder")
print("   Makes it easy to review and approve in batch!")
print()
print("="*80)
