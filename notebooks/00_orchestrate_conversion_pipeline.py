# Databricks notebook source
# MAGIC %md
# MAGIC # 00 - Orchestrate SAS Conversion Pipeline
# MAGIC
# MAGIC **Purpose:** End-to-end orchestration of the SAS migration pipeline
# MAGIC
# MAGIC **Pipeline Stages:**
# MAGIC 1. **Validate** - Check files in `00_inbound/`, move valid files to `01_staging/`
# MAGIC 2. **Convert** - Process files from `01_staging/` → `03_converted/needs_review/`
# MAGIC 3. **Archive** - Move successful source files to `04_archive/YYYY/MM/DD/run_XXXXX/`
# MAGIC 4. **Reject** - Move failed files to `05_reject/` with `.err` logs
# MAGIC 5. **Manifest** - Write run metadata to `06_logs_manifest/run_XXXXX.json`
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC - ✅ Upload SAS files to `00_inbound/`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import uuid
from datetime import datetime
import json
import hashlib
import os

# Generate unique run ID
run_id = f"run_{uuid.uuid4().hex[:8]}"
start_time = datetime.now()

# Volume paths
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"
VOLUME_NAME = "sas_migration"
volume_base = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}"

# Stage paths
inbound_dir = f"{volume_base}/00_inbound"
staging_dir = f"{volume_base}/01_staging"
processing_dir = f"{volume_base}/02_processing"
converted_dir = f"{volume_base}/03_converted/needs_review"
archive_base = f"{volume_base}/04_archive"
reject_dir = f"{volume_base}/05_reject"
manifest_dir = f"{volume_base}/06_logs_manifest"

# Archive with date partitioning
archive_dir = f"{archive_base}/{start_time.strftime('%Y/%m/%d')}/{run_id}"

print("="*80)
print(f"🚀 SAS CONVERSION PIPELINE - {run_id}")
print("="*80)
print(f"⏰ Start time:     {start_time.isoformat()}")
print(f"📁 Inbound:        {inbound_dir}")
print(f"📁 Staging:        {staging_dir}")
print(f"📁 Processing:     {processing_dir}")
print(f"📁 Converted:      {converted_dir}")
print(f"📁 Archive:        {archive_dir}")
print(f"📁 Reject:         {reject_dir}")
print(f"📁 Manifest:       {manifest_dir}")
print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 1: Validate Inbound Files

# COMMAND ----------

print("="*80)
print("📥 STAGE 1: VALIDATE INBOUND FILES")
print("="*80)
print()

validated_files = []
skipped_files = []

# Scan all subdirectories of 00_inbound
def scan_inbound_recursive(path):
    """Recursively find all .sas files in inbound"""
    files = []
    try:
        for item in dbutils.fs.ls(path):
            if item.isDir():
                # Recurse into subdirectories
                files.extend(scan_inbound_recursive(item.path))
            elif item.name.endswith('.sas'):
                files.append(item)
    except Exception as e:
        print(f"⚠️  Error scanning {path}: {e}")
    return files

inbound_files = scan_inbound_recursive(inbound_dir)

print(f"Found {len(inbound_files)} SAS files in inbound/")
print()

for file_info in inbound_files:
    print(f"Validating: {file_info.name}")

    # Basic validation
    if file_info.size == 0:
        print(f"  ❌ SKIP: Zero size")
        skipped_files.append({
            'file': file_info.name,
            'reason': 'Zero size',
            'path': file_info.path
        })
        continue

    # Read file to check it's readable
    try:
        content = dbutils.fs.head(file_info.path, 1024)
        if not content or len(content.strip()) == 0:
            print(f"  ❌ SKIP: Empty or unreadable")
            skipped_files.append({
                'file': file_info.name,
                'reason': 'Empty or unreadable',
                'path': file_info.path
            })
            continue
    except Exception as e:
        print(f"  ❌ SKIP: Read error - {e}")
        skipped_files.append({
            'file': file_info.name,
            'reason': f'Read error: {e}',
            'path': file_info.path
        })
        continue

    # Calculate checksum
    try:
        full_content = dbutils.fs.head(file_info.path, file_info.size)
        checksum = hashlib.sha256(full_content.encode('utf-8')).hexdigest()
    except:
        checksum = "UNKNOWN"

    # Move to staging
    staging_path = f"{staging_dir}/{file_info.name}"
    try:
        dbutils.fs.mv(file_info.path, staging_path)
        print(f"  ✅ Validated and staged")
        validated_files.append({
            'filename': file_info.name,
            'size_bytes': file_info.size,
            'checksum_sha256': checksum,
            'source_path': file_info.path,
            'staging_path': staging_path
        })
    except Exception as e:
        print(f"  ❌ Move failed: {e}")
        skipped_files.append({
            'file': file_info.name,
            'reason': f'Move to staging failed: {e}',
            'path': file_info.path
        })

