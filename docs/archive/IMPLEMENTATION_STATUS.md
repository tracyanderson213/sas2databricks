# SAS → Spark Pattern Implementation Status

Based on: SAS → Spark/SQL Conversion Patterns Document

## Implementation Progress

### ✅ Phase 1: Normalization Pass (COMPLETE)

| Pattern | Status | Function | Notes |
|---------|--------|----------|-------|
| **DATALINES** | ✅ **DONE** | `parse_sas_datalines()` | Fully working - extracts INPUT + data rows → DataFrame |
| **PROC FORMAT** | ✅ **DONE** | `extract_proc_formats()` | Extracts format definitions → dictionary |
| **Macro Expansion** | ⏸️ Deferred | N/A | Complex - deferred to Phase 3 |

---

### 🚧 Phase 2: Semantic Translation Pass (IN PROGRESS)

| Pattern | Status | Function | Next Steps |
|---------|--------|----------|------------|
| **MERGE Detection** | ✅ **DONE** | `translate_merge_to_join()` | Detects patterns + join type |
| **MERGE Code Gen** | 🚧 **IN PROGRESS** | Need to add | Generate correct PySpark `.join()` |
| **RETAIN Detection** | ✅ **DONE** | `translate_retain_to_window()` | Detects running totals |
| **RETAIN Code Gen** | 🚧 **IN PROGRESS** | Need to add | Generate Window functions |
| **FIRST./LAST.** | ⏳ TODO | Need to add | ROW_NUMBER() pattern |
| **IF/THEN/ELSE** | ⏳ TODO | Need to add | Collapse to CASE WHEN |

---

### ⏳ Phase 3: Advanced Patterns (TODO)

| Pattern | Priority | Complexity | Notes |
|---------|----------|------------|-------|
| **Macro Expansion** | Medium | High | Text preprocessing - may not be worth it |
| **Table Normalization** | High | Low | Quick win - fix `work.table` → `work_table` |
| **SQL Dialect Fixes** | High | Low | Fix broken SQL from sas2databricks |

---

## What's Working Now

### ✅ **DATALINES → Inline DataFrames** (100% Automated)

**Before:**
```python
return spark.sql("""SELECT * FROM src""")
```

**After:**
```python
data = [
    ("M00001", "PLNA01", "2025-01-01", "2025-12-31"),
    ...
]
schema = "member_id STRING, plan_id STRING, eff_date DATE, term_date DATE"
return spark.createDataFrame(data, schema)
```

**Impact:** 4/4 tables in claims conversion ✅

---

### ✅ **PROC FORMAT → Dictionary Extraction** (Detection Complete)

**Detects:**
```sas
proc format;
    value $diagcat
        'E11'  = 'DIABETES'
        'I10'  = 'HYPERTENSION'
        ...
        other  = 'OTHER';
run;
```

**Extracts to:**
```python
{
    'diagcat': {
        'type': 'char',
        'mappings': {'E11': 'DIABETES', 'I10': 'HYPERTENSION', ...},
        'default': 'OTHER'
    }
}
```

**Next:** Generate dictionary + UDF code and inject into output

---

### 🚧 **MERGE → JOIN Translation** (Detection Complete, Code Gen TODO)

**Detects:**
```sas
merge work.claims_in (in=inclaim)
      work.members    (in=inmember keep=member_id eff_date term_date);
by member_id;
if inclaim;
```

**Parsed Pattern:**
```python
{
    'tables': [
        {'name': 'work_claims_in', 'in_flag': 'inclaim'},
        {'name': 'work_members', 'in_flag': 'inmember', 'keep_vars': ['member_id', 'eff_date', 'term_date']}
    ],
    'by_vars': 'member_id',
    'join_type': 'left'  # Inferred from 'if inclaim'
}
```

**Next:** Generate this PySpark code:
```python
claims = spark.read.table("bronze.work_claims_in")
members = spark.read.table("bronze.work_members").select("member_id", "eff_date", "term_date")
return claims.join(members, "member_id", "left")
```

**Impact:** Would fix 5 broken joins in claims conversion

---

### 🚧 **RETAIN → Window Functions** (Detection Complete, Code Gen TODO)

**Detects:**
```sas
data work.claims_running;
    set work.claims_benefit;
    by member_id;
    retain ytd_paid 0;
    if first.member_id then ytd_paid = 0;
    ytd_paid + billed_amount;
run;
```

**Parsed Pattern:**
```python
{
    'output_table': 'work_claims_running',
    'partition_by': 'member_id',
    'order_by': 'service_date',  # From prior PROC SORT
    'retain_var': 'ytd_paid',
    'accum_source': 'billed_amount'
}
```

**Next:** Generate this PySpark code:
```python
from pyspark.sql.window import Window

window = Window.partitionBy("member_id") \
               .orderBy("service_date") \
               .rowsBetween(Window.unboundedPreceding, Window.currentRow)

return spark.read.table("silver.work_claims_benefit") \
    .withColumn("ytd_paid", F.sum("billed_amount").over(window))
```

