# Adventure Works Use Case

**External Database Integration Demo — SQL Server → Bronze → Silver → Gold**

---

## Overview

This use case demonstrates:
- ✅ **External database ingestion** — SQL Server → Databricks Bronze
- ✅ **Real production data** — 19,820 customers, 31,465 orders
- ✅ **Three ingestion patterns** — Lakeflow Connect, Direct JDBC, Mock data
- ✅ **Data quality expectations** — 20+ validation checks
- ✅ **Medallion architecture** — Bronze → Silver → Gold transformation

**Bronze Tables (Adventure Works):**
- `sas_tanderson_bronze.customer`
- `sas_tanderson_bronze.salesorderheader`

**Note:** Separate from the comprehensive use case which uses `work_benefit_plans` and `work_claims_in`.

---

## Directory Structure

```
use-cases/adventureworks/
├── README.md                           # This file
├── lakeflow_connect_adventureworks.yml # Lakeflow Connect config
├── scripts/                            # Python & Shell scripts
│   ├── check_adventureworks_tables.py         # Check what tables exist
│   ├── check_adventureworks_tables.sql        # SQL validation queries
│   ├── check_adventureworks_tables_notebook.py # Databricks notebook version
│   ├── create_adventureworks_mock_data.py     # Generate 50 synthetic customers
│   ├── ingest_real_adventureworks_data.py     # Direct JDBC ingestion (19K real)
│   ├── verify_bronze_tables.py                # Verify Bronze data loaded
│   └── run_with_real_data.sh                  # End-to-end workflow script
├── specifications/                     # SAS source files
│   ├── sales_summary.sas                      # Original (no expectations)
│   └── sales_summary_with_expectations.sas    # Enhanced (20+ checks)
└── documentation/                      # Use case docs
    ├── ADVENTURE_WORKS_DATA_AVAILABLE.md      # Data availability overview
    ├── ADVENTURE_WORKS_EXPECTATIONS_GUIDE.md  # Testing expectations guide
    ├── ADVENTURE_WORKS_README.md              # Setup guide
    └── SETUP_ADVENTUREWORKS_INGESTION.md      # Step-by-step ingestion setup
```

---

## Quick Start

### **Option 1: Lakeflow Connect (Production Pattern)** ✅ Recommended

```bash
cd use-cases/adventureworks

# 1. Deploy Lakeflow Connect pipeline
databricks bundle deploy -t dev

# 2. Run ingestion (19,820 customers from SQL Server)
databricks bundle run -t dev adventureworks_ingestion

# 3. Verify Bronze tables
python scripts/verify_bronze_tables.py

# 4. Run converter on SAS file
databricks fs cp specifications/sales_summary.sas \
  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/ --overwrite

databricks bundle run -t dev sas_dbx_code_translator
```

### **Option 2: Direct JDBC (Quick Testing)**

```bash
cd use-cases/adventureworks

# Direct copy from SQL Server to Bronze (bypasses pipeline)
python scripts/ingest_real_adventureworks_data.py

# Verify and proceed with converter
python scripts/verify_bronze_tables.py
```

### **Option 3: Mock Data (Offline Testing)**

```bash
cd use-cases/adventureworks

# Generate 50 synthetic customers + 200 orders
python scripts/create_adventureworks_mock_data.py

# Verify and proceed
python scripts/verify_bronze_tables.py
```

---

## Data Flow

```
┌────────────────────────────────────────────────────────┐
│ Azure SQL Server                                       │
│  • sqldbdbxtraining.database.windows.net              │
│  • Database: sqldb-adventureworks                     │
│  • Sales.Customer (19,820 rows)                       │
│  • Sales.SalesOrderHeader (31,465 rows)               │
└────────────────────────────────────────────────────────┘
                       │
                       │ Lakeflow Connect / JDBC
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ Bronze Layer (sas_tanderson_bronze)                   │
│  • customer (Delta table)                             │
│  • salesorderheader (Delta table)                     │
└────────────────────────────────────────────────────────┘
                       │
                       │ SDP Pipeline (Converted SAS)
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ Silver Layer (sas_tanderson_silver)                   │
│  • customers (filtered, enriched)                     │
│  • orders (calculated fields)                         │
│  • customer_metrics (joined, aggregated)              │
└────────────────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ Gold Layer (sas_tanderson_gold)                       │
│  • customer_summary (analytics-ready)                 │
│  • sales_statistics (KPIs, cross-tabs)                │
└────────────────────────────────────────────────────────┘
```

