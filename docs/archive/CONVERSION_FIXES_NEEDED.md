# Conversion Fixes Needed for claims_adjudication_comprehensive.sas

## 🚨 Critical Issues to Fix

### 1. **Replace `src` Placeholder** ❌

**Problem:** All Bronze tables have `SELECT * FROM src` which is undefined.

**Fix Options:**

#### Option A: Inline Data (for demo/test)
```python
@dp.temporary_view(name='bronze.work_members')
def work_members():
    """Member eligibility data from DATALINES"""
    data = [
        ("M00001", "PLNA01", "2025-01-01", "2025-12-31"),
        ("M00002", "PLNA01", "2025-01-01", "2025-06-30"),
        ("M00003", "PLNB02", "2025-03-01", "2025-12-31"),
        ("M00004", "PLNB02", "2025-01-01", "2025-12-31"),
    ]
    schema = "member_id STRING, plan_id STRING, eff_date DATE, term_date DATE"
    return spark.createDataFrame(data, schema)
```

#### Option B: External Source (for production)
```python
@dp.table(name='bronze.work_members')
def work_members():
    """Member eligibility from source system"""
    return spark.read.table("raw_source.members") \
        .select("member_id", "plan_id", "eff_date", "term_date")
```

---

### 2. **Fix View/Table Designations** ✅

#### **Current (Incorrect):**
```python
@dp.table(name='bronze.fmt_diagcat')        # ❌ Small lookup
@dp.table(name='bronze.work_members')       # ❌ Static reference
@dp.table(name='bronze.work_providers')     # ❌ Static reference
@dp.table(name='bronze.work_benefit_plans') # ❌ Static reference
```

#### **Should Be:**
```python
@dp.temporary_view(name='bronze.fmt_diagcat')        # ✅ Format lookup
@dp.temporary_view(name='bronze.work_members')       # ✅ Small reference (DATALINES)
@dp.temporary_view(name='bronze.work_providers')     # ✅ Small reference (DATALINES)
@dp.temporary_view(name='bronze.work_benefit_plans') # ✅ Small reference (DATALINES)
@dp.table(name='bronze.work_claims_in')              # ✅ Actual transactions (keep as table)
```

**Why:**
- **Temporary views**: Small, static reference data from DATALINES (doesn't need persistence)
- **Tables**: Actual transaction data that should be persisted

---

### 3. **Remove Duplicate `sort_raw` Definitions** ❌

**Problem:** 5 functions named `sort_raw` (Python can't have duplicate function names)

```python
def sort_raw():  # ❌ Defined 5 times!
    return spark.range(0)
```

**Fix:** Delete all `sort_raw` functions. PROC SORT in SAS doesn't create tables—it just sorts data before the next step. In Spark, sorting is handled inline with `.orderBy()`:

```python
# Don't need separate sort functions
# Just add .orderBy() to the consuming function:

@dp.materialized_view(name='silver.work_claims_elig')
def work_claims_elig():
    return spark.read.table("bronze.work_claims_in") \
        .join(spark.read.table("bronze.work_members"), "member_id", "left") \
        .orderBy("member_id")  # ← Inline sorting
```

---

### 4. **Fix Broken SQL Conversions** ❌

#### **Problem A: SAS MERGE syntax leaked through**
```python
# ❌ BROKEN:
FROM (work_claims_in FULL JOIN (in=inclaim) USING (member_id) FULL JOIN work_members ...)
```

**Fix:**
```python
@dp.materialized_view(name='silver.work_claims_elig')
def work_claims_elig():
    """Merge claims with member eligibility"""
    claims = spark.read.table("bronze.work_claims_in")
    members = spark.read.table("bronze.work_members")
    
    return claims.join(members, "member_id", "left") \
        .withColumn("elig_flag", F.when(members.member_id.isNull(), "N").otherwise("Y"))
```

#### **Problem B: SAS format function didn't convert**
```python
# ❌ BROKEN:
cast(diag_code, $diagcatNULL) AS diag_category
```

**Fix:**
```python
@dp.table(name='gold.clm_claims_adjudicated')
def clm_claims_adjudicated():
    """Apply diagnosis category format"""
    return spark.read.table("silver.work_claims_running") \
        .withColumn("diag_category", 
            F.when(F.col("diag_code") == "E11", "DIABETES")
             .when(F.col("diag_code") == "I10", "HYPERTENSION")
             .when(F.col("diag_code") == "J45", "ASTHMA")
             .when(F.col("diag_code") == "M54", "BACK_PAIN")
             .otherwise("OTHER")
        )
```

---

### 5. **Fix RETAIN Logic (Running Totals)** ⚠️

**Problem:** SAS `RETAIN` statement for running totals didn't convert properly.

**Original SAS:**
```sas
data work.claims_running;
    set work.claims_benefit;
    by member_id;
    retain ytd_paid;
    if first.member_id then ytd_paid = 0;
    ytd_paid + paid_amount;
run;
```

**Fix (Window Functions):**
```python
@dp.table(name='silver.work_claims_running')
def work_claims_running():
    """Calculate running year-to-date totals per member"""
    from pyspark.sql.window import Window
    
    window = Window.partitionBy("member_id") \
                   .orderBy("service_date") \
                   .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    return spark.read.table("silver.work_claims_benefit") \
        .withColumn("ytd_paid", F.sum("paid_amount").over(window)) \
        .withColumn("limit_exceeded", 
            F.when(F.col("ytd_paid") > F.col("annual_limit"), "Y").otherwise("N")
        )
```

---

## 📋 Summary of Changes

| Item | Current | Should Be | Reason |
|------|---------|-----------|--------|
| `fmt_diagcat` | `@dp.table` | `@dp.temporary_view` | Small format lookup |
| `work_members` | `@dp.table` + `FROM src` | `@dp.temporary_view` + inline data | DATALINES reference data |
| `work_providers` | `@dp.table` + `FROM src` | `@dp.temporary_view` + inline data | DATALINES reference data |
| `work_benefit_plans` | `@dp.table` + `FROM src` | `@dp.temporary_view` + inline data | DATALINES reference data |
| `work_claims_in` | `FROM src` | Real source or inline data | Replace placeholder |
| `sort_raw` (5x) | 5 duplicate functions | Delete all | PROC SORT doesn't create tables |
| MERGE syntax | Broken SQL | PySpark `.join()` | SAS syntax leaked through |
| Format function | `cast(x, $format)` | `F.when().otherwise()` | SAS format didn't convert |
| RETAIN | Broken | Window functions | Running totals need window |

---

## 🎯 Next Steps

**Want me to:**
1. ✅ Create a corrected version with all fixes applied?
2. ✅ Show you the inline data approach for DATALINES?
3. ✅ Fix just the critical issues (src, duplicates, SQL)?

Let me know which approach you prefer! 🚀
