# Databricks notebook source
# MAGIC %md
# MAGIC # 99 - Cleanup Old Volume Structure
# MAGIC
# MAGIC **Purpose:** Clean up old folder structure and migrate to new production structure
# MAGIC
# MAGIC **What this does:**
# MAGIC 1. Lists old folders (`input/`, `staging/`, `approved/`, etc.)
# MAGIC 2. Optionally backs up to `_backup_TIMESTAMP/`
# MAGIC 3. Deletes old folders
# MAGIC 4. Confirms cleanup complete
# MAGIC
# MAGIC **⚠️  WARNING:** This will delete old data. Review carefully before running!
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Run `01_setup_volumes.py` to create NEW structure first
# MAGIC - ✅ Backup important data manually if needed

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

from datetime import datetime
import json

# Volume paths
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"
VOLUME_NAME = "sas_migration"
volume_base = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}"

# Old folders to clean up
old_folders = [
    "input",
    "staging",
    "approved",
    "metadata_registry",
    "archive"
]

# Backup settings
CREATE_BACKUP = True  # Set to False to skip backup
backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f"{volume_base}/_backup_{backup_timestamp}"

print("="*80)
print("🧹 CLEANUP OLD VOLUME STRUCTURE")
print("="*80)
print(f"📁 Volume base: {volume_base}")
print(f"⚠️  Will clean:  {', '.join(old_folders)}")
print(f"💾 Backup to:   {backup_dir if CREATE_BACKUP else 'No backup'}")
print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Survey Existing Folders

# COMMAND ----------

print("="*80)
print("📊 STEP 1: SURVEY EXISTING FOLDERS")
print("="*80)
print()

existing_folders = []
folder_sizes = {}

for folder in old_folders:
    folder_path = f"{volume_base}/{folder}"
    try:
        # Check if folder exists
        files = dbutils.fs.ls(folder_path)
        file_count = len(files)

        # Calculate approximate size
        total_size = 0
        for f in files:
            if not f.isDir():
                total_size += f.size

        existing_folders.append(folder)
        folder_sizes[folder] = {
            'file_count': file_count,
            'size_bytes': total_size,
            'size_mb': total_size / (1024 * 1024)
        }

        print(f"✅ {folder:20} - {file_count:3} items, {folder_sizes[folder]['size_mb']:.2f} MB")

    except Exception as e:
        print(f"⚪ {folder:20} - Not found or empty")

print()
print(f"Found {len(existing_folders)} old folders to clean")
print()

if len(existing_folders) == 0:
    print("✅ No old folders found. Already clean!")
    dbutils.notebook.exit("No cleanup needed")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: List Files in Each Folder

# COMMAND ----------

print("="*80)
print("📋 STEP 2: LIST FILES IN OLD FOLDERS")
print("="*80)
print()

folder_contents = {}

for folder in existing_folders:
    folder_path = f"{volume_base}/{folder}"
    print(f"\n📂 {folder}/")
    print("-" * 80)

    try:
        files = dbutils.fs.ls(folder_path)
        folder_contents[folder] = []

        for f in files[:20]:  # Show first 20 items
            if f.isDir():
                print(f"  📁 {f.name}")
            else:
                size_kb = f.size / 1024
                print(f"  📄 {f.name:50} ({size_kb:>8.1f} KB)")
            folder_contents[folder].append(f.path)

        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more items")

    except Exception as e:
        print(f"  ⚠️  Error listing: {e}")

print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create Backup (Optional)

# COMMAND ----------

if CREATE_BACKUP and len(existing_folders) > 0:
    print("="*80)
    print("💾 STEP 3: CREATE BACKUP")
    print("="*80)
    print()

    print(f"Creating backup in: {backup_dir}")
    dbutils.fs.mkdirs(backup_dir)

    backed_up = []
    backup_failed = []

    for folder in existing_folders:
        source_path = f"{volume_base}/{folder}"
        backup_path = f"{backup_dir}/{folder}"

        print(f"Backing up: {folder}/")

        try:
            # Copy folder to backup
            dbutils.fs.cp(source_path, backup_path, recurse=True)
            backed_up.append(folder)
            print(f"  ✅ Backed up to {backup_path}")

        except Exception as e:
            backup_failed.append((folder, str(e)))
            print(f"  ❌ Backup failed: {e}")

    print()
    print(f"✅ Backed up {len(backed_up)} folders")

    if len(backup_failed) > 0:
        print(f"❌ Failed to backup {len(backup_failed)} folders:")
        for folder, error in backup_failed:
            print(f"   - {folder}: {error}")

    print()
    print("="*80)

else:
    print("="*80)
    print("⚪ STEP 3: BACKUP SKIPPED")
    print("="*80)
    print()
    print("CREATE_BACKUP is False - skipping backup")
    print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Delete Old Folders

# COMMAND ----------

