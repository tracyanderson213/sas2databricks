# DLT to SDP Migration Guide

**For Engineers:** This document explains the migration from legacy DLT syntax to modern SDP (Spark Declarative Pipelines) API.

---

## What Changed?

Delta Live Tables (DLT) was **rebranded** to **Spark Declarative Pipelines (SDP)** / **Lakeflow Spark Declarative Pipelines**. The product is the same, but the API has been modernized to align with PySpark conventions.

---

## Migration Summary

| Legacy DLT API | Modern SDP API | Why Changed |
|----------------|----------------|-------------|
| `import dlt` | `from pyspark import pipelines as dp` | Better namespace alignment with PySpark |
| `@dlt.table()` | `@dp.table()` | Consistent with new module |
| `@dlt.expect_*()` | `@dp.expect_*()` | Consistent with new module |
| `dlt.read("name")` | `spark.read.table("name")` | Standard PySpark API |
| `dlt.read_stream("name")` | `spark.readStream.table("name")` | Standard PySpark API |
| `FROM LIVE.table_name` (SQL) | `FROM table_name` | LIVE prefix deprecated |
| `.format("delta")` | *(optional)* | Delta is the default format |

---

## Step-by-Step Migration

### 1. Update Import Statement

**Before (Legacy DLT):**
```python
import dlt
from pyspark.sql import functions as F
```

**After (Modern SDP):**
```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F
```

---

### 2. Update Table Decorators

**Before:**
```python
@dlt.table(
    name="bronze_claims",
    comment="Raw claims data"
)
def bronze_claims():
    return spark.read.format("delta").table("raw_claims")
```

**After:**
```python
@dp.table(
    name="bronze_claims",
    comment="Raw claims data"
)
def bronze_claims():
    return spark.read.table("raw_claims")  # .format("delta") is optional
```

---

### 3. Update Expectations

**Before:**
```python
@dlt.expect_all({
    "valid_id": "id IS NOT NULL",
    "positive_amount": "amount > 0"
})
@dlt.expect_or_drop("valid_date", "date IS NOT NULL")
```

**After:**
```python
@dp.expect_all({
    "valid_id": "id IS NOT NULL",
    "positive_amount": "amount > 0"
})
@dp.expect_or_drop("valid_date", "date IS NOT NULL")
```

---

### 4. Update Table Reads

**Before:**
```python
bronze_claims = dlt.read("bronze_claims")
bronze_policies = dlt.read_stream("bronze_policies")
```

**After:**
```python
bronze_claims = spark.read.table("bronze_claims")
bronze_policies = spark.readStream.table("bronze_policies")
```

**Benefits:**
- Standard PySpark API (no custom DLT methods)
- Works in notebooks outside pipelines
- Better IDE autocomplete support

---

### 5. Update SQL References (Remove LIVE Prefix)

**Before:**
```sql
SELECT
    claim_date,
    COUNT(*) AS claim_count
FROM LIVE.silver_claims_enriched
GROUP BY claim_date
```

**After:**
```sql
SELECT
    claim_date,
    COUNT(*) AS claim_count
FROM silver_claims_enriched
GROUP BY claim_date
```

**Note:** The `LIVE.` prefix is deprecated in modern SDP pipelines.

---

## Complete Example: Before & After

### Before (Legacy DLT)

```python
import dlt
from pyspark.sql import functions as F

@dlt.table(name="bronze_orders")
def bronze_orders():
    return spark.read.format("delta").table("raw_orders")

@dlt.table(name="silver_orders_clean")
@dlt.expect_or_drop("positive_amount", "amount > 0")
def silver_orders_clean():
    orders = dlt.read("bronze_orders")
    return orders.filter(F.col("status") == "completed")

@dlt.table(name="gold_daily_summary")
def gold_daily_summary():
    return spark.sql("""
        SELECT 
            order_date,
            SUM(amount) AS total_amount
        FROM LIVE.silver_orders_clean
        GROUP BY order_date
    """)
```

### After (Modern SDP)

