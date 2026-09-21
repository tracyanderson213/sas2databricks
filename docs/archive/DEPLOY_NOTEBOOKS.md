# Deploy Setup Notebooks to Databricks Workspace

## 🚨 Token Issue: Workspace Scope Required

The current token lacks `workspace` scope needed for bundle deployment. **Two options available:**

---

## ✅ Option A: Manual Upload (EASIEST - 2 minutes)

**Recommended if token has limited permissions.**

### **Step 1: Open Databricks Workspace**

Go to: https://adb-1952652121322753.13.azuredatabricks.net/

### **Step 2: Create Folder**

1. Click **Workspace** in left sidebar
2. Navigate to **Users** → **tracy.anderson@3cloudsolutions.com**
3. Click **⋮** (three dots) → **Create** → **Folder**
4. Name it: `sas2dbx_setup`

### **Step 3: Import Notebooks**

1. Open the `sas2dbx_setup` folder you just created
2. Click **Import** button
3. Select **File** tab
4. Upload each notebook:
   - Browse to: `notebooks/01_setup_volumes.py` → Import
   - Browse to: `notebooks/02_upload_sample_sas.py` → Import
   - Browse to: `notebooks/03_test_conversion.py` → Import

**Result:**
```
Workspace/
└── Users/
    └── tracy.anderson@3cloudsolutions.com/
        └── sas2dbx_setup/
            ├── 01_setup_volumes
            ├── 02_upload_sample_sas
            └── 03_test_conversion
```

### **Step 4: Run Notebooks**

**In order:**

#### **1. Setup Volumes**
- Open: `01_setup_volumes`
- Attach to any cluster
- Click: **Run All**
- Wait: ~2-3 minutes
- ✅ Verify: "🎉 SAS MIGRATION INFRASTRUCTURE READY!"

#### **2. Upload Sample SAS**
- Open: `02_upload_sample_sas`
- Click: **Run All**
- Wait: ~30 seconds
- ✅ Verify: "📤 SAMPLE SAS CODE UPLOADED SUCCESSFULLY!"

#### **3. Test Conversion**
- Open: `03_test_conversion`
- Click: **Run All**
- Wait: ~5-10 minutes
- ✅ Verify: "✅ Conversion complete!" (3 projects)

---

## 🔐 Option B: Fix Token + Deploy via Bundle

**Use this if you can get a new token with full permissions.**

### **Step 1: Generate New Token**

1. Databricks → User Settings → Developer → Access tokens
2. Click: **Generate new token**
3. **IMPORTANT:** Select **"All APIs"** or check these scopes:
   - ✅ workspace
   - ✅ sql
   - ✅ pipelines
   - ✅ unity-catalog
4. Copy the token

### **Step 2: Update Config**

```bash
# Edit .databrickscfg
nano /app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg
```

Replace token line:
```
[DEFAULT]
host = https://adb-1952652121322753.13.azuredatabricks.net
token = <YOUR_NEW_TOKEN_HERE>
```

### **Step 3: Deploy Bundle**

```bash
cd /app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/setup-bundle
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

**What this does:**
- Creates folder: `/Workspace/Users/tracy.anderson@3cloudsolutions.com/.sas2dbx_setup/`
- Syncs all 3 notebooks
- Ready to run in workspace

### **Step 4: Run Notebooks**

Same as Option A, step 4.

---

## 📋 What Each Notebook Does

### **01_setup_volumes.py**
```sql
CREATE SCHEMA na-dbxtraining.sas2dbx_migrate;
CREATE VOLUME sas_migration;
-- Creates folder structure
```
**Output:** Complete volume infrastructure

### **02_upload_sample_sas.py**
```python
# Uploads 3 real SAS examples:
# - test_simple_sql (PROC SQL)
# - test_format_data (PROC FORMAT + DATA)
# - test_select_when (DATA with SELECT/WHEN)
```
**Output:** 3 SAS projects in input/ volume

### **03_test_conversion.py**
```python
%pip install sas2databricks
migrate_project(..., target="sdp")
```
**Output:** Converted SDP pipelines in staging/ volume

---

## ✅ Success Checklist

After running all 3 notebooks:

- [ ] Schema created: `na-dbxtraining.sas2dbx_migrate`
- [ ] Volume created: `sas_migration` with 5 folders
- [ ] Sample SAS uploaded: 3 projects in input/
- [ ] Conversion succeeded: 3 projects in staging/
- [ ] Reports generated: CONVERSION_REPORT.html for each
- [ ] High confidence: ≥95% green in reports

---

## 🎯 After All Notebooks Run

### **Check Your Work**

**1. Verify Volume Structure**
```python
# In any notebook
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"))
```

**Expected:**
```
input/
staging/
approved/
metadata_registry/
archive/
```

**2. Check Sample SAS**
```python
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input"))
```

**Expected:**
```
test_simple_sql/
test_format_data/
test_select_when/
```

**3. Check Conversion Output**
```python
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_simple_sql"))
```

**Expected:**
```
CONVERSION_REPORT.html
sdp/
pyspark/
validation/
databricks.yml
src/
```

### **Review Conversion Report**

**Option 1: Download and open in browser**
```python
# Get the file path
report = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_simple_sql/CONVERSION_REPORT.html"

# Copy to temp location you can download
dbutils.fs.cp(report, "dbfs:/tmp/CONVERSION_REPORT.html")
```

Then download from: `dbfs:/tmp/CONVERSION_REPORT.html`

**Option 2: Read converted code directly**
```python
with open("/dbfs/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_simple_sql/sdp/simple_select.py", "r") as f:
    print(f.read())
```

---

## 🚀 Next Steps

### **Deploy a Test Pipeline**

```bash
cd /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/test_simple_sql
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

### **Convert Your Real SAS Code**

1. Create project folder:
   ```python
   project = "your_project_name"
   base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input"
   dbutils.fs.mkdirs(f"{base}/{project}/sas")
   ```

2. Upload your SAS files to: `{base}/{project}/sas/`

3. Create config.yaml (see sample projects for template)

4. Run conversion:
   ```python
   from sas2databricks import migrate_project
   
   migrate_project(
       sas_project_dir=f"{base}/{project}",
       output_dir=f"/Volumes/.../staging/{project}",
       target="sdp",
       model="opus-4.8"
   )
   ```

---

## 🔧 Troubleshooting

### **Issue: Cannot create schema**
```
Error: Insufficient permissions
```
**Solution:** Need `CREATE SCHEMA` permission on `na-dbxtraining` catalog

### **Issue: Cannot create volume**
```
Error: Insufficient permissions
```
**Solution:** Need `CREATE VOLUME` permission in schema

### **Issue: sas2databricks install fails**
```
Error: No matching distribution found
```
**Solution:**
```python
%pip install --upgrade pip
%pip install sas2databricks --no-cache-dir
```

### **Issue: Conversion fails**
```
Error: Model not found or API error
```
**Solution:** Check if LLM API credentials needed for `opus-4.8` model

---

## 💡 Recommendation

**Use Option A (Manual Upload)** for now:
- ✅ Works with current token
- ✅ Fastest to get started (2 minutes)
- ✅ No permission issues
- ✅ Same result as bundle deployment

**Later:** Get full-scope token and use bundles for production deployments.

---

## 📚 Documentation Reference

- **QUICKSTART.md** — Overview of the 15-minute setup
- **README.md** — System architecture
- **SAS_MIGRATION_GUIDE.md** — Detailed conversion strategy
- **CONVERSION_WALKTHROUGH.md** — Real examples with output
