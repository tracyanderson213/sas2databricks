# SAS Coverage & Known Gaps

**What the converter handles well vs. potential gaps to test**

**Powered by:** [sas2databricks](https://github.com/navintkr/sas2databricks) — an open-source, LLM-assisted migration toolkit that converts SAS analytics, data transformations, and reports into Databricks (PySpark, Spark SQL, Delta Live Tables, and Workflows) end-to-end.

---

## ✅ Covered & Tested

### Data Steps
- **DATALINES** — Embedded data converted to Spark DataFrames
- **MERGE** (with BY statement) — Converted to appropriate JOINs (inner, left, right, full)
- **SET** — Reading tables converted to `dlt.read()`
- **IF/THEN/ELSE** — Converted to `F.when()` / CASE statements
- **RETAIN** — Converted to Window functions with cumulative operations
- **WHERE** — Converted to `.filter()`
- **DROP/KEEP** — Converted to `.select()` with explicit columns
- **RENAME** — Converted to `.withColumnRenamed()`

### PROC Statements
- **PROC SQL** — Handled with Spark SQL equivalent
- **PROC FORMAT** — Extracted to UDF dictionaries or mapping tables
- **PROC PRINT** — Removed (output only, not a table)
- **PROC REPORT** — Removed (output only, not a table)

### Functions & Operations
- **SUM/MEAN/MIN/MAX** — Converted to `F.sum()`, `F.mean()`, etc.
- **SUBSTR/SCAN** — Character functions mapped to Spark equivalents
- **missing()** — Converted to `.isNull()`
- **Comparison operators** — Properly mapped (EQ/NE/GT/LT → ==, !=, >, <)

### Complex Patterns
- **FIRST./LAST. variables** — Handled via window functions
- **Running totals** (RETAIN) — Window functions with cumulative sum
- **Nested IF/THEN/ELSE** — Collapsed to single CASE statement
- **IN= dataset options** — Join type determination

---

## ⚠️ Potential Gaps (Needs Testing)

### 1. **PROC TRANSPOSE**
- **SAS:** Pivot wide-to-long or long-to-wide
- **Spark equivalent:** `pivot()` / `unpivot()`
- **Risk:** High — common in reporting, complex logic
- **Test with:**
```sas
PROC TRANSPOSE DATA=sales OUT=sales_pivoted;
  BY customer_id;
  ID product_name;
  VAR amount;
RUN;
```

### 2. **PROC FREQ / PROC MEANS / PROC SUMMARY**
- **SAS:** Statistical summaries and cross-tabulations
- **Spark equivalent:** `.groupBy().agg()` with statistics
- **Risk:** Medium — often replaced by direct aggregations in Gold layer
- **Test with:**
```sas
PROC FREQ DATA=claims;
  TABLES status*severity / NOCOL NOPCT;
RUN;

PROC MEANS DATA=claims MEAN STD MIN MAX;
  CLASS customer_type;
  VAR claim_amount;
RUN;
```

### 3. **Macro Variables (%LET, &var)**
- **SAS:** Dynamic variable substitution
- **Spark equivalent:** Python variables or widgets
- **Risk:** Medium — often used for parameterization
- **Test with:**
```sas
%LET start_date = '2024-01-01';
%LET end_date = '2024-12-31';

DATA filtered;
  SET claims;
  WHERE claim_date BETWEEN &start_date AND &end_date;
RUN;
```

### 4. **ARRAY Processing**
- **SAS:** Looping over multiple columns
- **Spark equivalent:** Multiple `withColumn()` or `select()` with list comprehension
- **Risk:** High — common pattern, no direct equivalent
- **Test with:**
```sas
DATA normalized;
  SET sales;
  ARRAY amounts{12} jan feb mar apr may jun jul aug sep oct nov dec;
  ARRAY norm{12} jan_norm--dec_norm;
  
  DO i = 1 TO 12;
    norm{i} = amounts{i} / total_sales;
  END;
RUN;
```

### 5. **DO Loops (Iterative Processing)**
- **SAS:** `DO i = 1 TO n;`
- **Spark equivalent:** `explode()` or Python loops (anti-pattern!)
- **Risk:** High — iterative logic doesn't map cleanly to distributed processing
- **Test with:**
```sas
DATA amortization;
  principal = 100000;
  rate = 0.05;
  DO year = 1 TO 30;
    interest = principal * rate;
    principal = principal + interest;
    OUTPUT;
  END;
RUN;
```

### 6. **LAG / LEAD Functions**
- **SAS:** Access previous/next row values
- **Spark equivalent:** Window functions with `lag()` / `lead()`
- **Risk:** Medium — window functions handle this, but needs proper partitioning
- **Test with:**
```sas
DATA changes;
  SET sales;
  BY customer_id date;
  prev_amount = LAG(amount);
  change = amount - prev_amount;
RUN;
```

### 7. **PROC SORT**
- **SAS:** Explicit sorting, often required before MERGE
- **Spark equivalent:** `.orderBy()` (but Spark handles join ordering automatically)
- **Risk:** Low — usually not needed, but may appear in code
- **Test with:**
```sas
PROC SORT DATA=claims OUT=claims_sorted;
  BY customer_id claim_date;
RUN;
```

### 8. **PROC APPEND**
- **SAS:** Append one dataset to another
- **Spark equivalent:** `.union()` or `MERGE INTO`
- **Risk:** Low — straightforward mapping
- **Test with:**
```sas
PROC APPEND BASE=all_claims DATA=new_claims FORCE;
RUN;
```

### 9. **SET Options (OBS=, FIRSTOBS=, WHERE=)**
- **SAS:** Row filtering at read time
- **Spark equivalent:** `.limit()`, `.offset()`, `.filter()`
- **Risk:** Low — usually handled, but syntax variations exist
- **Test with:**
```sas
DATA sample;
  SET claims(FIRSTOBS=100 OBS=200 WHERE=(amount > 1000));
RUN;
```

### 10. **Date Functions (INTCK, INTNX, DATEPART)**
- **SAS:** Date arithmetic and manipulation
- **Spark equivalent:** `months_between()`, `add_months()`, `date_trunc()`, etc.
- **Risk:** Medium — date logic can be complex
- **Test with:**
```sas
DATA aged;
  SET claims;
  days_old = INTCK('DAY', claim_date, TODAY());
  next_month = INTNX('MONTH', claim_date, 1, 'E');
RUN;
```

### 11. **INPUT / PUT Statements**
- **SAS:** Data type conversions and formatting
- **Spark equivalent:** `.cast()`, `to_date()`, `date_format()`
- **Risk:** Medium — format strings may not map directly
- **Test with:**
```sas
DATA formatted;
  SET raw;
  claim_date = INPUT(date_char, YYMMDD10.);
  amount_text = PUT(amount, DOLLAR12.2);
RUN;
```

### 12. **Macro Programs (%MACRO/%MEND)**
- **SAS:** Reusable code generation
- **Spark equivalent:** Python functions or Jinja templates
- **Risk:** High — macro logic may not convert automatically
- **Test with:**
```sas
%MACRO filter_by_date(dataset, start, end);
  DATA filtered;
    SET &dataset;
    WHERE date BETWEEN "&start"d AND "&end"d;
  RUN;
%MEND;

%filter_by_date(claims, 2024-01-01, 2024-12-31);
```

### 13. **PROC TABULATE (Complex Reporting)**
- **SAS:** Multi-dimensional cross-tabulations
- **Spark equivalent:** Multiple `groupBy()` with `pivot()`
- **Risk:** High — complex output formatting
- **Test with:**
```sas
PROC TABULATE DATA=sales;
  CLASS region product;
  VAR amount;
  TABLE region, product*amount*(SUM MEAN);
RUN;
```

### 14. **BY-Group Processing**
- **SAS:** `FIRST.var` and `LAST.var` automatic variables
- **Spark equivalent:** Window functions with `row_number()`, `rank()`
- **Risk:** Medium — we handle some cases, but complex BY-group logic may have gaps
- **Test with:**
```sas
DATA summary;
  SET claims;
  BY customer_id;
  IF FIRST.customer_id THEN total = 0;
  total + amount;
  IF LAST.customer_id THEN OUTPUT;
RUN;
```

### 15. **Multi-Way Merges**
- **SAS:** `MERGE table1 table2 table3;`
- **Spark equivalent:** Chained `.join()` operations
- **Risk:** Medium — we handle 2-table merges, but 3+ may need testing
- **Test with:**
```sas
DATA combined;
  MERGE claims members providers;
  BY customer_id;
RUN;
```

---

## 🎯 Recommended Testing Strategy

### Priority 1 (High Risk, Common Usage)
1. **ARRAY processing** — Test column-wise operations
2. **DO loops** — Test iterative logic (may need redesign)
3. **PROC TRANSPOSE** — Test pivot operations
4. **Macro programs** — Test parameterized code generation
5. **Complex BY-group processing** — Test FIRST./LAST. with multiple conditions

### Priority 2 (Medium Risk, Moderate Usage)
6. **LAG/LEAD functions** — Test time-series comparisons
7. **Date functions (INTCK/INTNX)** — Test date arithmetic
8. **PROC FREQ/MEANS** — Test statistical summaries
9. **INPUT/PUT conversions** — Test format string mappings
10. **Multi-way merges** — Test 3+ table joins

### Priority 3 (Low Risk, Workarounds Available)
11. **PROC SORT** — Usually unnecessary in Spark
12. **PROC APPEND** — Straightforward `.union()`
13. **SET options** — Basic filtering
14. **Macro variables** — Easily replaced with Python variables

---

## 🔍 How to Test for Gaps

### 1. Create Minimal Test Cases
For each potential gap, create a simple SAS file that uses only that feature:

```sas
/* test_transpose.sas */
DATA sales;
  INPUT customer_id product $ amount;
  DATALINES;
1 A 100
1 B 200
2 A 150
;
RUN;

PROC TRANSPOSE DATA=sales OUT=sales_wide;
  BY customer_id;
  ID product;
  VAR amount;
RUN;

PROC PRINT DATA=sales_wide;
RUN;
```

### 2. Run Through Converter
```bash
# Place in specifications/
cp test_transpose.sas specifications/

# Run converter
databricks bundle run -t dev sas_dbx_code_translator

# Check output
python list_converted_files.py
```

### 3. Review Converted Code
- Does it compile?
- Does it produce correct output?
- Are there placeholders or TODOs?
- Is the logic equivalent to SAS?

### 4. Document Findings
Add to this file:
- ✅ Feature works correctly (move to "Covered & Tested")
- ⚠️ Feature partially works (document limitations)
- ❌ Feature not supported (document workaround)

---

## 📝 Known Workarounds

### ARRAY Processing → List Comprehension
```python
# SAS ARRAY pattern
# ARRAY amounts{12} jan--dec;
# DO i = 1 TO 12; amounts{i} = amounts{i} * 1.1; END;

# Spark equivalent
month_cols = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
for col in month_cols:
    df = df.withColumn(col, F.col(col) * 1.1)
```

### DO Loop → explode() or Redesign
```python
# SAS DO loop (generates multiple rows)
# DO year = 1 TO 30; ... OUTPUT; END;

# Spark: Create array, then explode
df = df.withColumn("year", F.expr("sequence(1, 30)"))
df = df.withColumn("year", F.explode("year"))
```

### Macro Variables → Widgets
```python
# SAS: %LET start_date = '2024-01-01';
# Spark: Widget or Python variable
start_date = spark.conf.get("start_date", "2024-01-01")
df = df.filter(F.col("claim_date") >= start_date)
```

---

## 🚀 Next Steps

1. **Review existing test cases** — What SAS features are in `claims_adjudication.sas`?
2. **Create gap test suite** — One minimal SAS file per potential gap
3. **Run through converter** — Document what works vs. needs enhancement
4. **Prioritize fixes** — Based on business need and frequency of use
5. **Update documentation** — Move confirmed features to "Covered & Tested"

---

**Bottom line:** The converter handles core SAS data processing (MERGE, RETAIN, IF/THEN/ELSE, PROC FORMAT), but advanced features like ARRAY processing, DO loops, and PROC TRANSPOSE need validation. Test with your actual SAS codebase to identify real gaps vs. theoretical ones.
