# File Naming Fix - Preserve Original SAS Filenames

## 🎯 The Problem You Discovered

**Input:** `claims_adjudication_comprehensive.sas`  
**Expected:** `claims_adjudication_comprehensive.py`  
**What you got:** `dlt_pipeline.py` ❌

### Why This Happened

The `sas2databricks` package's `migrate()` function returns `result.filename = "dlt_pipeline.py"` (a generic name) instead of preserving your original SAS filename.

**Impact:**
- ❌ All conversions create `dlt_pipeline.py` → overwrite each other
- ❌ No traceability back to original SAS file
- ❌ Can't tell which Python file came from which SAS file

---

## ✅ The Fix

### **Updated Notebook 03**

**BEFORE (Wrong):**
```python
result = migrate(sas_text, ...)

# Uses generic filename from sas2databricks
output_file = f"{staging_dir}/{result.filename}"  # ← Returns "dlt_pipeline.py"
```

**AFTER (Fixed):**
```python
sas_filename = "claims_adjudication_comprehensive.sas"
result = migrate(sas_text, source_path=sas_filename, ...)

# Preserve original filename (ignore result.filename)
output_basename = sas_filename.replace('.sas', '.py')  # ← "claims_adjudication_comprehensive.py"
output_file = f"{staging_dir}/{output_basename}"
```

---

## 📁 Expected Output Structure

### **After Fix:**

```
staging/
├── test_simple_sql/
│   └── simple_select.py              ← Matches: simple_select.sas
│
├── test_format_data/
│   └── format_cars.py                ← Matches: format_cars.sas
│
├── test_select_when/
│   └── car_origin.py                 ← Matches: car_origin.sas
│
└── comprehensive_claims_adjudication/
    └── claims_adjudication_comprehensive.py  ← Matches: claims_adjudication_comprehensive.sas
```

**Perfect 1:1 traceability!** ✅

---

## 🔧 What You Need to Do

### **Option 1: Re-run with Fixed Notebook (Recommended)**

1. **Re-import** the updated `03_test_conversion.py` to Databricks
2. **Re-run** the notebook
3. **Check output** - filenames should now match!

**Expected result:**
```
Input:  claims_adjudication_comprehensive.sas
Output: claims_adjudication_comprehensive.py  ← Matches!
```

---

### **Option 2: Check Your Current Output**

Import and run `notebooks/03a_check_output.py` to diagnose what you currently have:

```python
# This notebook will:
1. List all files in staging/
2. Show if they're all named "dlt_pipeline.py"
3. Check for original SAS filename references
4. Provide diagnosis and recommendations
```

---

### **Option 3: Manually Rename Files (Quick Fix)**

If you don't want to re-run, manually rename the files in Databricks:

**In a Databricks notebook:**
```python
import os

# Rename in staging/comprehensive_claims_adjudication/
old_path = "/dbfs/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/comprehensive_claims_adjudication/dlt_pipeline.py"
new_path = "/dbfs/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/comprehensive_claims_adjudication/claims_adjudication_comprehensive.py"

if os.path.exists(old_path):
    os.rename(old_path, new_path)
    print(f"✅ Renamed to: claims_adjudication_comprehensive.py")
else:
    print(f"⚠️  File not found: {old_path}")
```

---

## 📊 Verification

### **Check the Fixed Output:**

```python
# List files in staging
staging_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging"

projects = dbutils.fs.ls(staging_base)

for project in projects:
    if project.isDir():
        print(f"\n📂 {project.name}")
        files = dbutils.fs.ls(project.path)
        for file in files:
            if file.name.endswith('.py'):
                print(f"  ✅ {file.name}")
```

**Expected output:**
```
📂 test_simple_sql/
  ✅ simple_select.py

📂 test_format_data/
  ✅ format_cars.py

📂 test_select_when/
  ✅ car_origin.py

📂 comprehensive_claims_adjudication/
  ✅ claims_adjudication_comprehensive.py
```

---

## 💡 Why This Matters

### **Good Traceability:**
```
Input:  claims_adjudication_comprehensive.sas
Config: claims_adjudication_comprehensive.config.yaml  (optional)
Output: claims_adjudication_comprehensive.py
```

**Clear 1:1 mapping!** Easy to:
- Find the Python file for a given SAS file
- Trace back to original SAS from Python
- Organize and maintain files

### **Bad Traceability:**
```
Input:  claims_adjudication_comprehensive.sas
Output: dlt_pipeline.py  ❌ (generic!)

Input:  eligibility_validation.sas
Output: dlt_pipeline.py  ❌ (overwrites!)

Input:  risk_adjustment.sas
Output: dlt_pipeline.py  ❌ (overwrites again!)
```

**No way to tell which is which!** ❌

---

## 🎯 For Your Real SAS Migration

When you upload **your real SAS files**, the fixed notebook will:

1. ✅ Read: `your_sas_program.sas`
2. ✅ Convert with sas2databricks
3. ✅ Save as: `your_sas_program.py` (preserves name!)
4. ✅ Clear traceability

**Example with multiple files:**
```
Input:
  01_load_claims.sas
  02_enrich_data.sas
  03_apply_edits.sas
  04_adjudicate.sas
  05_generate_payment.sas

Output:
  01_load_claims.py
  02_enrich_data.py
  03_apply_edits.py
  04_adjudicate.py
  05_generate_payment.py
```

**Perfect traceability!** ✅

---

## 🚀 Summary

**Problem:** sas2databricks creates generic `dlt_pipeline.py` files  
**Solution:** Ignore `result.filename`, use original SAS filename  
**Result:** Clear 1:1 mapping between input and output  

**What you asked for:** ✅ **DELIVERED!**

---

## 📋 Next Steps

1. **Re-import** updated `03_test_conversion.py`
2. **Re-run** the conversion
3. **Verify** output filenames match input
4. **Proceed** with confidence - traceability is fixed!

Or:

1. **Import** `03a_check_output.py`
2. **Run** to diagnose current state
3. **Decide** whether to re-run or manually rename

---

**Your concern was 100% valid!** This fix ensures you'll always know which Python file came from which SAS file. 🎯
