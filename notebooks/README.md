# Setup Notebooks - Run in Order

These 3 notebooks set up and test the SAS migration system.

## 📋 Run in This Order

### **1. 01_setup_volumes.py** (3 min)
**Purpose:** Create schema, volume, and folder structure

**What it does:**
```sql
CREATE SCHEMA na-dbxtraining.sas2dbx_migrate;
CREATE VOLUME sas_migration;
-- Creates 5 subfolders: input, staging, approved, metadata_registry, archive
```

**Prerequisites:** None - run this first!

**Output:**
```
✅ Volume structure created
📁 /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/
```

---

### **2. 02_upload_sample_sas.py** (1 min)
**Purpose:** Upload 3 real SAS examples for testing

**What it does:**
- Uploads PROC SQL example
- Uploads PROC FORMAT + DATA step example
- Uploads DATA step with SELECT/WHEN example
- Creates config.yaml for each

**Prerequisites:**
- ✅ Run `01_setup_volumes.py` first

**Output:**
```
✅ 3 SAS projects uploaded to input/ volume
```

---

### **3. 03_test_conversion.py** (5-10 min)
**Purpose:** Convert SAS → SDP pipelines

**What it does:**
```python
%pip install sas2databricks
migrate_project(..., target="sdp")
# Converts all 3 samples
# Generates conversion reports
```

**Prerequisites:**
- ✅ Run `01_setup_volumes.py` first
- ✅ Run `02_upload_sample_sas.py` second

**Output:**
```
✅ Conversion complete
📁 /Volumes/.../staging/test_simple_sql/
    ├── CONVERSION_REPORT.html
    ├── sdp/simple_select.py
    └── databricks.yml
```

---

## 🚀 Quick Start

### **Option A: Manual Upload to Databricks**

1. **Open Databricks workspace:**
   https://adb-1952652121322753.13.azuredatabricks.net/

2. **Create folder:**
   - Workspace → Users → {your_email} → Create folder `sas2dbx_setup`

3. **Import notebooks:**
   - Click Import → File
   - Upload: `01_setup_volumes.py`
   - Upload: `02_upload_sample_sas.py`
   - Upload: `03_test_conversion.py`

4. **Run in order:**
   - Open `01_setup_volumes` → Run All
   - Open `02_upload_sample_sas` → Run All
   - Open `03_test_conversion` → Run All

---

### **Option B: Deploy via Bundle**

```bash
cd ../setup-bundle
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

**Note:** Requires token with `workspace` scope. If blocked, use Option A.

---

## ✅ Success Criteria

After running all 3 notebooks:

- [ ] Schema created: `na-dbxtraining.sas2dbx_migrate`
- [ ] Volume created with 5 folders
- [ ] 3 SAS projects in input/
- [ ] 3 converted projects in staging/
- [ ] CONVERSION_REPORT.html shows ≥95% HIGH confidence

---

## 🎯 After Completion

**Check your work:**
```python
# Verify volume structure
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"))

# Check conversion output
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_simple_sql"))
```

**Review conversion:**
- Open: `CONVERSION_REPORT.html` (download from staging/)
- Read: `sdp/simple_select.py` (converted pipeline)
- Verify: Confidence scores

**Deploy test pipeline:**
```bash
cd /Volumes/.../staging/test_simple_sql
databricks bundle deploy -t dev
```

---

## 📚 Documentation

- **../QUICKSTART.md** — 15-minute overview
- **../DEPLOY_NOTEBOOKS.md** — Detailed deployment instructions
- **../README.md** — System architecture
- **../specifications/** — Reference guides
