# Adventure Works Use Case - Quick Start

**Second use case: External database integration with Adventure Works sales data**

---

## ⚡ FASTEST PATH (Copy/Paste)

### Option 1: Run All Commands (Recommended)
```bash
# Run this script - it walks you through all steps
bash RUN_THIS_COMMANDS.sh
```

### Option 2: Use Checklist
Open `CHECKLIST.md` and follow step-by-step (printable!)

### Option 3: Manual Commands
See below for step-by-step manual process

---

## What This Proves

✅ **External database integration** — Data from SQL Server, not embedded DATALINES  
✅ **Source-agnostic converter** — Reads from Bronze regardless of ingestion method  
✅ **Production architecture** — Separation of ingestion and transformation  
✅ **Real SQL Server data** — Sales.Customer + Sales.SalesOrderHeader from Adventure Works  

---

## Prerequisites Check

```bash
# Run this first to verify everything is ready
python verify_sql_prerequisites.py
```

**This checks:**
- ✅ Databricks CLI installed
- ✅ databricks.yml updated (already done!)
- ✅ SAS file exists
- ❌ UC connection (you need to create this in Step 1)

---

## Quick Start (20 minutes)

### Step 1: Create Mock Data
```bash
python create_adventureworks_mock_data.py
```

**Creates:**
- `sas_dbx_tracy_anderson_bronze.customer` — 100 customers
- `sas_dbx_tracy_anderson_bronze.salesorderheader` — 500 orders

---

### Step 2: Upload SAS File to Volume

**Option A: Copy to staging folder**
```bash
# If volume mounted locally
cp specifications/sales_summary.sas /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/
```

**Option B: Upload via CLI**
```bash
databricks fs cp specifications/sales_summary.sas \
  dbfs:/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/sales_summary.sas
```

---

### Step 3: Run Converter
```bash
databricks bundle run -t dev sas_dbx_code_translator
```

**Output:** `transformed_sales_summary.py` in `/Volumes/.../converted/`

---

### Step 4: List Converted Files
```bash
python list_converted_files.py
```

**Should show:**
- `transformed_claims_adjudication.py` (from first use case)
- `transformed_sales_summary.py` (new!)

---

### Step 5: Update Pipeline
```bash
# Option 1: Use template pipeline
python update_pipeline_file.py template transformed_sales_summary.py

# Option 2: Create dedicated pipeline (in UI first), then:
python update_pipeline_file.py sales_summary transformed_sales_summary.py
```

---

### Step 6: Run Pipeline & Validate

**Run in UI:** `sas_dbx_template_tracy_anderson`

**Validate results:**
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

-- Summary by tier and churn risk
SELECT
    value_tier,
    churn_risk,
    customer_count,
    tier_revenue,
    avg_customer_revenue
