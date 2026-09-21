# Cleanup Old Files - Remove HLS Claims Demo Artifacts

## 🎯 What Changed

**Original project:** HLS Claims Demo (Bravo Insurance)
- Claims pipeline with synthetic data
- Dashboards, metric views, Genie

**Current project:** SAS to Databricks Migration System
- sas2databricks conversion pipeline
- Volume-based workflow
- Setup notebooks

---

## ❌ Files to DELETE (Old HLS Claims Demo)

### **Folders to Remove:**
```bash
rm -rf src/                    # Old claims pipeline code
rm -rf data_generation/        # Old synthetic data generation
rm -rf pipeline/              # Old pipeline configs
rm -rf resources/             # Old DAB resources
rm -rf context/               # Old project context
```

### **Root-level files to Remove:**
```bash
rm architecture.md            # Old architecture diagram
rm DEPLOY.md                  # Old manual deployment (HLS claims)
rm DAB_DEPLOYMENT.md          # Old DAB deployment guide (HLS claims)
```

### **Specification files to Remove:**
```bash
rm specifications/01-lakeflow.md      # Old Lakeflow spec
rm specifications/04-ai-bi.md         # Old AI/BI spec
rm specifications/SCHEMAS.md          # Old claims schema
rm specifications/SDP_MIGRATION.md    # Duplicate/old migration doc
```

---

## ✅ Files to KEEP (SAS Migration System)

### **Root Documentation:**
- ✅ `README.md` — System architecture
- ✅ `QUICKSTART.md` — 15-minute setup
- ✅ `DEPLOY_NOTEBOOKS.md` — Notebook deployment
- ✅ `FILE_NAMING_STRATEGY.md` — File naming & traceability
- ✅ `WHERE_TO_FIND_OUTPUT.md` — Where to find converted files
- ✅ `WHATS_NEW.md` — Latest updates
- ✅ `WHICH_EXAMPLE_TO_USE.md` — Example comparison
- ✅ `databricks.yml` — Main DAB bundle config
- ✅ `resources.json` — Resource tracking

### **Notebooks:**
- ✅ `notebooks/01_setup_volumes.py`
- ✅ `notebooks/02_upload_sample_sas.py`
- ✅ `notebooks/02a_upload_healthcare_example.py`
- ✅ `notebooks/02b_upload_comprehensive_claims.py`
- ✅ `notebooks/03_test_conversion.py`
- ✅ `notebooks/README.md`

### **Setup Bundle:**
- ✅ `setup-bundle/databricks.yml`
- ✅ `setup-bundle/README.md`

### **Specifications:**
- ✅ `specifications/SAS_MIGRATION_GUIDE.md`
- ✅ `specifications/CONVERSION_WALKTHROUGH.md`
- ✅ `specifications/VOLUME_SETUP.md`
- ✅ `specifications/TEST_CONVERSION_EXAMPLE.md`

### **Project Config:**
- ✅ `.databricks/project.json`

---

## 🧹 Cleanup Script

### **Option 1: Safe Cleanup (Archive First)**

```bash
# Create archive of old files
mkdir -p old_hls_demo_backup
mv src/ old_hls_demo_backup/
mv data_generation/ old_hls_demo_backup/
mv pipeline/ old_hls_demo_backup/
mv resources/ old_hls_demo_backup/
mv context/ old_hls_demo_backup/
mv architecture.md old_hls_demo_backup/
mv DEPLOY.md old_hls_demo_backup/
mv DAB_DEPLOYMENT.md old_hls_demo_backup/
mv specifications/01-lakeflow.md old_hls_demo_backup/
mv specifications/04-ai-bi.md old_hls_demo_backup/
mv specifications/SCHEMAS.md old_hls_demo_backup/
mv specifications/SDP_MIGRATION.md old_hls_demo_backup/

echo "✅ Old files archived to old_hls_demo_backup/"
echo "   Review, then delete: rm -rf old_hls_demo_backup/"
```

### **Option 2: Direct Delete**

