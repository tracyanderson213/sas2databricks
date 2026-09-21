# External Data Sources Integration Guide

**How to integrate external databases, files, and APIs with the SAS to Databricks converter.**

---

## Overview

The converter translates **SAS transformation logic**, not data ingestion. External data must first land in **Bronze tables**, then the converted SAS logic processes it.

### Architecture

```
External Source → Ingestion Pipeline → Bronze Tables → Converted SAS Logic → Gold Tables
     ↓                    ↓                 ↓                    ↓                ↓
SQL Server         Lakeflow Connect    raw tables         Silver logic     Analytics
```

**Key insight:** The converter is **source-agnostic** — it doesn't care where Bronze came from.

---

## Use Case: Adventure Works Sales Analytics

**Goal:** Demonstrate external database integration with simple sales reporting.

### Data Flow

```
Azure SQL Server (Adventure Works)
    ↓
Lakeflow Connect Ingestion Pipeline
    ↓
Bronze Tables (customer, salesorderheader)
    ↓
Converted SAS Logic (sales_summary.sas)
    ↓
Gold Tables (customer_summary, sales_statistics)
```

---

## Quick Start (Mock Data)

**For demo/testing without real SQL Server:**

### Step 1: Create Mock Data
```bash
python create_adventureworks_mock_data.py
```

**Creates:**
- `bronze.customer` — 100 sample customers
- `bronze.salesorderheader` — 500 sample orders

### Step 2: Upload SAS File
```bash
# Copy to volume staging
cp specifications/sales_summary.sas /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/
```

### Step 3: Run Converter
```bash
databricks bundle run -t dev sas_dbx_code_translator
```

### Step 4: Update Pipeline
```bash
# List available files
python list_converted_files.py

# Update pipeline
python update_pipeline_file.py sales_summary transformed_sales_summary.py
```

### Step 5: Run Pipeline & Validate
```sql
-- Check customer summary
SELECT * FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.customer_summary
ORDER BY TotalRevenue DESC
LIMIT 10;

-- Check statistics
SELECT * FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.sales_statistics
ORDER BY tier_revenue DESC;
```

**Total time:** 10-15 minutes

---

## Production Setup (Real SQL Server)

### Prerequisites

1. **Azure SQL Server** with Adventure Works database
2. **UC Connection** to SQL Server
3. **Network access** (VPC peering, ExpressRoute, or public)
4. **Permissions:**
   - SQL user: `SELECT` on source tables
   - Databricks SP: `CREATE TABLE` in Bronze schema

### Step 1: Create UC Connection

**Via UI (recommended for first time):**
1. Catalog Explorer → External Data → Connections
2. Create Connection → SQL Server
3. Enter credentials
4. Test connection

**Via CLI:**
```bash
databricks connections create \
  --name adventureworks_sql \
  --connection-type sqlserver \
  --options '{
    "host": "yourserver.database.windows.net",
    "port": "1433",
    "database": "AdventureWorksLT",
    "user": "sqluser",
    "password": "{{secrets/demo/sql_password}}"
  }'
```

**Verify:**
```bash
databricks connections get adventureworks_sql
# Should show: "state": "READY"
```

---

### Step 2: Add Lakeflow Connect Pipeline to Bundle

**Edit `databricks.yml` — add under `resources.pipelines`:**

```yaml
pipelines:
  # ... existing pipelines ...

  adventureworks_ingestion:
    name: "sas_dbx_adventureworks_ingestion_${var.developer_id}"

    ingestion_definition:
      connection_name: "adventureworks_sql"

      objects:
        - table:
            source_schema: "SalesLT"
            source_table: "Customer"
            destination_catalog: "${var.catalog}"
            destination_schema: "${resources.schemas.sas_dbx_bronze.name}"
            table_configuration:
              primary_keys: ["CustomerID"]

        - table:
            source_schema: "SalesLT"
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

**Full reference:** See `lakeflow_connect_adventureworks.yml`

---

### Step 3: Deploy & Run Ingestion

```bash
# Deploy bundle (adds ingestion pipeline)
databricks bundle deploy -t dev

