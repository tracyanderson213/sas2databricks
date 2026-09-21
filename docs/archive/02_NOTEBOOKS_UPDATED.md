# 02 Notebooks Updated for New Structure

## ✅ What's Been Updated

### **1. New Simple Upload Notebook** ✨
**File:** `notebooks/02_upload_sas_files.py`

**Purpose:** Clean, simple SAS file upload to `00_inbound/manual_uploads/`

**Features:**
- ✅ Uploads to new structure (`00_inbound/`)
- ✅ Three examples included:
  1. Simple SELECT
  2. PROC FORMAT + DATALINES
  3. Comprehensive claims adjudication
- ✅ No config.yaml clutter
- ✅ Clear next steps

**Use this as your main upload notebook** - it's simpler and cleaner.

---

### **2. Updated Comprehensive Claims Upload** ✅
**File:** `notebooks/02b_upload_comprehensive_claims.py`

**Changes:**
- ✅ Uploads to `00_inbound/manual_uploads/` (not `input/`)
- ✅ Removed config.yaml (not needed in new structure)
- ✅ Removed metadata folder (simplified)
- ✅ Updated next steps to reference orchestration

**Still includes:**
- Full 180-line claims adjudication SAS program
- All 10 major SAS features

---

### **3. Cleanup Script** ✨ NEW
**File:** `notebooks/99_cleanup_old_volumes.py`

**What it does:**
1. **Survey** - Lists all old folders (`input/`, `staging/`, `approved/`, etc.)
2. **Backup** - Copies to `_backup_TIMESTAMP/` (optional)
3. **Delete** - Removes old folders (requires manual confirmation)
4. **Verify** - Confirms new structure exists
5. **Report** - Writes summary JSON

**Safety features:**
- ✅ Requires `CONFIRM_DELETE = True` to actually delete
- ✅ Optional backup before deletion
- ✅ Detailed report of what's being removed
- ✅ Verifies new structure exists

---

## 📦 All Updated Notebooks

```
notebooks/
├── 00_orchestrate_conversion_pipeline.py  (12K)  ✨ NEW
├── 01_setup_volumes.py                    (7.7K) ✅ Updated
├── 02_upload_sas_files.py                 (8.3K) ✨ NEW - Use this!
├── 02b_upload_comprehensive_claims.py     (17K)  ✅ Updated
├── 03d_convert_sas.py                     (25K)  ✅ Updated
└── 99_cleanup_old_volumes.py              (14K)  ✨ NEW
```

---

## 🚀 Recommended Workflow

### **Step 1: Clean Up Old Structure**
```python
# Run 99_cleanup_old_volumes.py
# 1. Survey old folders
# 2. Create backup (optional)
# 3. Set CONFIRM_DELETE = True
# 4. Run again to delete
```

### **Step 2: Create New Structure**
```python
# Run 01_setup_volumes.py
# Creates 00_inbound/ → 06_logs_manifest/
```

### **Step 3: Upload SAS Files**
```python
# Run 02_upload_sas_files.py
# Uploads examples to 00_inbound/manual_uploads/
```

**OR manually upload:**
```bash
# Upload your SAS files to:
/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/00_inbound/manual_uploads/
```

### **Step 4: Run Pipeline**
```python
# Option A (Recommended):
# Run 00_orchestrate_conversion_pipeline.py
# → Full pipeline with validation, conversion, archiving, manifest

# Option B (Direct):
# Run 03d_convert_sas.py
# → Just conversion, no orchestration
```

---

## 🗑️ Using the Cleanup Script

### **Safe Mode (Survey Only):**
```python
# Default settings in 99_cleanup_old_volumes.py:
CONFIRM_DELETE = False  # ← Blocked, won't delete
CREATE_BACKUP = True    # ← Will backup
```

Run the notebook → it will:
- ✅ List all old folders
- ✅ Show file counts and sizes
- ✅ Create backup
- ❌ NOT delete (blocked)

### **Delete Mode:**
```python
# Update settings:
CONFIRM_DELETE = True   # ← Will actually delete
CREATE_BACKUP = True    # ← Backup first (recommended)
```

Run again → it will:
- ✅ Create backup to `_backup_TIMESTAMP/`
- ✅ Delete old folders
- ✅ Verify cleanup
- ✅ Write summary JSON

---

## 📋 What Gets Cleaned Up

| Old Folder | What's In It | Action |
|------------|--------------|--------|
| `input/` | Old SAS project uploads | Backed up + deleted |
| `staging/` | Old conversion output | Backed up + deleted |
| `approved/` | Old vetted code | Backed up + deleted |
| `metadata_registry/` | Old data dictionaries | Backed up + deleted |
| `archive/` | Old backups | Backed up + deleted |

**New structure takes over:**
```
00_inbound/       ← replaces input/
01_staging/       ← replaces staging/ (with validation)
03_converted/     ← replaces staging/ (with quality gates)
04_archive/       ← replaces archive/ (with date partitioning)
```

---

## 🎯 Key Differences: Old vs New

### **Old Structure:**
```
input/
└── project_name/
    ├── config.yaml    ← needed
    ├── sas/
    │   └── *.sas
    └── metadata/
        └── *.csv

staging/
└── project_name/
    └── converted_files.py
```

### **New Structure:**
```
00_inbound/
└── manual_uploads/
    └── *.sas          ← just drop SAS files!

03_converted/
├── needs_review/      ← quality gate
│   └── converted_*.py
├── approved/          ← human-reviewed
└── deployed/          ← actually deployed
```

**Simpler:** No config.yaml, no project folders, just drop SAS files!

---

## 💾 Backup Location

If `CREATE_BACKUP = True`, backup goes to:
```
/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/_backup_YYYYMMDD_HHMMSS/
├── input/
├── staging/
├── approved/
├── metadata_registry/
├── archive/
└── cleanup_summary.json  ← audit trail
```

**Keep this for 30+ days** in case you need to recover something.

---

## ⚠️ Important Notes

1. **Run 01 first** - Create new structure before cleaning old
2. **Review before deleting** - Check survey output carefully
3. **Backup recommended** - Set `CREATE_BACKUP = True` (default)
4. **Manual confirmation required** - Set `CONFIRM_DELETE = True`
5. **Audit trail** - `cleanup_summary.json` records what was done

---

## 🎯 Summary

**5 notebooks ready to upload:**
1. ✅ `01_setup_volumes.py` - Production structure
2. ✅ `02_upload_sas_files.py` - Simple upload (recommended)
3. ✅ `02b_upload_comprehensive_claims.py` - Updated for new structure
4. ✅ `03d_convert_sas.py` - View transformation working
5. ✅ `00_orchestrate_conversion_pipeline.py` - Full pipeline
6. ✅ `99_cleanup_old_volumes.py` - Safe cleanup with backup

**Workflow:**
```
99 (cleanup) → 01 (setup) → 02 (upload) → 00 or 03d (convert)
```

**All set!** 🚀
