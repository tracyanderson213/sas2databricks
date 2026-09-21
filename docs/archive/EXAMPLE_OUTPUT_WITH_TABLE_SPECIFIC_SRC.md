# Example: Table-Specific SRC Placeholders

## 🎯 Your Great Idea Implemented!

Instead of generic `FROM src` for every table, the converter now uses **table-specific placeholders** like:
- `FROM SRC_work_members`
- `FROM SRC_work_providers`
- `FROM SRC_work_claims_in`

Plus, it adds **context-aware guidance** (dictionary vs view vs external source).

---

## Example Output

### **Bronze Reference Data (DATALINES) → Dictionary or Temp View**

```python
@dp.temporary_view(name='bronze.work_members')
def work_members():
    return spark.sql("""SELECT *
FROM SRC_work_members
    -- ⚠️ REPLACE 'SRC_work_members' WITH ONE OF:
    --
    -- Option A (Small Lookup <100 rows): Python Dictionary + UDF
    --   - Best for: Format mappings, simple key-value lookups
    --   - Example: DIAGCAT_FORMAT = {'E11': 'DIABETES', 'I10': 'HTN'}
    --   - Use: .withColumn("category", format_udf(F.col("code")))
    --
    -- Option B (Reference Data 100-10K rows): Inline DataFrame → Temporary View
    --   - Best for: Reference tables used in joins (members, providers, plans)
    --   - Pattern:
    --     data = [("M001", "PLAN1", "2025-01-01"), ...]
    --     schema = "member_id STRING, plan_id STRING, eff_date DATE"
    --     return spark.createDataFrame(data, schema)
    --
    -- Option C (External Source): Widget-driven source table
    --   - Best for: Production external data
    --   - Pattern: spark.read.table(f"{SOURCE_CATALOG}.{SOURCE_SCHEMA}.work_members")
    --
""")
```

### **Bronze Transaction Data → External Source**

```python
@dp.table(name='bronze.work_claims_in')
def work_claims_in():
    return spark.sql("""SELECT *
FROM SRC_work_claims_in
    -- ⚠️ REPLACE 'SRC_work_claims_in' WITH EXTERNAL SOURCE:
    --
    -- Option A (Unity Catalog Table):
    --   spark.read.table("{SOURCE_CATALOG}.{SOURCE_SCHEMA}.work_claims_in")
    --
    -- Option B (Volume Path):
    --   spark.read.parquet("/Volumes/{CATALOG}/{SCHEMA}/landing/work_claims_in/")
    --
    -- Option C (External Location):
    --   spark.read.format("delta").load("s3://bucket/path/work_claims_in/")
    --
    -- Add widgets at top of file:
    --   SOURCE_CATALOG = dbutils.widgets.get("source_catalog")
    --   SOURCE_SCHEMA = dbutils.widgets.get("source_schema")
    --
""")
```

---

## Benefits

### **1. Clear Which Source to Replace** ✅
```python
# ❌ OLD (confusing):
FROM src  # work_members? work_providers? Who knows!
FROM src  # Same placeholder everywhere

# ✅ NEW (crystal clear):
FROM SRC_work_members   # Ah, this is the members table!
FROM SRC_work_providers # And this is providers
```

### **2. Selective Find/Replace** ✅
```python
# Can target specific tables:
# Find: SRC_work_members
# Replace with actual source

# Don't have to fix all tables at once!
```

### **3. Context-Aware Guidance** ✅
- **DATALINES reference data** → Gets dictionary vs temp view guidance
- **Transaction data** → Gets external source guidance
- **Each placeholder has relevant examples**

---

## Dictionary vs Temporary View Guide

### **Use Dictionary When:**
```python
# ✅ Simple format mappings (PROC FORMAT)
DIAGCAT_FORMAT = {
    'E11': 'DIABETES',
    'I10': 'HYPERTENSION',
    'J45': 'ASTHMA',
}

@udf(returnType=StringType())
def format_diagcat(code):
    return DIAGCAT_FORMAT.get(code, 'OTHER')

# Use in transformations
df.withColumn("diag_category", format_diagcat(F.col("diag_code")))
```

**Best for:**
- ✅ < 100 rows
- ✅ Simple key-value lookups
- ✅ Format mappings (PROC FORMAT → dictionary)
- ✅ Single column lookups

---

