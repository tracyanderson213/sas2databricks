# Setup Adventure Works Ingestion - Step by Step

**You have the full Adventure Works database with Sales.Customer and Sales.SalesOrderHeader!**

**Time to complete:** 20-30 minutes

---

## What You'll Create

```
Azure SQL Server (sqldbdbxtraining.database.windows.net)
    ↓
UC Connection (adventureworks_sql)
    ↓
Lakeflow Connect Pipeline
    ↓
Bronze Tables:
  • sas_dbx_tracy_anderson_bronze.customer (~19,000 rows)
  • sas_dbx_tracy_anderson_bronze.salesorderheader (~31,000 rows)
```

---

## Step 1: Create UC Connection

### Option A: Via CLI (Quickest)

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

**Verify connection created:**
```bash
databricks connections get adventureworks_sql
# Should show: "state": "READY"
```

---

### Option B: Via Databricks UI

1. **Catalog Explorer** → External Data → Connections
2. **Create Connection**
3. **Connection Type:** SQL Server
4. **Fill in details:**
   - Name: `adventureworks_sql`
   - Host: `sqldbdbxtraining.database.windows.net`
   - Port: `1433`
   - Database: `sqldb-adventureworks`
   - Username: `sqladministrator@sqldbdbxtraining`
   - Password: Get from Key Vault or use secret reference
5. **Test Connection**
6. **Create**

---

## Step 2: Add Pipeline to databricks.yml

**Copy the pipeline config from `lakeflow_connect_adventureworks.yml` (already updated with Sales schema!)**

**Edit `databricks.yml` and add under `resources.pipelines`:**

```yaml
resources:
  pipelines:
    # ... existing pipelines ...

    # Add this new pipeline:
    adventureworks_ingestion:
      name: "sas_dbx_adventureworks_ingestion_${var.developer_id}"

      ingestion_definition:
        connection_name: "adventureworks_sql"

        objects:
          # Customer table (Full Adventure Works - Sales schema)
          - table:
              source_schema: "Sales"
              source_table: "Customer"
              destination_catalog: "${var.catalog}"
              destination_schema: "${resources.schemas.sas_dbx_bronze.name}"
              table_configuration:
                primary_keys: ["CustomerID"]

          # SalesOrderHeader table (Full Adventure Works - Sales schema)
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
        bundle_target: "${bundle.target}"
        pipeline_type: "ingestion"
        source: "adventureworks_sql"
```

**Save the file.**

---

## Step 3: Deploy Bundle

```bash
databricks bundle deploy -t dev
```

**Expected output:**
```
Created pipelines.adventureworks_ingestion
Resources: 1 created, 0 changed, 0 deleted
```

**Verify pipeline created:**
```bash
databricks pipelines list-pipelines | grep adventureworks
# Should show: sas_dbx_adventureworks_ingestion_tracy_anderson
```

---

## Step 4: Run Ingestion Pipeline

```bash
databricks bundle run -t dev adventureworks_ingestion
```

**Or via UI:**
1. Workflows → Delta Live Tables
2. Find: `sas_dbx_adventureworks_ingestion_tracy_anderson`
3. Click **Start**

**Monitor progress:**
- UI shows table-by-table ingestion
- Typical duration: 2-5 minutes for 2 tables

---

## Step 5: Verify Data Ingested

```bash
# Check tables created
databricks tables list sas_dbx_tracy_anderson_bronze | grep -E 'customer|salesorderheader'
```

**Expected output:**
```
sas_dbx_tracy_anderson_bronze.customer
sas_dbx_tracy_anderson_bronze.salesorderheader
```

**Query row counts:**
```sql
-- Via Databricks SQL Editor or notebook
SELECT 'customer' as table_name, COUNT(*) as row_count
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_bronze.customer

UNION ALL

SELECT 'salesorderheader', COUNT(*)
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_bronze.salesorderheader;
```

**Expected results:**
- customer: ~19,000 rows
- salesorderheader: ~31,000 rows

---

## Step 6: Run SAS Converter

**Now that Bronze tables exist, run the converter:**

```bash
# 1. Upload SAS file to staging
# (Manual: Copy specifications/sales_summary.sas to volume staging folder)

# 2. Run converter
databricks bundle run -t dev sas_dbx_code_translator

# 3. List converted files
python list_converted_files.py
# Should show: transformed_sales_summary.py

# 4. Update pipeline
python update_pipeline_file.py sales_summary transformed_sales_summary.py

# 5. Run pipeline in UI
# Workflows → Delta Live Tables → sas_dbx_template_tracy_anderson → Start
```

