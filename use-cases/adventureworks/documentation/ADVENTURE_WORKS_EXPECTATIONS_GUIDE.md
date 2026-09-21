# Adventure Works Data Quality Expectations Guide

**Testing Data Quality with Real SQL Server Data**

---

## Overview

Created two versions of the Adventure Works SAS file:
1. **`sales_summary.sas`** — Original (NO expectations) ✅ Already exists
2. **`sales_summary_with_expectations.sas`** — Enhanced with 20+ data quality checks ✅ NEW

---

## What the Converter Does With Expectations

According to your technical documentation (CONVERTED_CODE_FEATURES.md), the converter:

1. ✅ **Generates expectations** from SAS comments marked `/* EXPECT ... */`
2. ✅ **Comments them out** as `#@dp.expect(...)` for manual review
3. ✅ **Safety first** — You enable them after verifying they're correct

**Converted output will look like:**
```python
# @dp.expect("valid_customer_id", "CustomerID > 0")
# @dp.expect("positive_revenue", "TotalRevenue > 0")
# @dp.expect("valid_value_tier", "value_tier IN ('High', 'Medium', 'Low')")
```

---

## Data Quality Checks Added (20+ Expectations)

### **Bronze Layer Validations**

#### Customers:
- ✅ `CustomerID > 0` — Valid customer IDs
- ✅ `CompanyName IS NOT NULL` — Required field populated
- ✅ `EmailAddress IS NOT NULL` — Contact info present

#### Orders:
- ✅ `SalesOrderID > 0` — Unique order IDs
- ✅ `OrderDate <= TODAY()` — No future orders
- ✅ `order_year >= 2010 AND order_year <= YEAR(TODAY())` — Reasonable date range
- ✅ `TotalDue > 0` — Positive amounts
- ✅ `ABS((SubTotal + TaxAmt + Freight) - TotalDue) < 0.01` — Math reconciliation

### **Silver Layer Validations**

#### Customer Metrics:
- ✅ `OrderCount > 0` — All customers have orders (HAVING filter)
- ✅ `TotalRevenue > 0` — Positive lifetime value
- ✅ `AvgOrderValue >= 10` — Minimum order size ($10)
- ✅ `FirstOrderDate <= LastOrderDate` — Logical date sequence
- ✅ `COUNT(DISTINCT CustomerID) = COUNT(*)` — No duplicate customers

#### Customer Classification:
- ✅ `value_tier IN ('High', 'Medium', 'Low')` — Valid categories
- ✅ `churn_risk IN ('High', 'Medium', 'Low')` — Valid risk levels
- ✅ `days_since_last_order >= 0` — Non-negative calculations
- ✅ `customer_lifetime_days >= 0` — Valid lifetimes
- ✅ `(value_tier = 'High' AND TotalRevenue >= 10000) OR value_tier != 'High'` — Business rule consistency

### **Gold Layer Validations**

#### Customer Summary:
- ✅ `COUNT(*) > 0` — Table not empty
- ✅ `CompanyName IS NOT NULL` — Key business field
- ✅ `value_tier IS NOT NULL` — Classification present
- ✅ `churn_risk IS NOT NULL` — Risk assessment present

#### Sales Statistics:
- ✅ `COUNT(*) <= 9` — Max combinations (3 tiers × 3 risks)
- ✅ `SUM(customer_count) = (SELECT COUNT(*) FROM customer_classified)` — Aggregation reconciliation
- ✅ `customer_count > 0` — No empty segments
- ✅ `tier_revenue > 0` — Positive revenue per segment

---

## How to Test Expectations

### **Step 1: Ingest Real Data into Bronze**

```bash
# Option A: Direct JDBC (quickest)
python ingest_real_adventureworks_data.py

# Option B: Lakeflow Connect (once bundle deploys)
databricks bundle run -t dev adventureworks_ingestion
```

### **Step 2: Convert SAS with Expectations**

```bash
# Upload enhanced SAS file
databricks fs cp specifications/sales_summary_with_expectations.sas \
  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/sales_summary_with_expectations.sas \
  --overwrite

# Run converter
databricks bundle run -t dev sas_dbx_code_translator

# Download converted Python
databricks fs cp \
  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/converted/transformed_sales_summary_with_expectations.py \
  transformations/transformed_sales_summary_with_expectations.py \
  --overwrite
```

### **Step 3: Review Commented Expectations**

Open `transformations/transformed_sales_summary_with_expectations.py` and look for:

```python
@dp.table(name="silver.customers")
def silver_customers():
    # @dp.expect("valid_customer_id", "CustomerID > 0")
    # @dp.expect("company_name_present", "CompanyName IS NOT NULL AND LENGTH(CompanyName) > 0")
    # @dp.expect("email_present", "EmailAddress IS NOT NULL")
    
    return spark.sql("""
        SELECT ...
    """)
```

### **Step 4: Enable Expectations (One at a Time)**

