# How to Fix Your Claims Conversion Output

## 🎯 Quick Fix Guide for `claims_adjudication_comprehensive.sas`

Your converted output has these specific issues. Here's how to fix each one:

---

## Issue 1: `FROM src` - Undefined Source ❌

### **What You See:**
```python
@dp.table(name='bronze.work_members')
def work_members():
    return spark.sql("""SELECT * FROM src""")
```

### **Root Cause:**
Original SAS uses DATALINES (inline data):
```sas
data work.members;
    input member_id $ plan_id $ eff_date :mmddyy10. term_date :mmddyy10.;
    datalines;
M00001 PLNA01 01/01/2025 12/31/2025
M00002 PLNA01 01/01/2025 06/30/2025
...
;
run;
```

### **Fix - Option A: Inline Data (for Demo/Test)**

```python
@dp.temporary_view(name='bronze.work_members')  # ← Use temporary_view for small static data
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

### **Fix - Option B: External Source (for Production)**

```python
# Add to parameters section at top of file:
SOURCE_CATALOG = dbutils.widgets.get("source_catalog")  # e.g., "prod_landing"
SOURCE_SCHEMA = dbutils.widgets.get("source_schema")    # e.g., "raw"

@dp.table(name='bronze.work_members')  # ← Keep as table if it's a real external source
def work_members():
    """Member eligibility from upstream system"""
    return spark.read.table(f"{SOURCE_CATALOG}.{SOURCE_SCHEMA}.members")
```

### **Apply to All Bronze Tables:**
- `work_members` → inline data or external source
- `work_providers` → inline data or external source
- `work_benefit_plans` → inline data or external source
- `work_claims_in` → inline data or external source

---

## Issue 2: Duplicate `sort_raw` Functions ❌

### **What You See:**
```python
def sort_raw():  # Defined 5 times!
    return spark.range(0)
```

### **Root Cause:**
PROC SORT steps from SAS:
```sas
proc sort data=work.claims_in; by member_id; run;
proc sort data=work.members; by member_id; run;
```

### **Fix: DELETE ALL `sort_raw` Functions**

PROC SORT doesn't create tables—it just sorts data before the next step. In Spark, sorting is handled inline:

```python
# Don't need separate sort functions
# Instead, add .orderBy() to the consuming function if needed:

@dp.materialized_view(name='silver.work_claims_elig')
def work_claims_elig():
    """Merge claims with member eligibility"""
    claims = spark.read.table("bronze.work_claims_in")
    members = spark.read.table("bronze.work_members")
    
    return claims.join(members, "member_id", "left") \
        .orderBy("member_id")  # ← Inline sorting
```

**Action:** Delete all 5 `sort_raw` function definitions.

---

## Issue 3: SAS MERGE Syntax Didn't Convert ❌

### **What You See:**
```python
FROM (work_claims_in FULL JOIN (in=inclaim) USING (member_id) FULL JOIN work_members ...)
```

### **Root Cause:**
SAS MERGE statement:
```sas
data work.claims_elig;
    merge work.claims_in (in=inclaim)
          work.members (in=inmember);
    by member_id;
    if inclaim;
run;
```

### **Fix: Rewrite as PySpark Join**

```python
@dp.materialized_view(name='silver.work_claims_elig')
def work_claims_elig():
    """Merge claims with member eligibility"""
    claims = spark.read.table("bronze.work_claims_in")
    members = spark.read.table("bronze.work_members")
    
    # SAS: if inclaim (keep all claims, add member data if exists)
    result = claims.join(members, "member_id", "left")
    
    # Add eligibility flag
    result = result.withColumn(
        "elig_flag",
        F.when(members.member_id.isNull(), "N").otherwise("Y")
    )
    
    return result
```

---

## Issue 4: SAS Format Function ❌

### **What You See:**
```python
cast(diag_code, $diagcat.) AS diag_category
```

### **Root Cause:**
SAS PROC FORMAT:
```sas
proc format;
    value $diagcat
        'E11'  = 'DIABETES'
        'I10'  = 'HYPERTENSION'
        'J45'  = 'ASTHMA'
        'M54'  = 'BACK_PAIN'
        other  = 'OTHER';
run;

data output;
    set input;
    diag_category = put(diag_code, $diagcat.);
run;
```

### **Fix: Use F.when().otherwise()**

**Option A: Direct in the table function**
```python
@dp.table(name='gold.clm_claims_adjudicated')
def clm_claims_adjudicated():
    """Apply diagnosis category formatting"""
    return spark.read.table("silver.work_claims_running") \
        .withColumn("diag_category",
            F.when(F.col("diag_code") == "E11", "DIABETES")
             .when(F.col("diag_code") == "I10", "HYPERTENSION")
             .when(F.col("diag_code") == "J45", "ASTHMA")
             .when(F.col("diag_code") == "M54", "BACK_PAIN")
             .otherwise("OTHER")
        )
```

**Option B: Create a reusable UDF**
```python
# Add to imports section
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

# Define format mapping
DIAGCAT_FORMAT = {
    'E11': 'DIABETES',
    'I10': 'HYPERTENSION',
    'J45': 'ASTHMA',
    'M54': 'BACK_PAIN'
}

@udf(returnType=StringType())
def format_diagcat(code):
    return DIAGCAT_FORMAT.get(code, 'OTHER')

# Use in table
@dp.table(name='gold.clm_claims_adjudicated')
def clm_claims_adjudicated():
    return spark.read.table("silver.work_claims_running") \
        .withColumn("diag_category", format_diagcat(F.col("diag_code")))