```bash
# ⚠️  WARNING: Permanent deletion!
rm -rf src/
rm -rf data_generation/
rm -rf pipeline/
rm -rf resources/
rm -rf context/
rm architecture.md
rm DEPLOY.md
rm DAB_DEPLOYMENT.md
rm specifications/01-lakeflow.md
rm specifications/04-ai-bi.md
rm specifications/SCHEMAS.md
rm specifications/SDP_MIGRATION.md

echo "✅ Cleanup complete!"
```

---

## 📋 After Cleanup - Project Structure

```
sas2dbx-migrate/
├── README.md                           ← System overview
├── QUICKSTART.md                       ← 15-min setup
├── DEPLOY_NOTEBOOKS.md                 ← How to deploy notebooks
├── FILE_NAMING_STRATEGY.md             ← File naming guide
├── WHERE_TO_FIND_OUTPUT.md             ← Output location guide
├── WHATS_NEW.md                        ← Latest changes
├── WHICH_EXAMPLE_TO_USE.md             ← Example comparison
├── databricks.yml                      ← Main DAB config
├── resources.json                      ← Resource tracking
│
├── notebooks/                          ← Setup notebooks
│   ├── 01_setup_volumes.py
│   ├── 02_upload_sample_sas.py
│   ├── 02a_upload_healthcare_example.py
│   ├── 02b_upload_comprehensive_claims.py
│   ├── 03_test_conversion.py
│   └── README.md
│
├── setup-bundle/                       ← Bundle deploy (optional)
│   ├── databricks.yml
│   └── README.md
│
├── specifications/                     ← Technical docs
│   ├── SAS_MIGRATION_GUIDE.md
│   ├── CONVERSION_WALKTHROUGH.md
│   ├── VOLUME_SETUP.md
│   └── TEST_CONVERSION_EXAMPLE.md
│
└── .databricks/
    └── project.json
```

**Clean, focused structure for SAS migration!**

---

## 🎯 Why Clean These Up?

### **Confusion:**
- ❌ Old `DEPLOY.md` talks about HLS claims pipeline (not SAS migration)
- ❌ `src/claims_pipeline.py` is unrelated to SAS conversion
- ❌ `data_generation/` creates Bravo Insurance synthetic data (not SAS test data)
- ❌ Old specifications reference wrong architecture

### **Maintenance:**
- ❌ Out-of-date documentation
- ❌ References to old project name (hls_sas_dbx_claims)
- ❌ Confusing for new users

### **Storage:**
- Removes ~60KB of unused code and docs

---

## ✅ Recommendation

**Run Option 1 (Archive First):**

```bash
cd /app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb

# Archive old files
mkdir -p old_hls_demo_backup
mv src/ data_generation/ pipeline/ resources/ context/ old_hls_demo_backup/ 2>/dev/null
mv architecture.md DEPLOY.md DAB_DEPLOYMENT.md old_hls_demo_backup/ 2>/dev/null
mv specifications/01-lakeflow.md specifications/04-ai-bi.md specifications/SCHEMAS.md specifications/SDP_MIGRATION.md old_hls_demo_backup/ 2>/dev/null

echo "✅ Cleanup complete! Archived to old_hls_demo_backup/"
```

**Then verify everything works:**
1. Check that notebooks still run
2. Review documentation
3. If all good, delete archive: `rm -rf old_hls_demo_backup/`

---

## 📊 Summary

| Category | DELETE | KEEP |
|----------|--------|------|
| **Folders** | src/, data_generation/, pipeline/, resources/, context/ | notebooks/, setup-bundle/, specifications/ |
| **Docs** | architecture.md, DEPLOY.md, DAB_DEPLOYMENT.md, 01-lakeflow.md, 04-ai-bi.md | README.md, QUICKSTART.md, FILE_NAMING_STRATEGY.md, etc. |
| **Config** | pipeline_config*.yml, claims_pipeline.yml | databricks.yml, resources.json |

**Result:** Clean project focused on SAS migration! 🎯