Uncomment expectations you want to enforce:

```python
@dp.table(name="silver.customers")
@dp.expect("valid_customer_id", "CustomerID > 0")  # ✓ Enabled
@dp.expect("company_name_present", "CompanyName IS NOT NULL")  # ✓ Enabled
# @dp.expect("email_present", "EmailAddress IS NOT NULL")  # Still reviewing
def silver_customers():
    return spark.sql("""
        SELECT ...
    """)
```

### **Step 5: Run Pipeline and Check Expectations**

```bash
# Deploy pipeline
databricks bundle deploy -t dev

# Run pipeline
# In Databricks UI: Workflows → Delta Live Tables → Your pipeline → Start

# View expectations results
# Pipeline UI shows:
#   ✓ valid_customer_id: 19,820 rows passed, 0 failed
#   ✓ company_name_present: 19,820 rows passed, 0 failed
```

---

## Testing Scenarios

### **Scenario 1: All Expectations Pass** ✅ Expected
Real Adventure Works data is clean, so most expectations should pass.

### **Scenario 2: Some Expectations Fail** ⚠️ Learning Opportunity
- Expectation: `EmailAddress IS NOT NULL`
- **Reality:** Adventure Works may have customers without emails
- **Fix:** Adjust expectation to `EmailAddress IS NOT NULL OR CustomerType = 'Store'`

### **Scenario 3: Business Rule Violation** 🚨 Data Quality Issue
- Expectation: `(value_tier = 'High') AND (TotalRevenue >= 10000)`
- **Failure:** Found customer classified as "High" with $8,500 revenue
- **Root Cause:** Logic error in classification code
- **Fix:** Correct the IF/THEN/ELSE thresholds

---

## Differences Between Files

| Feature | sales_summary.sas | sales_summary_with_expectations.sas |
|---------|-------------------|-------------------------------------|
| Expectations | ❌ None | ✅ 20+ checks |
| Bronze validation | ❌ No | ✅ Yes (IDs, dates, amounts) |
| Silver validation | ❌ No | ✅ Yes (metrics, classifications) |
| Gold validation | ❌ No | ✅ Yes (aggregations, completeness) |
| Business rules | ❌ Not enforced | ✅ Validated (tier logic, date sequences) |
| Testing readiness | ⚠️ Basic | ✅ Production-ready |

---

## Real Adventure Works Data Characteristics

Based on SQL Server schema (19,820 customers, 31,465 orders):

### **What Will Pass:**
- ✅ All CustomerIDs are positive integers
- ✅ All orders have positive TotalDue amounts
- ✅ OrderDates are in reasonable range (2010-2014)
- ✅ Math reconciliation: SubTotal + Tax + Freight = TotalDue

### **What Might Fail:**
- ⚠️ Some customers may lack EmailAddress (stores vs. individuals)
- ⚠️ Some orders may have NULL ship dates (not yet shipped)
- ⚠️ Edge cases: Orders with $0 freight (pickup)

### **Testing Value:**
Real data exposes edge cases that synthetic data misses!

---

## Converter Output Preview

**Without expectations:**
```python
@dp.table(name="gold.customer_summary")
def gold_customer_summary():
    return spark.sql("""
        SELECT CustomerID, CompanyName, TotalRevenue, value_tier
        FROM silver.customer_classified
        ORDER BY TotalRevenue DESC
    """)
```

**With expectations (commented out):**
```python
@dp.table(name="gold.customer_summary")
def gold_customer_summary():
    # @dp.expect("not_empty", "COUNT(*) > 0")
    # @dp.expect("company_name_required", "CompanyName IS NOT NULL")
    # @dp.expect("valid_value_tier", "value_tier IS NOT NULL")
    # @dp.expect("valid_tier_values", "value_tier IN ('High', 'Medium', 'Low')")
    
    return spark.sql("""
        SELECT CustomerID, CompanyName, TotalRevenue, value_tier
        FROM silver.customer_classified
        ORDER BY TotalRevenue DESC
    """)
```

---

## Next Steps

1. **Start without expectations** — Run `sales_summary.sas` (original) to verify pipeline works
2. **Add expectations gradually** — Run `sales_summary_with_expectations.sas` and review output
3. **Enable one at a time** — Uncomment expectations after verifying they make sense
4. **Monitor in production** — Use Databricks Pipeline UI to track expectation metrics

---

## Documentation References

- **Converter Features:** `CONVERTED_CODE_FEATURES.md` (Section 10: Data Quality Expectations)
- **Architecture:** `docs/architecture/SAS_MIGRATION_ARCHITECTURE.md`
- **SQL Server Setup:** `docs/external-sources/SETUP_ADVENTUREWORKS_INGESTION.md`
- **Testing Strategy:** `CONVERTED_CODE_FEATURES.md` (Testing Strategy section)

---

**Bottom Line:** You now have TWO versions to test with — start simple, then add data quality! 🎯
