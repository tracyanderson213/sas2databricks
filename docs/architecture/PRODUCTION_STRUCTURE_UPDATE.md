# Production Structure Update - Ready to Upload

## ✅ What's Been Updated

### **1. Notebook 01 - Setup Volumes** ✅
**File:** `notebooks/01_setup_volumes.py`

**New structure:**
```
/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/
├── 00_inbound/                    ← Drop zone (read-only after write)
│   ├── claims_mainframe/
│   └── manual_uploads/
├── 01_staging/                    ← Validated, ready for conversion
├── 02_processing/                 ← In-flight (crash recovery)
├── 03_converted/                  ← Conversion output
│   ├── needs_review/              ← Quality gate
│   ├── approved/                  ← Human-reviewed
│   └── deployed/                  ← Actually deployed
├── 04_archive/                    ← Source files (date-partitioned)
├── 05_reject/                     ← Failed + .err logs
└── 06_logs_manifest/              ← Run metadata, audit trail
```

**Run this first** to create the new structure.

---

### **2. Notebook 03d - Convert SAS** ✅
**File:** `notebooks/03d_convert_sas.py` (renamed from `03d_intelligent_conversion.py`)

**Updates:**
- ✅ Renamed for clarity
- ✅ Updated paths to use new structure:
  - Input: `01_staging/` (validated files)
  - Output: `03_converted/needs_review/` (quality gate)
- ✅ **View transformation working** - replaces `@dlt.table` with `@dlt.view` for intermediate tables
- ✅ **Layer detection improved** - smarter Bronze/Silver/Gold detection
- ✅ All features from before still work (widgets, production template, etc.)

---

### **3. Notebook 00 - Orchestration** ✨ NEW
**File:** `notebooks/00_orchestrate_conversion_pipeline.py`

**What it does:**
1. **Validate** - Scans `00_inbound/`, validates files, moves to `01_staging/`
2. **Convert** - Calls `03d_convert_sas.py` (or inline conversion)
3. **Archive** - Moves successful source files to `04_archive/YYYY/MM/DD/run_XXXXX/`
4. **Reject** - Moves failed files to `05_reject/` with `.err` logs
5. **Manifest** - Writes run metadata to `06_logs_manifest/run_XXXXX.json`

**Manifest includes:**
- Run ID, timestamps, duration
- File checksums (SHA256)
- Success/failure counts
- Full lineage (source → staging → converted → archive)

---

## 🚀 How to Use

### **Step 1: Upload Notebooks**

Upload these 3 notebooks to Databricks:
1. `notebooks/01_setup_volumes.py`
2. `notebooks/03d_convert_sas.py`
3. `notebooks/00_orchestrate_conversion_pipeline.py`

---

### **Step 2: Run 01 to Create Structure**

```python
# Run notebook 01_setup_volumes.py
# This creates all the folders
```

You said you'll **manually clean up old volumes** first - good plan.

---

### **Step 3: Upload SAS Files**

Upload your SAS files to:
```
/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/00_inbound/
```

Or to specific subfolders:
```
00_inbound/claims_mainframe/claims_adjudication_comprehensive.sas
00_inbound/manual_uploads/eligibility_validation.sas
```

---

### **Step 4: Run Orchestration (Option A)**

```python
# Run notebook 00_orchestrate_conversion_pipeline.py
# This will:
# 1. Validate files in 00_inbound → move to 01_staging
# 2. Call 03d to convert
# 3. Archive successful files
# 4. Reject failed files with .err logs
# 5. Write manifest
```

---

### **Step 5: Run Conversion Directly (Option B)**

If you just want to convert without the full pipeline:

```python
# Run notebook 03d_convert_sas.py
# This reads from 01_staging/ and writes to 03_converted/needs_review/
```

---

## 📋 Naming Convention

We're using **letter suffixes** for iterations:
- ✅ `03d_convert_sas.py` (current)
- Next: `03e_whatever.py`
- Then: `03f_whatever.py`