# Run ingestion (one-time or scheduled)
databricks bundle run -t dev adventureworks_ingestion
```

**Monitor:**
```sql
-- Check ingestion progress
SELECT
  table_name,
  COUNT(*) as row_count
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_bronze.customer
GROUP BY table_name

UNION ALL

SELECT
  table_name,
  COUNT(*) as row_count
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_bronze.salesorderheader
GROUP BY table_name;
```

---

### Step 4: Run SAS Converter (Same as Mock!)

Once Bronze tables exist, the workflow is identical:

```bash
# 1. Upload SAS file
cp specifications/sales_summary.sas /Volumes/.../staging/

# 2. Run converter
databricks bundle run -t dev sas_dbx_code_translator

# 3. Update pipeline
python update_pipeline_file.py sales_summary transformed_sales_summary.py

# 4. Run pipeline in UI
```

**The converter doesn't know or care that data came from SQL Server!**

---

## Other Data Sources

### CSV Files in ADLS (Auto Loader)

**Bronze ingestion:**
```python
@dp.table(name='bronze.daily_sales')
def daily_sales():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("cloudFiles.schemaLocation", "/tmp/schema")
            .load("/Volumes/.../sales/")
    )
```

**Converted SAS reads the same way:**
```sas
DATA work.sales;
    SET bronze.daily_sales;  /* ← From Auto Loader */
RUN;
```

---

### Snowflake (Lakehouse Federation)

**Bronze (federated, no copy):**
```sql
CREATE TABLE bronze.sales_fact
USING snowflake
OPTIONS (
  dbtable 'SALES_SCHEMA.FACT_SALES',
  sfUrl 'xyz.snowflakecomputing.com',
  sfDatabase 'WAREHOUSE'
);
```

**Converted SAS:**
```sas
DATA work.sales;
    SET bronze.sales_fact;  /* ← Federated query */
RUN;
```

---

### Salesforce (Lakeflow Connect SaaS)

**Bronze ingestion:**
```yaml
pipelines:
  salesforce_ingestion:
    ingestion_definition:
      connection_name: "salesforce_oauth"
      objects:
        - table:
            source_schema: "salesforce"
            source_table: "Account"
            destination_schema: "bronze"
```

**Converted SAS:**
```sas
DATA work.accounts;
    SET bronze.account;  /* ← From Salesforce */
RUN;
```

---

## What the Converter Needs to Handle

### Current (DATALINES)

```sas
DATA work.members;
    DATALINES;
001,John,Active
;
RUN;
```

**Converter produces:**
```python
@dp.table(name='bronze.work_members')
def work_members():
    data = [("001", "John", "Active")]
    return spark.createDataFrame(data, schema)
```

---

### New (External Source)

```sas
DATA work.members;
    SET bronze.members;  /* No transformation */
RUN;
```

**Converter should produce:**
```python
@dp.view(name='bronze.work_members')
def work_members():
    # Bronze.members ingested by Lakeflow Connect
    return dlt.read("bronze.members")
```

**This is a simple enhancement:**
- Detect: `SET` statement with no transformations
- Output: `dlt.read()` instead of `spark.createDataFrame()`
- Add comment explaining source

---

## Converter Enhancement (Future)

### Detection Logic

```python
# In SAS parser
if data_step.has_set_statement() and not data_step.has_transformations():
    # Passthrough: just reading from Bronze
    return generate_dlt_read(table_name)
else:
    # Transformation: apply SAS logic
    return generate_transformation_code(data_step)
```

### Output Examples

**Pattern 1: Passthrough (no transformation)**
```python
@dp.view(name='silver.work_customers')
def work_customers():
    """
    Passthrough from Bronze
    Source: Ingested via Lakeflow Connect from Azure SQL Server
    """
    return dlt.read("bronze.customer")
```

**Pattern 2: With transformation (existing behavior)**
```python
@dp.view(name='silver.work_customers_filtered')
def work_customers_filtered():
    """
    Filtered customers from Bronze
    """
    df = dlt.read("bronze.customer")
    return df.filter(F.col("CompanyName").isNotNull())