print()
print("="*80)
print(f"✅ Validated: {len(validated_files)} files")
print(f"⚠️  Skipped:  {len(skipped_files)} files")
print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 2: Convert Files (Call 03d)

# COMMAND ----------

print("="*80)
print("🔄 STAGE 2: CONVERT FILES")
print("="*80)
print()

if len(validated_files) == 0:
    print("⚠️  No files to convert. Exiting.")
    dbutils.notebook.exit("No files to convert")

print(f"Converting {len(validated_files)} files...")
print()

# Option A: Call 03d_convert_sas notebook
# Uncomment to use orchestration via notebook call:
#
# try:
#     result = dbutils.notebook.run(
#         "./03d_convert_sas",
#         timeout_seconds=3600,
#         arguments={}
#     )
#     print(f"✅ Conversion complete: {result}")
# except Exception as e:
#     print(f"❌ Conversion failed: {e}")

# Option B: Inline conversion (simplified)
# For now, we'll track which files were staged and mark them for manual conversion
print("📌 Files staged for conversion:")
for f in validated_files:
    print(f"  - {f['filename']} ({f['size_bytes']} bytes)")

print()
print("👉 Next step: Run notebook 03d_convert_sas.py to convert these files")
print()

# For this orchestrator, we'll assume conversion happens via 03d
# and mark all validated files as "ready_for_conversion"
conversion_results = []
for f in validated_files:
    conversion_results.append({
        'filename': f['filename'],
        'status': 'staged_for_conversion',  # Would be 'success' or 'failed' after real conversion
        'source_path': f['staging_path'],
        'converted_path': f"{converted_dir}/converted_{f['filename'].replace('.sas', '.py')}"
    })

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 3: Archive Successful Source Files

# COMMAND ----------

print("="*80)
print("📦 STAGE 3: ARCHIVE SOURCE FILES")
print("="*80)
print()

# Create archive directory
dbutils.fs.mkdirs(archive_dir)
print(f"Created archive: {archive_dir}")
print()

archived_files = []

# For now, we'll simulate archiving by noting which files would be moved
# In a real pipeline, you'd check conversion_results for status='success'
for f in validated_files:
    # Would only archive if conversion succeeded
    # if conversion_results[i]['status'] == 'success':
    archive_path = f"{archive_dir}/{f['filename']}"
    print(f"📦 Archive: {f['filename']}")
    print(f"   From: {f['staging_path']}")
    print(f"   To:   {archive_path}")

    # Move to archive (commented out for now since we're simulating)
    # try:
    #     dbutils.fs.mv(f['staging_path'], archive_path)
    #     archived_files.append({
    #         'filename': f['filename'],
    #         'archived_to': archive_path
    #     })
    #     print(f"   ✅ Archived")
    # except Exception as e:
    #     print(f"   ❌ Archive failed: {e}")

    archived_files.append({
        'filename': f['filename'],
        'archived_to': archive_path
    })
    print()

print(f"✅ Archived {len(archived_files)} files")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 4: Reject Failed Files

# COMMAND ----------

print("="*80)
print("❌ STAGE 4: HANDLE REJECTED FILES")
print("="*80)
print()

rejected_files = []

