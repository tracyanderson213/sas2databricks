# Adventure Works SQL Validation Checklist

**Goal:** Prove SAS converter works with external SQL Server data  
**Time:** 20 minutes  
**Date:** _____________

---

## Prerequisites ✅

- [ ] Databricks CLI installed and working
- [ ] `.databrickscfg.bundle` file exists
- [ ] Access to Databricks workspace
- [ ] SQL Server connection info available

**Verify:** `python verify_sql_prerequisites.py`

---

## Step 1: Create UC Connection (2 min)

```bash
databricks connections create \
  --name adventureworks_sql \
  --connection-type sqlserver \
  --options '{"host":"sqldbdbxtraining.database.windows.net","port":"1433","database":"sqldb-adventureworks","user":"sqladministrator@sqldbdbxtraining","password":"{{secrets/dbx-ss-kv-natraining-2/natraining-sql-adventureworks-password}}"}'
```

**Verify:**
```bash
databricks connections get adventureworks_sql
# Should show: "state": "READY"
```

- [ ] Connection created
- [ ] Connection is READY

---

## Step 2: Deploy Bundle (2 min)

```bash
databricks bundle deploy -t dev
```

**Expected output:**
```
Created pipelines.adventureworks_ingestion
Resources: 1 created, ...
```

- [ ] Bundle deployed successfully
- [ ] adventureworks_ingestion pipeline created

---

## Step 3: Run Ingestion (5 min)

```bash
databricks bundle run -t dev adventureworks_ingestion
```

**Wait for completion** (3-5 minutes)

**Monitor:** Check UI → Workflows → Delta Live Tables → adventureworks_ingestion

- [ ] Ingestion pipeline started
- [ ] Ingestion completed successfully
- [ ] No errors in event log

---

## Step 4: Verify Bronze Tables (1 min)

```bash
databricks tables list sas_dbx_tracy_anderson_bronze | grep -E 'customer|salesorderheader'
```

**Expected output:**
```
sas_dbx_tracy_anderson_bronze.customer
sas_dbx_tracy_anderson_bronze.salesorderheader
```

- [ ] customer table exists
- [ ] salesorderheader table exists

---

## Step 5: Upload SAS File (2 min)

**Manual:** Copy `specifications/sales_summary.sas` to volume

**Location:** `/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/`

**Methods:**
- Databricks UI: Catalog → Volumes → Upload
- CLI: `databricks fs cp specifications/sales_summary.sas dbfs:/Volumes/.../staging/`

- [ ] SAS file uploaded to volume staging folder

---

## Step 6: Run Converter (2 min)

```bash
databricks bundle run -t dev sas_dbx_code_translator
```

**Expected:** Converter runs successfully, creates transformed_sales_summary.py

- [ ] Converter ran successfully
- [ ] No errors in job output

---

## Step 7: List Converted Files (30 sec)

```bash
python list_converted_files.py
```

**Expected output:**
```
📄 transformed_sales_summary.py
   Size: XX KB
   Modified: 2026-XX-XX
```

- [ ] transformed_sales_summary.py appears in list

---

## Step 8: Update Pipeline (1 min)

```bash
python update_pipeline_file.py template transformed_sales_summary.py
```

**Expected output:**
```
✅ Pipeline File Updated!
Next: Open sas_dbx_template_tracy_anderson and click Start
```

- [ ] Pipeline file updated
- [ ] No errors

---

## Step 9: Run Pipeline (5-10 min)

**In Databricks UI:**
1. Workflows → Delta Live Tables
2. Find: `sas_dbx_template_tracy_anderson`
3. Click **Start**
4. Wait for completion

- [ ] Pipeline started
- [ ] Pipeline completed successfully
- [ ] Gold tables created

---

## Step 10: Validate Results (2 min)

**Run in SQL Editor:**

```sql
-- Check customer summary
SELECT * FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.customer_summary
ORDER BY TotalRevenue DESC
LIMIT 10;

-- Check statistics
SELECT * FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.sales_statistics
ORDER BY tier_revenue DESC;
```

**Expected:**
- Customer rows with revenue, value_tier, churn_risk
- Statistics grouped by tier and churn risk

- [ ] customer_summary table exists
- [ ] customer_summary has data
- [ ] sales_statistics table exists
- [ ] sales_statistics has data
- [ ] Data looks correct (revenue, tiers, etc.)

---

## Success Criteria ✅

- [ ] **All 10 steps completed**
- [ ] **Bronze tables ingested from SQL Server**
- [ ] **Converter produced clean Python file**
- [ ] **Pipeline ran successfully**
- [ ] **Gold tables contain valid analytics**

---

## What This Proves

✅ **External database integration** — Data from SQL Server, not DATALINES  
✅ **Lakeflow Connect works** — Ingestion pipeline functional  
✅ **Converter is source-agnostic** — Works regardless of Bronze source  
✅ **End-to-end flow** — SQL Server → Bronze → Converter → Gold  

**Architecture validated!** 🎉

---

## Troubleshooting

### Connection fails
- Check secret exists in Key Vault
- Verify network access to SQL Server
- Try creating connection via UI instead

### Ingestion fails
- Check event log in pipeline UI
- Verify SQL user has SELECT permission
- Check source tables exist in SQL Server

### Converter fails
- Verify SAS file uploaded to correct location
- Check job logs for errors
- Ensure volume path is correct

### Pipeline fails
- Check Bronze tables exist before running
- Verify pipeline configuration
- Review error in DLT event log

### Validation fails
- Check if pipeline completed (not just started)
- Verify Gold schema exists
- Run `databricks tables list sas_dbx_tracy_anderson_gold`

---

## Time Breakdown

| Step | Task | Time |
|------|------|------|
| 1 | Create connection | 2 min |
| 2 | Deploy bundle | 2 min |
| 3 | Run ingestion | 5 min |
| 4 | Verify tables | 1 min |
| 5 | Upload SAS file | 2 min |
| 6 | Run converter | 2 min |
| 7 | List files | 0.5 min |
| 8 | Update pipeline | 1 min |
| 9 | Run pipeline | 5-10 min |
| 10 | Validate | 2 min |
| **Total** | | **~20-25 min** |

---

## Notes

Date completed: _____________

Issues encountered: _______________________________________

_______________________________________________________

_______________________________________________________

Overall result: ⭐ ⭐ ⭐ ⭐ ⭐

---

**Reference files:**
- `QUICK_START_SQL_VALIDATION.md` — Detailed guide
- `RUN_THIS_COMMANDS.sh` — All commands in one script
- `verify_sql_prerequisites.py` — Check prerequisites