### **Use Temporary View When:**
```python
# ✅ Reference tables used in joins
@dp.temporary_view(name='bronze.work_members')
def work_members():
    """Member eligibility lookup"""
    data = [
        ("M00001", "PLNA01", "2025-01-01", "2025-12-31"),
        ("M00002", "PLNA01", "2025-01-01", "2025-06-30"),
        ("M00003", "PLNB02", "2025-03-01", "2025-12-31"),
    ]
    schema = "member_id STRING, plan_id STRING, eff_date DATE, term_date DATE"
    return spark.createDataFrame(data, schema)

# Use in joins
claims.join(spark.read.table("bronze.work_members"), "member_id", "left")
```

**Best for:**
- ✅ 100-10K rows
- ✅ Multiple columns
- ✅ Used in joins (members, providers, plans)
- ✅ Need SQL query capability
- ✅ Broadcast automatically when small

---

## POST-PROCESSING SUMMARY Example

```python
# ==============================================================================
# POST-PROCESSING SUMMARY
# ==============================================================================
# Automatic fixes applied:
#   ✓ Replaced generic 'src' with table-specific placeholders (SRC_<table_name>)
#   ✓ Added guidance: dictionary vs temporary view for DATALINES
#   ✓ Removed all PROC SORT artifacts (sort_raw functions)
#
# ⚠️  Manual review required:
#   ⚠️  'work_members': Replace SRC_work_members with inline data (dictionary or temp view)
#   ⚠️  'work_providers': Replace SRC_work_providers with inline data (dictionary or temp view)
#   ⚠️  'fmt_diagcat': Replace SRC_fmt_diagcat with inline data (dictionary or temp view)
#   ⚠️  'work_claims_in': Replace SRC_work_claims_in with external source
#
# 💡 Recommendations:
#   - Consider using @dp.temporary_view for small reference data:
#     • work_members (DATALINES)
#     • work_providers (DATALINES)
#     • work_benefit_plans (DATALINES)
#   - Consider Python dictionary for format lookups:
#     • fmt_diagcat (PROC FORMAT)
# ==============================================================================
```

---

## Real Example: Fix Format Lookup

### **Original SAS:**
```sas
proc format;
    value $diagcat
        'E11' = 'DIABETES'
        'I10' = 'HYPERTENSION'
        'J45' = 'ASTHMA'
        other = 'OTHER';
run;

data output;
    set input;
    diag_category = put(diag_code, $diagcat.);
run;
```

### **Converted Output (with new placeholder):**
```python
@dp.table(name='bronze.fmt_diagcat')
def fmt_diagcat():
    return spark.sql("""SELECT *
FROM SRC_fmt_diagcat
    -- ⚠️ REPLACE 'SRC_fmt_diagcat' WITH ONE OF:
    -- Option A (Small Lookup <100 rows): Python Dictionary + UDF
    --   Example: DIAGCAT_FORMAT = {'E11': 'DIABETES', 'I10': 'HTN'}
    -- ...
""")
```

### **Recommended Fix (Dictionary):**
```python
# Remove the table entirely, replace with dictionary at module level:

# After imports section:
DIAGCAT_FORMAT = {
    'E11': 'DIABETES',
    'I10': 'HYPERTENSION',
    'J45': 'ASTHMA',
    'M54': 'BACK_PAIN'
}

@udf(returnType=StringType())
def format_diagcat(code):
    """Apply diagnosis category formatting"""
    return DIAGCAT_FORMAT.get(code, 'OTHER')

# Use in downstream table:
@dp.table(name='gold.clm_claims_adjudicated')
def clm_claims_adjudicated():
    return spark.read.table("silver.work_claims_running") \
        .withColumn("diag_category", format_diagcat(F.col("diag_code")))
```

---

## Summary

### **Your Questions:**
1. **"Should DATALINES be dictionary or lookup view?"**  
   ✅ **Answer:** Depends on size and usage:
   - Dictionary: < 100 rows, simple key-value
   - Temporary view: 100-10K rows, multiple columns, joins

2. **"Should each table have different SRC?"**  
   ✅ **Answer:** YES! Now implemented:
   - `SRC_work_members`
   - `SRC_work_providers`
   - `SRC_work_claims_in`
   - Each has context-specific guidance

### **Benefits:**
- ✅ Clear which placeholder is which table
- ✅ Can fix tables one at a time
- ✅ Context-aware recommendations
- ✅ Easier to track what's been fixed

🚀 **Ready to test!**