---

## Step 7: Validate Results

**Query Gold tables created by the pipeline:**

```sql
-- Top customers by revenue
SELECT
    CustomerID,
    CompanyName,
    OrderCount,
    TotalRevenue,
    value_tier,
    churn_risk
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.customer_summary
ORDER BY TotalRevenue DESC
LIMIT 10;

-- Statistics by customer tier
SELECT
    value_tier,
    churn_risk,
    customer_count,
    tier_revenue,
    avg_customer_revenue
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.sales_statistics
ORDER BY tier_revenue DESC;
```

**Expected results:**
- customer_summary: Hundreds of rows with value tiers and churn risk
- sales_statistics: Summary by tier (High/Medium/Low) and churn risk

---

## Troubleshooting

### Issue: "Connection not found"

**Error:** `UC connection adventureworks_sql does not exist`

**Fix:**
```bash
# Verify connection exists
databricks connections list | grep adventureworks

# Create if missing (see Step 1)
```

---

### Issue: "Cannot reach host"

**Error:** `Failed to connect to sqldbdbxtraining.database.windows.net`

**Possible causes:**
- Network connectivity issue
- Firewall blocking Databricks IP
- SQL Server not accessible

**Fix:**
- Check VPC peering / network rules
- Verify SQL Server is running
- Test connection from notebook (JDBC)

---

### Issue: "Permission denied"

**Error:** `SELECT permission was denied on object 'Customer'`

**Fix:**
```sql
-- In SQL Server, grant permissions:
GRANT SELECT ON Sales.Customer TO sqladministrator;
GRANT SELECT ON Sales.SalesOrderHeader TO sqladministrator;
```

---

### Issue: "Pipeline runs but creates no tables"

**Check:**
1. Connection state: `databricks connections get adventureworks_sql`
2. Event log: Open pipeline in UI → View Event Log
3. Source tables exist: Run notebook to query SQL Server directly

---

### Issue: "SAS file references wrong tables"

**Error:** `Table bronze.customer not found`

**Current Bronze tables should be:**
- `bronze.customer` (from Sales.Customer)
- `bronze.salesorderheader` (from Sales.SalesOrderHeader)

**If sales_summary.sas references different names:**
- Update SAS file to use correct Bronze table names
- Or update destination table names in Lakeflow Connect config

---

## What's Next

### After Ingestion Works

1. ✅ **Test converter** with real SQL Server data
2. ✅ **Validate results** match expectations
3. ✅ **Document the pattern** for future use cases
4. ✅ **Add more tables** if needed (SalesOrderDetail, Product, etc.)

### Future Enhancements

1. **Schedule ingestion** via Jobs
   ```yaml
   jobs:
     adventureworks_daily_sync:
       schedule:
         quartz_cron_expression: "0 0 2 * * ?"  # Daily at 2 AM
       tasks:
         - pipeline_task:
             pipeline_id: "${resources.pipelines.adventureworks_ingestion.id}"
   ```

2. **Add CDC** for incremental updates
   - Enable change tracking in SQL Server
   - Lakeflow Connect automatically picks up changes

3. **Add more tables**
   - SalesOrderDetail (line items)
   - Product (product catalog)
   - SalesTerritory (already have this!)

---

## Summary

**What you accomplished:**

✅ Created UC connection to SQL Server  
✅ Added Lakeflow Connect ingestion pipeline  
✅ Ingested Customer & SalesOrderHeader to Bronze  
✅ Ran converter on sales_summary.sas  
✅ Created Gold analytics tables  
✅ **Proved end-to-end: SQL Server → Bronze → Gold with REAL data!**

**Total time:** 20-30 minutes

**Result:** Working demo with real Adventure Works data! 🚀

---

## Files Reference

| File | Purpose |
|------|---------|
| `lakeflow_connect_adventureworks.yml` | Pipeline config (Sales schema) |
| `specifications/sales_summary.sas` | Source SAS file |
| `EXTERNAL_SOURCES_GUIDE.md` | Complete integration guide |
| `ADVENTURE_WORKS_README.md` | Quick reference |
| This file | Step-by-step setup |

---

## Connection Details (Your Setup)

```
Server: sqldbdbxtraining.database.windows.net
Database: sqldb-adventureworks
User: sqladministrator@sqldbdbxtraining
Password: Key Vault secret (dbx-ss-kv-natraining-2)
Schema: Sales (Full Adventure Works)
Tables: Customer (~19K rows), SalesOrderHeader (~31K rows)
```

**Ready to proceed? Start with Step 1!** ✨
