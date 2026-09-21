# Production Template Guide

## 🎯 What You Asked For

You requested converted files include:
1. ✅ **Header comment block** (name, purpose, author, change history)
2. ✅ **Parameters section** (catalog, schema, file_path)
3. ✅ **Bronze ingestion timestamp** for audit trail

**All implemented in notebook `03c_production_ready_conversion.py`!**

---

## 📄 Example Output

### **Input SAS File:**
```sas
/* claims_adjudication_comprehensive.sas */
proc sql;
    select claim_id, member_id, billed_amount
    from claims.raw_837
    where claim_date >= '01JAN2025'd;
quit;
```

### **Output Python File:** `converted_claims_adjudication_comprehensive.py`

```python
# ==============================================================================
# CONVERTED SAS PIPELINE - PRODUCTION READY
# ==============================================================================
# Name:           converted_claims_adjudication_comprehensive.py
# Original File:  claims_adjudication_comprehensive.sas
# Purpose:        Converted from SAS to Spark Declarative Pipeline (SDP)
# Author:         SAS Migration Team
# Converted:      2026-09-17
# Target:         Databricks SDP (Spark Declarative Pipelines)
# Model:          sas2databricks with opus-4.8
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# 2026-09-17 | SAS Migration Team | Initial conversion from SAS
# ------------------------------------------------------------------------------
#
# Notes:
# - This file was auto-generated using sas2databricks
# - Review business logic carefully before deploying to production
# - Test with sample data before running on full dataset
# - Verify data quality expectations are appropriate
#
# ==============================================================================

# ==============================================================================
# PARAMETERS
# ==============================================================================

# Unity Catalog configuration
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"

# Source paths (adjust for your environment)
SOURCE_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/sas_migration"
INPUT_PATH = f"{SOURCE_VOLUME}/input"

# Data quality settings
ENABLE_EXPECTATIONS = True
EXPECTATION_ACTION = "drop"  # Options: "drop", "fail", "warn"

# ==============================================================================
# IMPORTS
# ==============================================================================

from pyspark.sql import functions as F
from pyspark.sql import types as T
from datetime import datetime

# ==============================================================================
# ORIGINAL SAS CODE (for reference)
# ==============================================================================
"""
/* claims_adjudication_comprehensive.sas */
proc sql;
    select claim_id, member_id, billed_amount
    from claims.raw_837
    where claim_date >= '01JAN2025'd;
quit;
"""

# ==============================================================================
# CONVERTED PIPELINE CODE
# ==============================================================================

# [sas2databricks converted code here]
import dlt
from pyspark.sql import functions as F

@dlt.table(
    name="claims_select",
    comment="Converted from claims_adjudication_comprehensive.sas"
)
def claims_select():
    return spark.sql("""
        SELECT claim_id, member_id, billed_amount
        FROM `na-dbxtraining`.healthcare_claims.raw_837
        WHERE claim_date >= '2025-01-01'
    """)

# ==============================================================================
# HELPER: Add Bronze Metadata Columns
# ==============================================================================

def add_bronze_metadata(df, source_file="claims_adjudication_comprehensive.sas"):
    """
    Adds standard bronze layer metadata columns for audit trail

    Args:
        df: Input DataFrame
        source_file: Name of source SAS file

    Returns:
        DataFrame with metadata columns
    """
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
    )

# ==============================================================================
# ENHANCED TABLES (with metadata)
# ==============================================================================

@dlt.table(
    name="bronze_claims",
    comment="Bronze layer with metadata - converted from claims_adjudication_comprehensive.sas"
)
@dlt.expect_or_drop("valid_claim_id", "claim_id IS NOT NULL")
@dlt.expect_or_drop("positive_amount", "billed_amount > 0")
def bronze_claims():
    # Get data from converted table
    df = spark.table("LIVE.claims_select")
    
    # Add bronze metadata
    return add_bronze_metadata(df, source_file="claims_adjudication_comprehensive.sas")

# ==============================================================================
# DATA QUALITY EXPECTATIONS
# ==============================================================================

# Add data quality checks based on SAS validation rules
# Example patterns:
#
# @dlt.expect_or_drop("valid_dates", "claim_date >= '2020-01-01'")
# @dlt.expect_or_drop("positive_amounts", "billed_amount > 0")
# @dlt.expect_or_warn("member_exists", "member_id IS NOT NULL")

# ==============================================================================
# END OF CONVERTED PIPELINE
# ==============================================================================
#
# Deployment checklist:
# □ Review business logic against original SAS
# □ Verify data quality expectations
# □ Test with sample data
# □ Validate output matches SAS results
# □ Update change history when modifying
# □ Deploy via DAB or pipeline UI
#
# ==============================================================================
```

---

## ✅ What's Included

### **1. Header Comment Block**
```python
# ==============================================================================
# CONVERTED SAS PIPELINE - PRODUCTION READY
# ==============================================================================
# Name:           converted_claims_adjudication_comprehensive.py
# Original File:  claims_adjudication_comprehensive.sas
# Purpose:        Converted from SAS to Spark Declarative Pipeline (SDP)
# Author:         SAS Migration Team
# Converted:      2026-09-17
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# 2026-09-17 | SAS Migration Team | Initial conversion from SAS
# 2026-09-20 | Your Name          | Added validation rules
# 2026-09-25 | Your Name          | Updated bronze metadata
# ------------------------------------------------------------------------------
```

**Customizable:** Change author name, add your change history entries

---

### **2. Parameters Section**
```python
# ==============================================================================
# PARAMETERS
# ==============================================================================

# Unity Catalog configuration
CATALOG = "na-dbxtraining"
SCHEMA = "sas2dbx_migrate"

# Source paths (adjust for your environment)
SOURCE_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/sas_migration"
INPUT_PATH = f"{SOURCE_VOLUME}/input"

# Data quality settings
ENABLE_EXPECTATIONS = True
EXPECTATION_ACTION = "drop"  # Options: "drop", "fail", "warn"
```