```

---

## Issue 5: RETAIN (Running Totals) ⚠️

### **What You See:**
```python
CASE WHEN (row_number() OVER ... = 1) THEN 0 END AS ytd_paid
```

### **Root Cause:**
SAS RETAIN statement:
```sas
data work.claims_running;
    set work.claims_benefit;
    by member_id;
    retain ytd_paid;
    if first.member_id then ytd_paid = 0;
    ytd_paid + paid_amount;
run;
```

### **Fix: Use Window Functions**

```python
from pyspark.sql.window import Window

@dp.table(name='silver.work_claims_running')
def work_claims_running():
    """Calculate running year-to-date totals per member"""
    
    # Define window for running sum
    window = Window.partitionBy("member_id") \
                   .orderBy("service_date") \
                   .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    return spark.read.table("silver.work_claims_benefit") \
        .withColumn("ytd_paid", 
            F.sum(F.coalesce("paid_amount", F.lit(0))).over(window)
        ) \
        .withColumn("limit_exceeded",
            F.when(F.col("ytd_paid") > F.col("annual_limit"), "Y").otherwise("N")
        )
```

---

## Issue 6: Change Tables to Temporary Views 💡

### **Current (Conservative):**
```python
@dp.table(name='bronze.fmt_diagcat')         # Small format lookup
@dp.table(name='bronze.work_members')        # Small reference data (DATALINES)
@dp.table(name='bronze.work_providers')      # Small reference data (DATALINES)
@dp.table(name='bronze.work_benefit_plans')  # Small reference data (DATALINES)
```

### **Recommended (Optimized):**
```python
@dp.temporary_view(name='bronze.fmt_diagcat')         # ✅ Temp view for format lookup
@dp.temporary_view(name='bronze.work_members')        # ✅ Temp view for small ref data
@dp.temporary_view(name='bronze.work_providers')      # ✅ Temp view for small ref data
@dp.temporary_view(name='bronze.work_benefit_plans')  # ✅ Temp view for small ref data

@dp.table(name='bronze.work_claims_in')  # ✅ Keep as table (actual transaction data)
```

**Why?**
- These are small, static lookup tables from DATALINES
- They don't need persistence across pipeline runs
- `temporary_view` is more efficient for this use case

---

## 🚀 Quick Action Checklist

Use this as you fix the converted file:

### **Bronze Layer:**
- [ ] Replace all `FROM src` with inline data or external sources
- [ ] Change reference tables to `@dp.temporary_view`:
  - [ ] `fmt_diagcat`
  - [ ] `work_members`
  - [ ] `work_providers`
  - [ ] `work_benefit_plans`
- [ ] Keep `work_claims_in` as `@dp.table`

### **Silver Layer:**
- [ ] Delete all `sort_raw` function definitions (5x)
- [ ] Rewrite `work_claims_elig` - fix SAS MERGE syntax
- [ ] Rewrite `work_claims_elig2` - fix eligibility logic
- [ ] Rewrite `work_claims_network` - fix PROC SQL join
- [ ] Rewrite `work_claims_dupflag` - fix duplicate detection
- [ ] Rewrite `work_claims_benefit` - fix join logic
- [ ] Fix `work_claims_running` - use Window functions for RETAIN

### **Gold Layer:**
- [ ] Fix `clm_claims_adjudicated` - replace format function with F.when()
- [ ] Fix `result` - update table reference (clm.claims_adjudicated → gold.clm_claims_adjudicated)

---

## 📋 Expected Final Structure

```python
# Bronze (Sources & Reference Data)
@dp.temporary_view(name='bronze.fmt_diagcat')         # Format lookup
@dp.temporary_view(name='bronze.work_members')        # Reference data
@dp.temporary_view(name='bronze.work_providers')      # Reference data
@dp.temporary_view(name='bronze.work_benefit_plans')  # Reference data
@dp.table(name='bronze.work_claims_in')               # Transaction data

# Silver (Transformations)
@dp.materialized_view(name='silver.work_claims_elig')    # Join claims + members
@dp.materialized_view(name='silver.work_claims_elig2')   # Add eligibility flag
@dp.materialized_view(name='silver.work_claims_network') # Join with providers
@dp.materialized_view(name='silver.work_claims_dupflag') # Duplicate detection
@dp.materialized_view(name='silver.work_claims_benefit') # Join with benefit plans
@dp.table(name='silver.work_claims_running')             # Running totals (stateful)

# Gold (Aggregations)
@dp.table(name='gold.clm_claims_adjudicated')  # Final adjudication
@dp.table(name='gold.result')                  # Summary report
```

---

## 🎯 Test Your Fixed Pipeline

After making all fixes, test with sample data:

```python
# In a separate notebook:
from pyspark.sql import functions as F

# Test Bronze
bronze_members = spark.read.table("bronze.work_members")
print(f"Members count: {bronze_members.count()}")
bronze_members.show()

# Test Silver
silver_elig = spark.read.table("silver.work_claims_elig")
print(f"Claims with eligibility: {silver_elig.count()}")
silver_elig.show()

# Test Gold
gold_adjudicated = spark.read.table("gold.clm_claims_adjudicated")
print(f"Adjudicated claims: {gold_adjudicated.count()}")
gold_adjudicated.groupBy("adj_status").count().show()
```

---

## 💡 Pro Tip

**Run the updated converter again!** With the new post-processing logic, it will:
- Add ⚠️ markers to all these issues
- Include fix instructions as inline comments
- Recommend temporary views automatically
- Remove duplicate functions

Much easier to work with! 🚀
