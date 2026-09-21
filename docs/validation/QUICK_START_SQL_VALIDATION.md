# Quick Start: SQL Server Validation (20 Minutes)

**Goal:** Prove the SAS converter works with external SQL Server data.

**What you'll create:** 2 Bronze tables from SQL Server → Run converter → Validate

---

## Step 1: Create UC Connection (2 minutes)

```bash
databricks connections create \
  --name adventureworks_sql \
  --connection-type sqlserver \
  --options '{
    "host": "sqldbdbxtraining.database.windows.net",
    "port": "1433",
    "database": "sqldb-adventureworks",
    "user": "sqladministrator@sqldbdbxtraining",
    "password": "{{secrets/dbx-ss-kv-natraining-2/natraining-sql-adventureworks-password}}"
  }'
```

**Verify:**
```bash
databricks connections get adventureworks_sql
# Should show: "state": "READY"
```

---

## Step 2: Add Pipeline to databricks.yml (5 minutes)

**Edit:** `databricks.yml`

**Add this under `resources.pipelines` (after the existing pipelines):**

```yaml
    adventureworks_ingestion:
      name: "sas_dbx_adventureworks_ingestion_${var.developer_id}"

      ingestion_definition:
        connection_name: "adventureworks_sql"

        objects:
          - table:
              source_schema: "Sales"
              source_table: "Customer"
              destination_catalog: "${var.catalog}"
              destination_schema: "${resources.schemas.sas_dbx_bronze.name}"
              table_configuration:
                primary_keys: ["CustomerID"]

          - table:
              source_schema: "Sales"
              source_table: "SalesOrderHeader"
              destination_catalog: "${var.catalog}"
              destination_schema: "${resources.schemas.sas_dbx_bronze.name}"
              table_configuration:
                primary_keys: ["SalesOrderID"]

      serverless: true
      continuous: false
      development: true

      tags:
        project: "sas_dbx_migration"
        developer_id: "${var.developer_id}"
        pipeline_type: "ingestion"
```

**Save the file.**

---

## Step 3: Deploy & Run Ingestion (5 minutes)

```bash
# Deploy bundle
databricks bundle deploy -t dev

# Run ingestion pipeline
databricks bundle run -t dev adventureworks_ingestion
```

**Monitor:** Pipeline runs in UI (Workflows → Delta Live Tables → adventureworks_ingestion)

**Expected duration:** 3-5 minutes

**Verify tables created:**
```bash
databricks tables list sas_dbx_tracy_anderson_bronze | grep -E 'customer|salesorderheader'
```

**Should show:**
- `sas_dbx_tracy_anderson_bronze.customer`
- `sas_dbx_tracy_anderson_bronze.salesorderheader`

---

## Step 4: Run Converter & Validate (8 minutes)

### 4a. Upload SAS File to Volume
```bash
# Manual step: Copy specifications/sales_summary.sas to volume staging folder
# /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/
```

### 4b. Run Converter
```bash
databricks bundle run -t dev sas_dbx_code_translator
```

### 4c. List Converted Files
```bash
python list_converted_files.py
# Should show: transformed_sales_summary.py
```

### 4d. Update Pipeline
```bash
python update_pipeline_file.py template transformed_sales_summary.py
```

### 4e. Run Pipeline in UI
- Workflows → Delta Live Tables
- Pipeline: `sas_dbx_template_tracy_anderson`
- Click **Start**

### 4f. Validate Results
```sql
-- Query Gold table
SELECT * FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.customer_summary
ORDER BY TotalRevenue DESC
LIMIT 10;
```

**Expected:** Customer list with revenue, value tier, churn risk

---

## Done! ✅

**What you proved:**
- ✅ Data ingested from SQL Server (not DATALINES)
- ✅ Converter works with external databases
- ✅ End-to-end flow: SQL → Bronze → Converter → Gold
- ✅ Architecture is source-agnostic

**Total time:** ~20 minutes

---

## Troubleshooting

### Connection fails
```bash
# Check secret exists
databricks secrets list-scopes | grep dbx-ss-kv-natraining-2

# Test with different auth (if needed)
```

### Pipeline fails
```bash
# Check event log in UI
# Workflows → Delta Live Tables → [pipeline] → Event Log
```

### Tables not created
```bash
# Verify pipeline completed
databricks pipelines list-pipelines | grep adventureworks

# Check Bronze schema
databricks tables list sas_dbx_tracy_anderson_bronze
```

---

## Next Steps

**If this works:**
- ✅ Validation complete!
- ✅ Document as second use case
- ✅ Add to project README

**If needed:**
- Add more tables (SalesOrderDetail, Product)
- Schedule ingestion via Jobs
- Test with other SAS files

---

**That's it! 4 steps, 20 minutes, proves the architecture.** 🚀