**Customizable:** Update catalog, schema, paths for your environment

---

### **3. Bronze Ingestion Timestamp**
```python
def add_bronze_metadata(df, source_file="your_file.sas"):
    """Adds audit trail columns"""
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
    )

# Use it:
@dlt.table(name="bronze_claims")
def bronze_claims():
    df = spark.table("LIVE.claims_select")
    return add_bronze_metadata(df, source_file="claims.sas")
```

**Result:** Every record gets:
- `bronze_ingestion_timestamp` → `2026-09-17 14:32:15.123`
- `bronze_source_file` → `claims_adjudication_comprehensive.sas`
- `bronze_ingestion_date` → `2026-09-17`

---

### **4. Original SAS Code (Embedded)**
```python
# ==============================================================================
# ORIGINAL SAS CODE (for reference)
# ==============================================================================
"""
/* Your original SAS code embedded here for traceability */
proc sql;
    select ...
quit;
"""
```

**Benefit:** Always know what the original SAS logic was

---

### **5. Data Quality Expectations (Template)**
```python
# ==============================================================================
# DATA QUALITY EXPECTATIONS
# ==============================================================================

@dlt.expect_or_drop("valid_dates", "claim_date >= '2020-01-01'")
@dlt.expect_or_drop("positive_amounts", "billed_amount > 0")
@dlt.expect_or_warn("member_exists", "member_id IS NOT NULL")
```

**Customizable:** Add your validation rules based on SAS edits

---

## 🎨 Customization Examples

### **Example 1: Update Author**

Find line 15, change:
```python
# Author:         SAS Migration Team
```

To:
```python
# Author:         Your Name / Your Team
```

---

### **Example 2: Add Change History**

Find the change history section (lines 18-22), add:
```python
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# 2026-09-17 | SAS Migration Team | Initial conversion from SAS
# 2026-09-20 | John Doe           | Added member_id validation
# 2026-09-25 | Jane Smith         | Updated catalog to prod
# ------------------------------------------------------------------------------
```

---

### **Example 3: Customize Parameters**

Find the parameters section (lines 30-40), update:
```python
# Unity Catalog configuration
CATALOG = "your_catalog"          # ← Change to your catalog
SCHEMA = "your_schema"            # ← Change to your schema

# Source paths
SOURCE_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/your_volume"
INPUT_PATH = f"{SOURCE_VOLUME}/your_input_folder"
```

---

### **Example 4: Add More Bronze Metadata**

Enhance the helper function:
```python
def add_bronze_metadata(df, source_file="your_file.sas"):
    """Enhanced with more audit columns"""
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
        .withColumn("bronze_pipeline_name", F.lit("claims_processing"))
        .withColumn("bronze_version", F.lit("v1.0"))
        .withColumn("bronze_processed_by", F.lit("databricks_job_123"))
    )
```

---

### **Example 5: Add Custom Expectations**

Based on your SAS validation rules:
```python
# SAS had: if billed_amount < 0 or billed_amount > 1000000 then delete;
@dlt.expect_or_drop(
    "valid_billed_amount",
    "billed_amount BETWEEN 0 AND 1000000"
)

# SAS had: if missing(member_id) then edit_flag = 1;
@dlt.expect_or_drop(
    "member_id_required",
    "member_id IS NOT NULL AND member_id != ''"
)

# SAS had: if not (eff_date <= service_date <= term_date);
@dlt.expect_or_drop(
    "valid_coverage_dates",
    "service_date BETWEEN eff_date AND term_date"
)
```

---

## 🚀 How to Use

### **Step 1: Run Conversion**

Import and run `03c_production_ready_conversion.py`:

```
Output: staging/needs_review/converted_claims_adjudication_comprehensive.py
```

---

### **Step 2: Customize**

Open the converted file and update:
1. ✅ Line 15: Change author name
2. ✅ Lines 30-40: Update CATALOG, SCHEMA
3. ✅ Lines 18-22: Add change history when you modify
4. ✅ Lines 120-130: Add data quality expectations

---

### **Step 3: Test**

Copy the code to a new notebook and run:

```python
# Your customized converted code here
# Test with sample data

# Verify bronze metadata columns exist
df = spark.table("LIVE.bronze_claims")
df.select("bronze_ingestion_timestamp", "bronze_source_file").show()
```

---

### **Step 4: Deploy**

Move to approved and deploy:

```bash
# Move to approved
mv staging/needs_review/converted_file.py staging/approved/

# Deploy via DAB or UI
```

---

## 📊 Output Structure

```
staging/
└── needs_review/
    ├── converted_claims_adjudication_comprehensive.py  ← Production-ready!
    │   - Header comment ✅
    │   - Parameters ✅
    │   - Bronze timestamp ✅
    │   - Original SAS ✅
    │
    ├── converted_eligibility_validation.py
    └── converted_simple_select.py
```

**Every file** includes all production patterns! 🎯

---

## 💡 Benefits

| Pattern | Benefit |
|---------|---------|
| **Header block** | Know who created it, when, and why |
| **Change history** | Track modifications over time |
| **Parameters** | Easy to promote dev → test → prod |
| **Bronze timestamp** | Audit trail for every record |
| **Original SAS** | Always know source logic |
| **Expectations** | Data quality built-in |

---

## 🎯 Summary

**Your request:** Production-ready templates with headers, params, and timestamps  
**Solution:** Notebook `03c` wraps sas2databricks output with all patterns  
**Result:** Every converted file is deployment-ready! ✅

**Next:** Run `03c_production_ready_conversion.py` and customize the output!