```

---

## Benefits of This Architecture

### ✅ Separation of Concerns
- **Ingestion:** Lakeflow Connect, Auto Loader, Federation
- **Transformation:** Converted SAS logic
- Each layer handles what it's good at

### ✅ Source Flexibility
- Add new sources without changing converter
- Mix sources (SQL + CSV + API) in same pipeline
- Swap sources (SQL Server → PostgreSQL) without SAS changes

### ✅ Incremental Processing
- Lakeflow Connect handles CDC automatically
- Auto Loader handles new files automatically
- Converted SAS logic stays simple

### ✅ Clear Responsibility
- **Data Engineering:** Sets up ingestion pipelines
- **SAS Developers:** Write transformation logic
- **Converter:** Translates transformations (not ingestion)

---

## Use Case Comparison

| Use Case | Data Source | Ingestion Method | Converter Input | Output |
|----------|-------------|------------------|-----------------|---------|
| **Healthcare Claims** (demo) | DATALINES | Built-in | claims_adjudication.sas | Bronze tables (embedded data) |
| **Adventure Works** (this guide) | Azure SQL Server | Lakeflow Connect | sales_summary.sas | Bronze → Gold analytics |
| **Retail Sales** | CSV in ADLS | Auto Loader | sales_forecast.sas | Streaming Bronze → predictions |
| **Financial Reporting** | Oracle + SQL Server | Lakeflow Connect (2x) | consolidated_report.sas | Multi-source Gold reports |

---

## Troubleshooting

### Issue: "Table bronze.customer not found"

**Cause:** Bronze ingestion not run yet

**Fix:**
```bash
# Check if Bronze tables exist
databricks schemas list na-dbxtraining | grep bronze

# Run ingestion pipeline
databricks bundle run -t dev adventureworks_ingestion

# Or create mock data
python create_adventureworks_mock_data.py
```

---

### Issue: "Connection not found"

**Cause:** UC connection doesn't exist

**Fix:**
```bash
# List connections
databricks connections list

# Create if missing
databricks connections create --name adventureworks_sql ...
```

---

### Issue: "Permission denied on source table"

**Cause:** SQL user lacks SELECT permission

**Fix:**
```sql
-- In SQL Server
GRANT SELECT ON SalesLT.Customer TO [sql_user];
GRANT SELECT ON SalesLT.SalesOrderHeader TO [sql_user];
```

---

### Issue: "Converter produces wrong table reference"

**Cause:** SAS file references wrong schema

**Fix:**
```sas
/* Wrong */
DATA work.customers;
    SET mydb.customers;  /* External LIBNAME not recognized */
RUN;

/* Right */
DATA work.customers;
    SET bronze.customer;  /* Assumes data already in Bronze */
RUN;
```

---

## Next Steps

### For Demo/POC
1. ✅ Run mock data script
2. ✅ Test with sales_summary.sas
3. ✅ Validate end-to-end workflow

### For Production
1. Create UC connection to real SQL Server
2. Add Lakeflow Connect pipeline to bundle
3. Deploy and run ingestion
4. Replace mock script with real ingestion
5. Document source-specific patterns

### Future Enhancements
1. Add converter support for `SET` passthrough
2. Add more source examples (PostgreSQL, Oracle, etc.)
3. Create source-specific SAS templates
4. Document CDC and incremental patterns

---

## Related Documentation

- **[AUTOMATED_WORKFLOW_GUIDE.md](AUTOMATED_WORKFLOW_GUIDE.md)** — Core workflow (DATALINES → Gold)
- **[NAMING_CONVENTIONS.md](NAMING_CONVENTIONS.md)** — Resource naming patterns
- **[databricks-lakeflow-connect skill](/.claude/skills/databricks-lakeflow-connect/)** — Ingestion setup
- **[lakeflow_connect_adventureworks.yml](lakeflow_connect_adventureworks.yml)** — Full pipeline config

---

## Summary

**Key Takeaways:**

1. **Ingestion is separate from transformation** — Bronze ingestion happens BEFORE converter runs
2. **Converter is source-agnostic** — Works the same whether Bronze came from SQL Server, CSV, or API
3. **Mock data for testing** — No SQL Server needed for initial POC
4. **Production uses Lakeflow Connect** — Managed, CDC-enabled ingestion from databases
5. **Same workflow regardless** — Upload SAS → Run converter → Update pipeline → Validate

**The architecture scales from demo to production with minimal changes!** 🚀
