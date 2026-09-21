# Adventure Works Real Data Available! 🎉

**Great news:** You have access to the **full Adventure Works database** with real production data!

---

## Verified Data Availability

### Database Connection
- **Server:** `sqldbdbxtraining.database.windows.net`
- **Database:** `sqldb-adventureworks`
- **Version:** Full Adventure Works (not AdventureWorksLT)
- **Total Tables:** 68 tables

### Key Tables for SAS Migration Demo

| Schema | Table | Rows | Status |
|--------|-------|------|--------|
| Sales | Customer | 19,820 | ✅ Available |
| Sales | SalesOrderHeader | 31,465 | ✅ Available |

**This is REAL production data** — much better than mock data for demos!

---

## Next Steps: Use Real Data Instead of Mock

### Option A: Lakeflow Connect (Recommended for Production)

**Set up ingestion pipeline to pull real data into Bronze:**

```bash
# 1. Verify connection exists
databricks connections get adventureworks_sql

# 2. Deploy Lakeflow Connect pipeline
databricks bundle deploy -t dev

# 3. Run ingestion
databricks bundle run -t dev adventureworks_ingestion

# This will create:
# - sas_tanderson_bronze.customer (19,820 rows from real DB)
# - sas_tanderson_bronze.salesorderheader (31,465 rows from real DB)
```

**Config:** `lakeflow_connect_adventureworks.yml`

### Option B: Direct Query (Quick Testing)

**Read directly from SQL Server without ingestion:**

```python
# Use JDBC to read directly (for quick tests)
# See: check_adventureworks_tables_notebook.py for working example

# Then manually create Bronze tables:
# CREATE TABLE sas_tanderson_bronze.customer AS 
# SELECT * FROM jdbc_customer;
```

### Option C: Mock Data (Offline Testing)

**Still works if SQL Server is unavailable:**

```bash
python create_adventureworks_mock_data.py
# Creates 50 customers, 200 orders (synthetic)
```

---

## Run Conversion with Real Data

Once you have real data in Bronze (via Lakeflow Connect or direct query):

```bash
# Run the sales summary conversion
./run_sales_summary_test.sh

# Or manually:
# 1. Upload SAS file
databricks fs cp specifications/sales_summary.sas \
  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/

# 2. Run converter
databricks bundle run -t dev sas_dbx_code_translator

# 3. Deploy pipeline
databricks bundle deploy -t dev

# 4. Verify Gold output
SELECT * FROM sas_tanderson_gold.customer_summary LIMIT 10;
# Should have ~19,820 customers (or fewer after filters)
```

---

## Demo Value: Real vs Mock Data

### Mock Data (50 customers, 200 orders)
- ✅ Good for: Quick testing, offline work
- ❌ Limited: Doesn't show scalability
- ❌ Not impressive: Obviously fake data

### Real Data (19,820 customers, 31,465 orders)
- ✅ Production-scale: Shows real-world performance
- ✅ Credible: Executives see actual business data
- ✅ Complete workflow: Ingestion → Transformation → Analytics
- ✅ Impressive: "This is running on 20K+ real customers"

---

## Technical Note: SQL Server ORDER BY Restriction

**Issue:** SQL Server prohibits `ORDER BY` in derived tables/subqueries unless `TOP` or `OFFSET` is also specified.

**Why it matters:** Spark JDBC wraps queries as `(SELECT ... ORDER BY ...) AS subquery`, which triggers SQL Server error.

**Solution:** Remove `ORDER BY` from queries read via JDBC.

**Example:**

```python
# ❌ FAILS with Spark JDBC
query = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME  -- <-- Problem!
"""

# ✅ WORKS with Spark JDBC
query = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
-- ORDER BY removed; sort in Spark instead
"""

# Sort in Spark after loading
df = spark.read.jdbc(jdbc_url, f"({query}) AS t", properties)
df_sorted = df.orderBy("TABLE_SCHEMA", "TABLE_NAME")
```

**Reference:** `check_adventureworks_tables_notebook.py` (updated with working version)

---

## Updated Workflow Recommendation

### For Demos & Presentations:

1. **Use Lakeflow Connect** to ingest 19,820 real customers
2. **Run converter** on `sales_summary.sas`
3. **Show Gold output** with real customer analytics
4. **Highlight:** "This processed 20K customers and 31K orders in X minutes"

### For Development & Testing:

1. **Use mock data** (50 customers) for quick iteration
2. **Test with real data** before demos to verify scale
3. **Keep both options** in documentation

---

## Files Updated

- ✅ `check_adventureworks_tables_notebook.py` — Fixed ORDER BY issue
- ✅ `ADVENTURE_WORKS_DATA_AVAILABLE.md` — This file (new)
- 📝 Next: Update `run_sales_summary_test.sh` to add real data option

---

**Bottom line:** You have access to production-scale Adventure Works data. Use it for impressive demos! 🚀
