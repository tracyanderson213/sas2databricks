# 📦 File Archival Feature

## Overview

Added automatic archival of successfully processed files to prevent reprocessing on subsequent runs.

---

## How It Works

### **Folder Structure:**
```
/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration/
├── 01_staging/              ← Input files (SAS programs)
├── 02_processing/           ← Lock mechanism (files being processed)
├── 03_converted/            ← Output files (converted PySpark)
│   └── needs_review/
└── 04_archive/              ← Successfully processed files (NEW!)
```

### **Workflow:**
1. **Place files** in `01_staging/`
2. **Run converter** - processes files
3. **On success:**
   - If `ARCHIVE_ON_SUCCESS = True`: Move file from `01_staging/` → `04_archive/`
   - If `ARCHIVE_ON_SUCCESS = False`: Leave file in `01_staging/` (for testing)

---

## Configuration

### **Enable/Disable Archival:**

Located at **Line ~1683** in `notebooks/03_convert_sas.py`:

```python
# ==============================================================================
# ARCHIVE ON SUCCESS - Move processed files to prevent reprocessing
# ==============================================================================
# Set to True to enable archival (disabled for testing)
# When enabled: successfully converted files are moved to 04_archive/
# This prevents reprocessing the same file on subsequent runs
ARCHIVE_ON_SUCCESS = False  # ← Set to True in production
# ==============================================================================
```

**For testing:** Keep `ARCHIVE_ON_SUCCESS = False`
- Files remain in `01_staging/`
- Can re-run conversion on same files
- Safe for iterative development

**For production:** Set `ARCHIVE_ON_SUCCESS = True`
- Successfully processed files automatically move to `04_archive/`
- Prevents accidental reprocessing
- Clean separation of processed vs pending files

---

## What Happens During Conversion

### **When ARCHIVE_ON_SUCCESS = False (Testing Mode):**
```
📊 CONVERSION SUMMARY
Total files:     1
✅ Successful:   1
❌ Failed:       0

📦 Archival:     DISABLED (testing mode) - Files remain in 01_staging/
   → Set ARCHIVE_ON_SUCCESS = True to enable archival in production

✅ SUCCESSFUL CONVERSIONS (with intelligent enhancements + bug fixes)
📄 claims_adjudication_comprehensive.sas
   → converted_claims_adjudication_comprehensive.py
   Status: ✅ success
```

File stays in `01_staging/` for reprocessing.

---

### **When ARCHIVE_ON_SUCCESS = True (Production Mode):**
```
📄 Input:  claims_adjudication_comprehensive.sas
📄 Output: converted_claims_adjudication_comprehensive.py
✨ Enhanced with:
   - Intelligent layer detection (Bronze/Silver/Gold)
   - Three schema variables
   - View optimization for intermediate tables
   - Bronze metadata helper
   - ✅ ALL 5 BUG FIXES APPLIED

📦 Archived: claims_adjudication_comprehensive.sas → 04_archive/

---

📊 CONVERSION SUMMARY
Total files:     1
✅ Successful:   1
❌ Failed:       0

📦 Archival:     ENABLED - Successful files moved to 04_archive/
```

File moved from `01_staging/` to `04_archive/`.

---

## Error Handling

If archival fails (e.g., permission issue, disk full):
```python
⚠️  Failed to archive claims_adjudication_comprehensive.sas: [error message]
   File will remain in 01_staging/
```

Conversion still succeeds - archival failure is non-fatal.

---

## Implementation Details

### **Added Imports:**
```python
import shutil  # For moving files
```

### **Added Configuration:**
```python
archive_dir = f"{volume_base}/04_archive"
ARCHIVE_ON_SUCCESS = False
```

### **Archival Logic (after successful conversion):**
```python
if ARCHIVE_ON_SUCCESS:
    try:
        # Ensure archive directory exists
        os.makedirs(archive_dir, exist_ok=True)

        # Source and destination paths
        source_path = os.path.join(input_base, sas_file['filename'])
        archive_path = os.path.join(archive_dir, sas_file['filename'])

        # Move file to archive
        shutil.move(source_path, archive_path)
        print(f"📦 Archived: {sas_file['filename']} → 04_archive/")

    except Exception as e:
        print(f"⚠️  Failed to archive {sas_file['filename']}: {e}")
        print(f"   File will remain in 01_staging/")
```

---

## Benefits

### **Testing:**
- ✅ Leave archival disabled (`False`)
- ✅ Re-run same files multiple times
- ✅ Fast iteration on converter improvements

### **Production:**
- ✅ Enable archival (`True`)
- ✅ Prevents accidental reprocessing
- ✅ Clean audit trail (archived files = processed files)
- ✅ Easy to track what's been converted

---

## Restoring Files

If you need to reprocess an archived file:

```bash
# In Databricks notebook:
dbutils.fs.mv(
    "dbfs:/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration/04_archive/myfile.sas",
    "dbfs:/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration/01_staging/myfile.sas"
)
```

Or use the Catalog Explorer UI to move files between folders.

---

## Files Modified

- **`notebooks/03_convert_sas.py`** - 4 changes:
  1. Line ~83: Added `import shutil`
  2. Line ~1665: Added `import shutil` (after restart)
  3. Line ~1678-1683: Added `ARCHIVE_ON_SUCCESS` flag and `archive_dir` path
  4. Line ~1905-1922: Added archival logic after successful conversion
  5. Line ~1975-1980: Added archival status to summary report

---

## Recommendation

**Start with archival disabled** (current state) until you're satisfied with conversion quality, then enable it for production runs.

To enable:
1. Open `notebooks/03_convert_sas.py`
2. Find line ~1683
3. Change: `ARCHIVE_ON_SUCCESS = False` → `ARCHIVE_ON_SUCCESS = True`
4. Upload to Databricks
5. Run converter

---

## Ready to Test! 🚀

Current state: **Archival DISABLED** (safe for testing)

Upload the notebook and run - files will stay in `01_staging/` for reprocessing.
