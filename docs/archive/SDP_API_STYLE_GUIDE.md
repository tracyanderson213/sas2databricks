# Apache Spark 4.1+ SDP API Style Guide

## 🎯 What Changed

**Old:** Delta Live Tables (DLT) - Databricks proprietary API  
**New:** Apache Spark Declarative Pipelines (SDP) - Open standard in Apache Spark 4.1+

Databricks contributed the core framework to Apache Spark and renamed their product:
- **Product:** Delta Live Tables → **Lakeflow Pipelines**
- **API:** `import dlt` → `from pyspark import pipelines as dp` (SDP)

---

## 📋 API Mapping (Official Apache Spark 4.1+)

| Old (DLT) | New (SDP) | Purpose |
|-----------|-----------|---------|
| `import dlt` | `from pyspark import pipelines as dp` | Import statement |
| `@dlt.table` | `@dp.table` | Persistent table (streaming or batch) |
| `@dlt.view` | `@dp.temporary_view` | Temporary view (not persisted) |
| N/A | `@dp.materialized_view` | Persistent view (new in SDP) |

---

## 🔄 What Our Converter Does

### **Input (from sas2databricks):**
```python
import dlt
from pyspark.sql import functions as F

@dlt.table(name='work_members')
def work_members():
    return spark.sql("...")

@dlt.view(name='work_claims_elig')  # Intermediate
def work_claims_elig():
    return spark.sql("...")

@dlt.table(name='clm_claims_adjudicated')  # Final
def clm_claims_adjudicated():
    return spark.sql("...")
```

### **Output (with api_style="dp"):**
```python
from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
from pyspark.sql import functions as F

@dp.table(name='bronze.work_members')  # Persistent table - Bronze layer
def work_members():
    return spark.sql("...")

@dp.materialized_view(name='silver.work_claims_elig')  # Persistent view - Silver layer
def work_claims_elig():
    return spark.sql("...")

@dp.table(name='gold.clm_claims_adjudicated')  # Persistent table - Gold layer
def clm_claims_adjudicated():
    return spark.sql("...")
```

---

## 🎨 Our Conversion Strategy

### **For Intermediate Tables (Silver layer):**
- ✅ **Use:** `@dp.materialized_view`
- **Why:** These are transformation steps that should be persisted and queryable
- **Examples:** `work_claims_elig`, `work_claims_network`, `work_claims_benefit`

### **For Persistent Tables:**
- ✅ **Use:** `@dp.table`
- **Why:** Source data (Bronze) and final outputs (Gold) need full persistence
- **Examples:** 
  - Bronze: `work_members`, `work_providers`, `work_benefit_plans`
  - Gold: `clm_claims_adjudicated`, `result`

### **Layer Prefixing:**
All table names get layer prefixes:
- `bronze.table_name` - Source/reference data
- `silver.table_name` - Transformations
- `gold.table_name` - Final aggregations/reports

---

## 🚀 How to Use

### **Widget Configuration:**

```python
# In notebook 03_convert_sas.py:
api_style = "dp"  # ← Set this to use Apache Spark 4.1+ SDP API
```

### **What You Get:**

1. ✅ **Modern API:** `from pyspark import pipelines as dp`
2. ✅ **Layer prefixes:** `bronze.`, `silver.`, `gold.`
3. ✅ **Correct decorators:**
   - `@dp.table` for persistent tables
   - `@dp.materialized_view` for persistent intermediate views
4. ✅ **Forward compatible:** Works with Apache Spark 4.1+ and Databricks Lakeflow

---

## 📊 Example: Claims Adjudication Pipeline

### **Bronze Layer (Source Data):**
```python
@dp.table(name='bronze.work_members')
def work_members():
    """Member eligibility data from DATALINES"""
    return spark.sql("...")

@dp.table(name='bronze.work_providers')
def work_providers():
    """Provider network status from DATALINES"""
    return spark.sql("...")
```

### **Silver Layer (Transformations):**
```python
@dp.materialized_view(name='silver.work_claims_elig')
def work_claims_elig():
    """Join claims with member eligibility"""
    return spark.read.table("bronze.work_members") \
        .join(spark.read.table("bronze.work_claims_in"), "member_id")

@dp.materialized_view(name='silver.work_claims_network')
def work_claims_network():
    """Add provider network status"""
    return spark.read.table("silver.work_claims_elig") \
        .join(spark.read.table("bronze.work_providers"), "provider_id")
```

### **Gold Layer (Final Outputs):**
```python
@dp.table(name='gold.clm_claims_adjudicated')
def clm_claims_adjudicated():
    """Final adjudication decisions with business logic"""
    return spark.read.table("silver.work_claims_network") \
        .withColumn("adj_status", ...) \
        .withColumn("paid_amount", ...)

@dp.table(name='gold.result')
def result():
    """Summary report: claims by status"""
    return spark.read.table("gold.clm_claims_adjudicated") \
        .groupBy("adj_status") \
        .agg(F.count("*").alias("claim_count"))
```

---

## ✅ Benefits

| Feature | Benefit |
|---------|---------|
| **Open Standard** | Portable across any SDP-compatible runtime |
| **Forward Compatible** | Apache Spark 4.1+ recommended API |
| **Layer Clarity** | `bronze.`, `silver.`, `gold.` prefixes make architecture obvious |
| **Materialized Views** | Explicit persistence for intermediate transformations |
| **Backward Compatible** | Old `import dlt` still works, no migration required |

---

## 🔄 Backward Compatibility

**Both APIs work!**

```python
# Old style - still works
import dlt
@dlt.table(name='table_name')

# New style - recommended
from pyspark import pipelines as dp
@dp.table(name='bronze.table_name')
```

Databricks recommends adopting `dp` (SDP) for new projects.

---

## 📋 Summary

**What sas2databricks generates:** `import dlt` (old API)  
**What we convert to (optional):** `from pyspark import pipelines as dp` (new Apache Spark 4.1+ SDP API)

**Why convert:**
1. ✅ Apache Spark open standard (SDP)
2. ✅ Forward compatible with Spark 4.1+
3. ✅ Clearer layer separation (`bronze.`, `silver.`, `gold.`)
4. ✅ Materialized views for persistent intermediates

**How to enable:** Set widget `api_style = "dp"` in notebook 03

**Perfect for your use case!** 🎯