```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F

@dp.table(name="bronze_orders")
def bronze_orders():
    return spark.read.table("raw_orders")

@dp.table(name="silver_orders_clean")
@dp.expect_or_drop("positive_amount", "amount > 0")
def silver_orders_clean():
    orders = spark.read.table("bronze_orders")
    return orders.filter(F.col("status") == "completed")

@dp.table(name="gold_daily_summary")
def gold_daily_summary():
    return spark.sql("""
        SELECT 
            order_date,
            SUM(amount) AS total_amount
        FROM silver_orders_clean
        GROUP BY order_date
    """)
```

---

## Advanced Features (No Changes)

These features use the same syntax in both legacy DLT and modern SDP:

### Auto Loader (No Change)
```python
@dp.table(name="bronze_events")
def bronze_events():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .load("/path/to/files")
    )
```

### Streaming Tables (No Change)
```python
@dp.table(name="streaming_orders")
def streaming_orders():
    return spark.readStream.table("bronze_orders")
```

### Materialized Views (No Change)
```python
@dp.materialized_view(name="gold_aggregates")
def gold_aggregates():
    return spark.read.table("silver_cleaned")
```

### Liquid Clustering (No Change)
```python
@dp.table(
    name="partitioned_data",
    cluster_by=["state", "date"]
)
def partitioned_data():
    return spark.read.table("source")
```

---

## SQL Pipelines (No Import Changes)

SQL pipelines don't use Python imports, so the syntax is nearly identical:

**Before:**
```sql
CREATE LIVE TABLE bronze_claims
AS SELECT * FROM raw_claims;

SELECT * FROM LIVE.bronze_claims;
```

**After:**
```sql
CREATE OR REFRESH MATERIALIZED VIEW bronze_claims
AS SELECT * FROM raw_claims;

SELECT * FROM bronze_claims;  -- No LIVE prefix
```

**Changes:**
1. `CREATE LIVE TABLE` → `CREATE OR REFRESH MATERIALIZED VIEW`
2. Remove `LIVE.` prefix in FROM clauses

---

## Why Migrate?

| Benefit | Description |
|---------|-------------|
| **Future-proof** | Modern API is the officially supported syntax |
| **PySpark alignment** | Uses standard PySpark read/write patterns |
| **Better tooling** | IDE autocomplete works better with standard APIs |
| **Cleaner code** | No custom `dlt.read()` methods - just PySpark |
| **Consistency** | Same patterns work inside and outside pipelines |

---

## Backward Compatibility

**Good news:** Legacy DLT syntax still works! Databricks hasn't removed it.

**However:** New features and improvements will target the modern SDP API, so migrating is recommended for long-term maintainability.

---

## Migration Checklist

Use this checklist when migrating a pipeline:

- [ ] Replace `import dlt` with `from pyspark import pipelines as dp`
- [ ] Replace all `@dlt.*` decorators with `@dp.*`
- [ ] Replace `dlt.read("name")` with `spark.read.table("name")`
- [ ] Replace `dlt.read_stream("name")` with `spark.readStream.table("name")`
- [ ] Remove `LIVE.` prefix from SQL queries
- [ ] Remove `.format("delta")` (optional - Delta is default)
- [ ] Test pipeline with `databricks pipelines validate`
- [ ] Run full refresh to verify all tables materialize correctly

---

## Our Migration (HLS SAS DBX Claims Pipeline)

We've migrated `pipeline/claims_pipeline.py` to modern SDP syntax:

**Changes Made:**
1. ✅ `import dlt` → `from pyspark import pipelines as dp`
2. ✅ All `@dlt.*` → `@dp.*` (7 tables updated)
3. ✅ `dlt.read()` → `spark.read.table()` (4 calls updated)
4. ✅ Removed `LIVE.` prefix from SQL queries (3 locations)
5. ✅ Simplified `.format("delta")` to just `.table()` (cleaner)

**Result:** Production-ready modern SDP pipeline following latest best practices.

---

## References

- [Databricks SDP Documentation](https://docs.databricks.com/en/delta-live-tables/index.html)
- [Migration Guide (Official)](https://docs.databricks.com/en/delta-live-tables/api-migration.html)
- [PySpark API Reference](https://spark.apache.org/docs/latest/api/python/)

---

**Questions?** The pipeline in this repo (`pipeline/claims_pipeline.py`) is a complete working example of modern SDP syntax with SAS migration patterns.
