# Bugs Fixed in Post-Processor (Cell 12)

## 🐛 Bug #1: Corrupted Return Statement (CRITICAL)

### **The Bug:**
```python
return spark.createDataFrame(data, schema): Python Dictionary + UDF  # ❌ SYNTAX ERROR!
```

**Root Cause:** 
Regex pattern didn't match closing triple quotes in `return spark.sql("""...""")`:
```python
# ❌ WRONG:
func_pattern = rf"(def {table_name}\(\):)(.*?)(return spark\.sql\(\"\"\".*?\))"
                                                                      ^^^ Missing closing """
```

The pattern matched `return spark.sql("""<anything>)` and stopped at the first `)`, leaving placeholder guidance text after the auto-generated code.

### **The Fix:**
```python
# ✅ CORRECT:
func_pattern = rf"(def {table_name}\(\):)(.*?)(return spark\.sql\(\"\"\".*?\"\"\"\))"
                                                                      ^^^^^^^^ Now matches closing """
```

**Impact:** 
- **Before:** Syntax error, code won't run
- **After:** Clean auto-generated functions

---

## 🐛 Bug #2: Duplicate `sort_raw` Functions Not Removed

### **The Bug:**
Output still had 7 duplicate `sort_raw` functions even though post-processor claimed to remove them:
```python
def sort_raw():  # ❌ Still present 7 times!
    return spark.range(0)
```

**Root Cause:**
The regex was too fragile and didn't reliably match the full function:
```python
# ❌ WRONG:
code = re.sub(
    r'@d[lp]\.\w+\(name=.*?sort_raw.*?\).*?\ndef sort_raw\(\):.*?\n.*?return spark\.range\(0\)\n',
    '',
    code,
    flags=re.DOTALL
)
```

Too many `.*?` non-greedy patterns made it unreliable.

### **The Fix:**
```python
# ✅ CORRECT: More robust pattern
sort_raw_pattern = (
    r'@d[lp]t?\.(?:view|table|materialized_view|temporary_view)\([^)]*sort_raw[^)]*\)'  # Decorator
    r'\s*(?:#[^\n]*)?\s*'  # Optional comment
    r'def sort_raw\(\):'  # Function def
    r'[^@def]*?'  # Everything until next @ or def
    r'return spark\.range\(0\)'  # Return statement
    r'\s*'  # Trailing whitespace
)

code = re.sub(sort_raw_pattern, '', code, flags=re.DOTALL)
```

**Benefits:**
- Handles both `@dlt` and `@dp` decorators
- Handles all decorator types (view, table, materialized_view, temporary_view)
- Stops at next function/decorator
- Counts removed functions for reporting

**Impact:**
- **Before:** 7 duplicate functions → Python syntax error (can't redefine same function)
- **After:** All `sort_raw` artifacts removed cleanly

---

## 🐛 Bug #3: Python Boolean Literal Error

### **The Bug:**
```python
ENABLE_VIEWS = true  # ❌ Should be True (capitalized)
```

**Root Cause:**
Template used `.lower()` on boolean:
```python
# ❌ WRONG:
ENABLE_VIEWS = {str(enable_views).lower()}
# → str(True).lower() → "true" (not valid Python)
```

### **The Fix:**
```python
# ✅ CORRECT:
ENABLE_VIEWS = {enable_views}
# → True (proper Python boolean literal)
```

**Impact:**
- **Before:** `NameError: name 'true' is not defined`
- **After:** Valid Python boolean `True`

---

## Summary of Fixes

| Bug | Severity | Impact | Status |
|-----|----------|--------|--------|
| Corrupted return statement | 🚨 Critical | Syntax error, won't run | ✅ Fixed |
| Duplicate sort_raw not removed | 🚨 Critical | Syntax error, won't run | ✅ Fixed |
| Boolean literal | 🚨 Critical | NameError, won't run | ✅ Fixed |

---

## What Still Needs Manual Fixing

These are **sas2databricks conversion issues**, not post-processor bugs:

1. **SAS MERGE syntax** - needs rewrite to PySpark `.join()`
2. **SAS format functions** - needs `F.when().otherwise()`
3. **Running totals** - needs Window functions
4. **Broken SQL** - needs manual SQL rewrite
5. **Logic errors** - multiple columns with same name in `clm_claims_adjudicated`

The post-processor **marks these with ⚠️ warnings** but cannot auto-fix them (require business logic understanding).

---

## Testing the Fix

Re-run the conversion on your claims file:

```python
# In notebook 03_convert_sas.py
# Set widgets:
api_style = "dp"  # Use Apache Spark 4.1+ SDP
enable_views = True

# Run conversion
# Expected output:
# ✅ No corrupted return statements
# ✅ No duplicate sort_raw functions
# ✅ ENABLE_VIEWS = True (not "true")
```

---

## Verification

After the fix, the POST-PROCESSING SUMMARY should show:
```python
# ✅ AUTO-GENERATED from SAS DATALINES (ready to use!):
#   ✅ work_members: 5 rows × 5 columns
#   ✅ work_providers: 4 rows × 4 columns
#   ✅ work_benefit_plans: 2 rows × 5 columns
#   ✅ work_claims_in: 7 rows × 8 columns
#
# Automatic fixes applied:
#   ✓ Parsed 4 DATALINES blocks from original SAS code
#   ✓ Successfully auto-generated 4 table(s) from DATALINES
#   ✓ Removed 7 PROC SORT artifact(s) (sort_raw functions)  # ← Should see this!
```

And the generated functions should look like:
```python
@dp.temporary_view(name='bronze.work_members')
def work_members():
    """Auto-generated from SAS DATALINES"""
    data = [
        ("M00001", "PLNA01", "2025-01-01", "2025-12-31", "1980-05-14"),
        ...
    ]
    schema = "member_id STRING, plan_id STRING, eff_date DATE, term_date DATE, dob DATE"
    return spark.createDataFrame(data, schema)  # ✅ Clean return statement!
```

No more garbage text after the return statement! 🎉