print("="*80)
print("🗑️  STEP 4: DELETE OLD FOLDERS")
print("="*80)
print()
print("⚠️  WARNING: This will permanently delete the old folders!")
print()

# Safety check - require manual confirmation
CONFIRM_DELETE = False  # Set to True to actually delete

if not CONFIRM_DELETE:
    print("❌ DELETION BLOCKED")
    print()
    print("To actually delete, set CONFIRM_DELETE = True in this cell")
    print("Review the survey and backup steps above first!")
    print()
    dbutils.notebook.exit("Deletion blocked - set CONFIRM_DELETE = True")

print("🚨 CONFIRM_DELETE is True - proceeding with deletion...")
print()

deleted = []
delete_failed = []

for folder in existing_folders:
    folder_path = f"{volume_base}/{folder}"

    print(f"Deleting: {folder}/")

    try:
        dbutils.fs.rm(folder_path, recurse=True)
        deleted.append(folder)
        print(f"  ✅ Deleted")

    except Exception as e:
        delete_failed.append((folder, str(e)))
        print(f"  ❌ Delete failed: {e}")

print()
print("="*80)
print(f"✅ Deleted {len(deleted)} folders")

if len(delete_failed) > 0:
    print(f"❌ Failed to delete {len(delete_failed)} folders:")
    for folder, error in delete_failed:
        print(f"   - {folder}: {error}")

print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Verify Cleanup

# COMMAND ----------

print("="*80)
print("✅ STEP 5: VERIFY CLEANUP")
print("="*80)
print()

print("Checking for old folders...")
print()

remaining = []
for folder in old_folders:
    folder_path = f"{volume_base}/{folder}"
    try:
        dbutils.fs.ls(folder_path)
        remaining.append(folder)
        print(f"⚠️  Still exists: {folder}/")
    except:
        print(f"✅ Removed: {folder}/")

print()
print("="*80)

if len(remaining) == 0:
    print("✅ ALL OLD FOLDERS REMOVED!")
else:
    print(f"⚠️  {len(remaining)} folders still exist:")
    for folder in remaining:
        print(f"   - {folder}/")

print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Verify New Structure Exists

# COMMAND ----------

print("="*80)
print("📊 STEP 6: VERIFY NEW STRUCTURE")
print("="*80)
print()

# New folders that should exist
new_folders = [
    "00_inbound",
    "01_staging",
    "02_processing",
    "03_converted",
    "04_archive",
    "05_reject",
    "06_logs_manifest"
]

print("Checking new production structure...")
print()

missing_new = []
for folder in new_folders:
    folder_path = f"{volume_base}/{folder}"
    try:
        dbutils.fs.ls(folder_path)
        print(f"✅ {folder}/")
    except:
        missing_new.append(folder)
        print(f"❌ MISSING: {folder}/")

print()
print("="*80)

if len(missing_new) == 0:
    print("✅ NEW STRUCTURE COMPLETE!")
else:
    print(f"⚠️  {len(missing_new)} folders missing:")
    for folder in missing_new:
        print(f"   - {folder}/")
    print()
    print("👉 Run notebook 01_setup_volumes.py to create new structure")

print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Report

# COMMAND ----------

print("="*80)
print("📊 CLEANUP SUMMARY REPORT")
print("="*80)
print()

summary = {
    "cleanup_timestamp": datetime.now().isoformat(),
    "volume": f"{CATALOG}.{SCHEMA}.{VOLUME_NAME}",
    "old_folders_found": len(existing_folders),
    "old_folders_deleted": len(deleted) if CONFIRM_DELETE else 0,
    "backup_created": CREATE_BACKUP,
    "backup_location": backup_dir if CREATE_BACKUP else None,
    "new_structure_complete": len(missing_new) == 0,
    "status": "COMPLETE" if (len(remaining) == 0 and len(missing_new) == 0) else "INCOMPLETE"
}

print(json.dumps(summary, indent=2))
print()

# Write summary to manifest
if CREATE_BACKUP:
    summary_path = f"{backup_dir}/cleanup_summary.json"
    dbutils.fs.put(summary_path, json.dumps(summary, indent=2), overwrite=True)
    print(f"📝 Summary written to: {summary_path}")
    print()

print("="*80)
print()

if summary["status"] == "COMPLETE":
    print("✅ CLEANUP COMPLETE!")
    print()
    print("👉 Next steps:")
    print("   1. Upload SAS files to 00_inbound/")
    print("   2. Run 00_orchestrate_conversion_pipeline.py")
else:
    print("⚠️  CLEANUP INCOMPLETE")
    print()
    print("Review the report above and:")
    if not CONFIRM_DELETE:
        print("   - Set CONFIRM_DELETE = True to actually delete")
    if len(remaining) > 0:
        print("   - Manually remove remaining folders")
    if len(missing_new) > 0:
        print("   - Run 01_setup_volumes.py to create new structure")

print()
print("="*80)

# COMMAND ----------

# Return summary
dbutils.notebook.exit(json.dumps(summary))