Clean, simple progression.

---

## 🎯 Key Benefits

| Feature | Benefit |
|---------|---------|
| **00_inbound/** | Read-only drop zone, never modify source |
| **01_staging/** | Validated files, ready for processing |
| **02_processing/** | In-flight tracking, crash recovery |
| **03_converted/** | Quality gates (needs_review → approved → deployed) |
| **04_archive/** | Date-partitioned, 7+ year retention |
| **05_reject/** | Audit trail for failures with .err logs |
| **06_logs_manifest/** | Full lineage, checksums, compliance |

---

## 🔧 What's Fixed in 03d

### **Problem:** `@dlt.table` everywhere
**Before:**
```python
@dlt.table(name='work_claims_elig')  # Intermediate table
@dlt.table(name='sort_raw')          # Just sorting
@dlt.table(name='clm_claims_adjudicated')  # Final output
```

**After (now working):**
```python
@dlt.view(name='work_claims_elig')   # ✅ View (intermediate)
@dlt.view(name='sort_raw')           # ✅ View (just sorting)
@dlt.table(name='clm_claims_adjudicated')  # ✅ Table (final output)
```

### **View Detection Logic:**

| Table Name | Type | Reason |
|------------|------|--------|
| `sort_raw` | VIEW | Just sorting |
| `work_claims_elig`, `work_claims_elig2` | VIEW | Intermediate join |
| `work_claims_network`, `work_claims_benefit` | VIEW | Intermediate join |
| `work_claims_dupflag` | VIEW | Intermediate flag |
| `work_members`, `work_providers` | TABLE | Bronze reference data |
| `work_claims_running` | TABLE | RETAIN logic (stateful) |
| `clm_claims_adjudicated`, `result` | TABLE | Final gold outputs |

### **Layer Detection Logic:**

| Table Name | Layer | Schema |
|------------|-------|--------|
| `fmt_diagcat`, `work_members`, `work_providers` | **Bronze** | sas2dbx_migrate |
| `work_claims_elig`, `work_claims_network` | **Silver** | sas2dbx_migrate |
| `clm_claims_adjudicated`, `result` | **Gold** | sas2dbx_migrate |

(All default to same schema for now, but widget-driven for prod)

---

## 📊 Manifest Example

After orchestration, you get:

**File:** `06_logs_manifest/run_a3f8b2c1.json`
```json
{
  "run_id": "run_a3f8b2c1",
  "start_time": "2026-09-17T14:32:15Z",
  "end_time": "2026-09-17T14:35:42Z",
  "duration_seconds": 207.5,
  "status": "completed",
  "summary": {
    "files_validated": 3,
    "files_converted": 3,
    "files_archived": 3,
    "files_rejected": 0
  },
  "validated_files": [
    {
      "filename": "claims_adjudication_comprehensive.sas",
      "checksum_sha256": "a3f8b2...",
      "source_path": "00_inbound/claims_mainframe/claims_adj.sas",
      "staging_path": "01_staging/claims_adj.sas"
    }
  ],
  "archived_files": [
    {
      "filename": "claims_adjudication_comprehensive.sas",
      "archived_to": "04_archive/2026/09/17/run_a3f8b2c1/claims_adj.sas"
    }
  ]
}
```

**Perfect for compliance audits!** ✅

---

## 🎯 Summary

**Three files updated:**
1. ✅ `01_setup_volumes.py` - Production folder structure
2. ✅ `03d_convert_sas.py` - View transformation working, new paths
3. ✅ `00_orchestrate_conversion_pipeline.py` - Full pipeline orchestration

**Your action:**
1. Manual cleanup old volumes
2. Upload these 3 notebooks
3. Run 01 to create structure
4. Upload SAS files to 00_inbound/
5. Run 00 or 03d to convert

**Ready to go!** 🚀