FROM `na-dbxtraining`.sas_dbx_tracy_anderson_gold.sales_statistics
ORDER BY tier_revenue DESC;
```

---

## What the SAS File Does

**Input:** Bronze tables (customer, salesorderheader)

**Transformations:**
1. Filter active customers
2. Calculate order metrics (count, revenue, avg value)
3. Classify customers by value tier (High/Medium/Low)
4. Flag churn risk based on days since last order
5. Calculate customer lifetime

**Output:** 2 Gold tables
- `customer_summary` — Per-customer metrics and classifications
- `sales_statistics` — Aggregate statistics by tier and risk

---

## Production Setup (With Real SQL Server)

**When you have an actual Adventure Works database:**

### Prerequisites
- Azure SQL Server with Adventure Works
- Network access from Databricks
- UC Connection created

### Step 1: Create UC Connection
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

### Step 2: Add Lakeflow Connect Pipeline

**Add to `databricks.yml`:**
```yaml
# See lakeflow_connect_adventureworks.yml for full config
```

### Step 3: Deploy & Run Ingestion
```bash
databricks bundle deploy -t dev
databricks bundle run -t dev adventureworks_ingestion
```

### Step 4: Run Converter (Same as Mock!)
The rest of the workflow is identical — converter doesn't care where Bronze came from.

---

## Files Created

| File | Purpose |
|------|---------|
| `specifications/sales_summary.sas` | Source SAS file (sales analytics) |
| `create_adventureworks_mock_data.py` | Creates mock Bronze tables |
| `lakeflow_connect_adventureworks.yml` | Production ingestion config |
| `EXTERNAL_SOURCES_GUIDE.md` | Complete integration guide |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Mock Data (Testing)                                     │
├──────────────────────────────────────────────────────────┤
│  create_adventureworks_mock_data.py                      │
│      ↓                                                    │
│  Bronze Tables (customer, salesorderheader)              │
└──────────────────────────────────────────────────────────┘

                         OR

┌──────────────────────────────────────────────────────────┐
│  Production (Real SQL Server)                            │
├──────────────────────────────────────────────────────────┤
│  Azure SQL Server (Adventure Works)                      │
│      ↓                                                    │
│  Lakeflow Connect Ingestion Pipeline                     │
│      ↓                                                    │
│  Bronze Tables (customer, salesorderheader)              │
└──────────────────────────────────────────────────────────┘

                          ↓
                   (Same from here!)

┌──────────────────────────────────────────────────────────┐
│  Converter (Source-Agnostic)                             │
├──────────────────────────────────────────────────────────┤
│  sales_summary.sas                                       │
│      ↓                                                    │
│  Converter (13 bug fixes applied)                        │
│      ↓                                                    │
│  transformed_sales_summary.py                            │
└──────────────────────────────────────────────────────────┘

                          ↓

┌──────────────────────────────────────────────────────────┐
│  Pipeline Execution                                      │
├──────────────────────────────────────────────────────────┤
│  Bronze → Silver (transformations) → Gold (analytics)    │
│      ↓                                                    │
│  Gold Tables: customer_summary, sales_statistics         │
└──────────────────────────────────────────────────────────┘
```

---

## Comparison: Use Case 1 vs Use Case 2

| Aspect | Claims (Use Case 1) | Adventure Works (Use Case 2) |
|--------|---------------------|------------------------------|
| **Data source** | DATALINES (embedded) | SQL Server (external) |
| **Bronze ingestion** | Built-in (converter creates) | Lakeflow Connect OR mock script |
| **Complexity** | High (MERGE, RETAIN, nested IF) | Medium (JOINs, aggregations) |
| **What it proves** | Converter handles complex logic | Converter is source-agnostic |
| **Lines of SAS** | 271 | 120 |
| **Output tables** | 12 (4 Bronze, 6 Silver, 2 Gold) | 6 (2 Bronze, 2 Silver, 2 Gold) |

**Both prove end-to-end conversion with ZERO manual fixes!**

---

## Next Steps

### Test This Use Case
```bash
# 1. Create mock data
python create_adventureworks_mock_data.py

# 2. Upload SAS file (manual copy to volume)

# 3. Run converter
databricks bundle run -t dev sas_dbx_code_translator

# 4. Update pipeline
python update_pipeline_file.py template transformed_sales_summary.py

# 5. Run and validate
```

### Add More Use Cases
- **Retail:** CSV files → Auto Loader → Bronze
- **Financial:** Multi-database (Oracle + SQL Server + PostgreSQL)
- **Manufacturing:** IoT streams → Zerobus → Bronze

### Enhance Converter
Add support for `SET` passthrough (no transformation):
```python
# When SAS says: SET bronze.table;
# Output: return dlt.read("bronze.table")
```

---

## Documentation

**Full guide:** [EXTERNAL_SOURCES_GUIDE.md](EXTERNAL_SOURCES_GUIDE.md)

**Topics covered:**
- Lakeflow Connect setup
- Auto Loader patterns
- Lakehouse Federation
- Source-agnostic architecture
- Multiple data sources
- Troubleshooting

---

## Summary

**What this adds to the project:**

✅ **Second working use case** — External database integration  
✅ **Flexible testing** — Mock data OR real SQL Server  
✅ **Production-ready pattern** — Ingestion → Transformation separation  
✅ **Clear documentation** — Complete integration guide  
✅ **Scalable architecture** — Add more sources without converter changes  

**Time to test:** 10-15 minutes (with mock data) 🚀