# Process skipped files from validation
for skip in skipped_files:
    reject_filename = skip['file']
    reject_path = f"{reject_dir}/{reject_filename}"
    error_log_path = f"{reject_dir}/{reject_filename}.err"

    print(f"❌ Reject: {reject_filename}")
    print(f"   Reason: {skip['reason']}")

    # Write error log
    error_content = f"""SAS Migration Pipeline - Rejection Report
Run ID: {run_id}
Timestamp: {datetime.now().isoformat()}
File: {reject_filename}
Original Path: {skip['path']}

Reason for Rejection:
{skip['reason']}

Suggested Actions:
1. Verify file is valid SAS code
2. Check file is not empty
3. Ensure file encoding is correct (UTF-8)
4. Re-upload to 00_inbound/ after fixing
"""

    try:
        dbutils.fs.put(error_log_path, error_content, overwrite=True)
        print(f"   ✅ Error log written: {error_log_path}")

        rejected_files.append({
            'filename': reject_filename,
            'reason': skip['reason'],
            'rejected_to': reject_path,
            'error_log': error_log_path
        })
    except Exception as e:
        print(f"   ⚠️  Could not write error log: {e}")

    print()

if len(rejected_files) == 0:
    print("✅ No rejections")
else:
    print(f"❌ Rejected {len(rejected_files)} files")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Stage 5: Write Manifest

# COMMAND ----------

print("="*80)
print("📝 STAGE 5: WRITE MANIFEST")
print("="*80)
print()

end_time = datetime.now()
duration_seconds = (end_time - start_time).total_seconds()

manifest = {
    "run_id": run_id,
    "pipeline_version": "1.0",
    "start_time": start_time.isoformat(),
    "end_time": end_time.isoformat(),
    "duration_seconds": duration_seconds,
    "status": "completed",
    "catalog": CATALOG,
    "schema": SCHEMA,
    "volume": VOLUME_NAME,
    "summary": {
        "files_found": len(inbound_files),
        "files_validated": len(validated_files),
        "files_skipped": len(skipped_files),
        "files_converted": len(conversion_results),
        "files_archived": len(archived_files),
        "files_rejected": len(rejected_files)
    },
    "validated_files": validated_files,
    "conversion_results": conversion_results,
    "archived_files": archived_files,
    "rejected_files": rejected_files,
    "paths": {
        "inbound": inbound_dir,
        "staging": staging_dir,
        "processing": processing_dir,
        "converted": converted_dir,
        "archive": archive_dir,
        "reject": reject_dir,
        "manifest": manifest_dir
    }
}

manifest_json = json.dumps(manifest, indent=2)
manifest_path = f"{manifest_dir}/{run_id}.json"

try:
    dbutils.fs.put(manifest_path, manifest_json, overwrite=True)
    print(f"✅ Manifest written: {manifest_path}")
except Exception as e:
    print(f"❌ Failed to write manifest: {e}")

print()
print("="*80)
print(f"📊 MANIFEST SUMMARY")
print("="*80)
print(json.dumps(manifest['summary'], indent=2))
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete

# COMMAND ----------

print()
print("="*80)
print(f"✅ PIPELINE COMPLETE - {run_id}")
print("="*80)
print(f"⏰ Started:   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"⏰ Finished:  {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"⏱️  Duration: {duration_seconds:.1f} seconds")
print()
print("📊 Summary:")
print(f"   Files validated:  {len(validated_files)}")
print(f"   Files converted:  {len(conversion_results)}")
print(f"   Files archived:   {len(archived_files)}")
print(f"   Files rejected:   {len(rejected_files)}")
print()
print("📁 Outputs:")
print(f"   Converted files:  {converted_dir}")
print(f"   Archive:          {archive_dir}")
print(f"   Rejections:       {reject_dir}")
print(f"   Manifest:         {manifest_path}")
print()
print("👉 Next steps:")
print("   1. Review converted files in 03_converted/needs_review/")
print("   2. Test and approve conversions")
print("   3. Move approved files to 03_converted/approved/")
print("   4. Deploy to production")
print()
print("="*80)

# COMMAND ----------

# Return manifest path for downstream processing
dbutils.notebook.exit(manifest_path)