**Impact:** Would fix 1 running total in claims conversion

---

## Next Immediate Steps

### **1. Complete MERGE Code Generation** (Highest Value)

**File:** `notebooks/03_convert_sas.py`
**Function:** `generate_merge_join_code(merge_pattern, api_style="dp")`

**What to generate:**
```python
@dp.materialized_view(name='silver.work_claims_elig')
def work_claims_elig():
    """Merge claims with member eligibility (converted from SAS MERGE)"""
    # Table reads
    claims = spark.read.table("bronze.work_claims_in")
    members = spark.read.table("bronze.work_members").select("member_id", "eff_date", "term_date")
    
    # Join
    result = claims.join(members, "member_id", "left")
    
    # Add elig_flag based on in= logic
    return result.withColumn("elig_flag",
        F.when(F.col("eff_date").isNull(), "N").otherwise(None)
    )
```

**Then:** Replace the broken SQL in `post_process_converted_code`

---

### **2. Complete RETAIN Code Generation** (Medium Value)

**File:** `notebooks/03_convert_sas.py`
**Function:** `generate_retain_window_code(retain_pattern, api_style="dp")`

**What to generate:**
```python
@dp.table(name='silver.work_claims_running')
def work_claims_running():
    """Running totals per member (converted from SAS RETAIN)"""
    from pyspark.sql.window import Window
    
    window = Window.partitionBy("member_id") \
                   .orderBy("service_date") \
                   .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    return spark.read.table("silver.work_claims_benefit") \
        .withColumn("ytd_paid", F.sum("billed_amount").over(window)) \
        .withColumn("limit_exceeded",
            F.when(F.col("ytd_paid") > F.col("annual_limit"), "Y").otherwise("N")
        )
```

---

### **3. Add PROC FORMAT Code Generation** (Medium Value)

**Generate module-level dictionary + UDF:**
```python
# At module level after imports
from pyspark.sql.types import StringType

DIAGCAT_FORMAT = {
    'E11': 'DIABETES',
    'I10': 'HYPERTENSION',
    'J45': 'ASTHMA',
    'M54': 'BACK_PAIN'
}

@F.udf(returnType=StringType())
def format_diagcat(code):
    """Apply diagcat format (from PROC FORMAT)"""
    return DIAGCAT_FORMAT.get(code, 'OTHER')
```

**Then:** Replace `fmt_diagcat` table with this dictionary, and fix usage sites:
```python
# Replace: cast(diag_code, $diagcat.)
# With:    format_diagcat(F.col("diag_code"))
```

---

## Expected Impact After Implementation

| Metric | Current | After Code Gen | Improvement |
|--------|---------|---------------|-------------|
| **DATALINES** | ✅ 100% | ✅ 100% | ✅ Already done |
| **PROC FORMAT** | ⚠️ Placeholder | ✅ Dictionary + UDF | 🔥 **100%** |
| **MERGE joins** | ❌ Broken SQL (5×) | ✅ Correct PySpark | 🔥 **100%** |
| **RETAIN totals** | ❌ Wrong logic (1×) | ✅ Correct Window | 🔥 **100%** |
| **Manual fixes** | 30-50% | **5-10%** | 🔥 **6-10x better** |

---

## Timeline

| Phase | Effort | Status |
|-------|--------|--------|
| Pattern Detection | 2-3 days | ✅ **DONE** |
| Code Generation | 2-3 days | 🚧 **IN PROGRESS** |
| Integration & Testing | 1-2 days | ⏳ TODO |
| **Total** | **5-8 days** | **60% complete** |

---

## Current Session Progress

✅ Created pattern detection functions:
- `extract_proc_formats()`
- `translate_merge_to_join()`
- `translate_retain_to_window()`

✅ Integrated into post-processor:
- Detection runs in normalization pass
- Results logged in POST-PROCESSING SUMMARY

🚧 **Next:** Add code generation functions that actually FIX the broken output

---

## Files Modified

1. **`notebooks/03_convert_sas.py`**
   - Added PROC FORMAT extractor
   - Added MERGE translator
   - Added RETAIN translator
   - Integrated detection into post-processor

2. **`IMPLEMENTATION_STATUS.md`** (this file)
   - Tracks progress
   - Documents what's working
   - Shows next steps

---

## How to Continue

**Pick up where we left off:**

1. Add `generate_merge_join_code()` function
2. Add `generate_retain_window_code()` function
3. Add `generate_format_dict_code()` function
4. Update `post_process_converted_code()` to actually replace broken code
5. Test on claims conversion
6. Verify all 5 MERGE issues are fixed
7. Verify RETAIN issue is fixed
8. Verify PROC FORMAT issue is fixed

**Estimated remaining effort:** 2-3 days

**Expected result:** Reduce manual fixes from 30-50% to 5-10%! 🚀