---

## SAS Files

### **sales_summary.sas** — Basic Version
- No data quality expectations
- Simple transformation: Bronze → Silver → Gold
- Good for initial testing
- **Uses:** `sas_tanderson_bronze.customer`, `sas_tanderson_bronze.salesorderheader`

### **sales_summary_with_expectations.sas** — Production Version
- 20+ data quality checks
- Validates:
  - Bronze: IDs, dates, amounts, math reconciliation
  - Silver: Metrics, classifications, business rules
  - Gold: Aggregations, completeness
- Expectations are commented out by converter for manual review
- **Uses:** Same Adventure Works Bronze tables

**See:** `documentation/ADVENTURE_WORKS_EXPECTATIONS_GUIDE.md` for testing scenarios

---

## Key Features Demonstrated

1. **External Database Integration**
   - SQL Server → Databricks via Lakeflow Connect
   - CDC-capable ingestion
   - Schema: `Sales.Customer`, `Sales.SalesOrderHeader`

2. **Medallion Architecture**
   - Bronze: Raw Delta tables from SQL Server
   - Silver: Business transformations (views for optimization)
   - Gold: Analytics-ready tables

3. **Data Quality Expectations**
   - Converter generates `@dp.expect()` decorators
   - Comments them out for manual review
   - Test with real data (19,820 rows)

4. **Three Ingestion Patterns**
   - Production: Lakeflow Connect (CDC, managed)
   - Testing: Direct JDBC (faster iteration)
   - Offline: Mock data generator (no SQL Server needed)

---

## Schema Naming

**Pattern:** `sas_{developer_id}_{layer}`

**Example:**
- `sas_tanderson_bronze`
- `sas_tanderson_silver`
- `sas_tanderson_gold`

**Volume:** `/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration`

---

## Documentation

| File | Purpose |
|------|---------|
| `ADVENTURE_WORKS_DATA_AVAILABLE.md` | Data availability (19K customers) |
| `ADVENTURE_WORKS_EXPECTATIONS_GUIDE.md` | Testing expectations with real data |
| `ADVENTURE_WORKS_README.md` | Setup overview |
| `SETUP_ADVENTUREWORKS_INGESTION.md` | Step-by-step ingestion setup |

---

## Troubleshooting

### **Bronze tables not found**
```bash
# Check schema naming
python scripts/verify_bronze_tables.py

# Correct pattern: sas_tanderson_bronze.customer
```

### **SQL Server connection issues**
```bash
# Test connection
databricks connections get adventureworks_sql

# Should show: "state": "READY"
```

### **ORDER BY errors with JDBC**
SQL Server prohibits `ORDER BY` in subqueries unless `TOP` or `OFFSET` is specified.

**Fix:** Remove `ORDER BY` from source query, sort in Spark instead.

**See:** `../../SQL_SERVER_JDBC_NOTES.md`

---

## Related Files

- **Main Bundle:** `../../databricks.yml` (defines `adventureworks_ingestion` pipeline)
- **Architecture:** `../../docs/architecture/SAS_MIGRATION_ARCHITECTURE.md`
- **Schema Fix:** `../../SCHEMA_NAMING_FIX.md`
- **Technical Ref:** `../../CONVERTED_CODE_FEATURES.md`

---

## Next Steps

1. ✅ **Seed Bronze** — Choose ingestion method (Lakeflow/JDBC/Mock)
2. ✅ **Run Converter** — Convert `sales_summary.sas` or `sales_summary_with_expectations.sas`
3. ✅ **Deploy Pipeline** — Create transformation pipeline from converted code
4. ✅ **Verify Gold** — Query `sas_tanderson_gold.customer_summary`
5. ✅ **Enable Expectations** — Uncomment `@dp.expect()` decorators after review

---

**Ready to test? Start with:** `scripts/run_with_real_data.sh` 🎯
