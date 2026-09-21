# File Naming & Traceability Strategy

## The Problem You Identified

**Reality:** In production, you'll upload dozens of SAS programs:
```
input/
├── claims_adjudication.sas
├── eligibility_validation.sas
├── risk_adjustment_scoring.sas
├── provider_credentialing.sas
├── pharmacy_rebate_calc.sas
└── ... 50 more files
```

**Your concerns:**
1. ❌ **Config files all named `config.yaml`** — confusing when you have many projects
2. ❌ **Output filenames might not match input** — hard to trace back
3. ❌ **No original SAS code in converted output** — lose context and audit trail

**You're absolutely right!** Let me show the improved approach:

---

## ✅ Improved File Organization

### **Option 1: Flat Structure (Simple Projects)**

**Best for:** Small migrations with <20 SAS files, single domain

```
input/
├── claims_adjudication.sas              # Input SAS
├── claims_adjudication.config.yaml      # ✅ Filename-specific config
├── eligibility_validation.sas
├── eligibility_validation.config.yaml   # ✅ Another config
├── risk_adjustment_scoring.sas
├── risk_adjustment_scoring.config.yaml
└── metadata/
    └── global_libname_mapping.yaml      # Shared across all

staging/
├── claims_adjudication.py               # ✅ SAME NAME (except extension)
├── claims_adjudication.html             # Conversion report
├── eligibility_validation.py            # ✅ SAME NAME
├── eligibility_validation.html
├── risk_adjustment_scoring.py           # ✅ SAME NAME
└── risk_adjustment_scoring.html
```

**Advantages:**
- ✅ Easy 1:1 mapping (input → output)
- ✅ No nested folders to navigate
- ✅ Config travels with SAS file
- ✅ grep/find works easily

**Disadvantages:**
- ❌ Gets cluttered with 50+ files
- ❌ No execution order across files

---

### **Option 2: Project-Based Structure (Complex Projects)**

**Best for:** Large migrations, multi-step pipelines, dependencies

```
input/
├── claims_processing/
│   ├── PROJECT.yaml                      # ✅ Project manifest (was config.yaml)
│   ├── 01_load_raw_claims.sas
│   ├── 02_enrich_member_data.sas
│   ├── 03_apply_edits.sas
│   ├── 04_calculate_risk_adjustment.sas
│   ├── 05_generate_payment_file.sas
│   └── metadata/
│       ├── libname_mapping.yaml
│       └── table_schemas.csv
│
├── eligibility_management/
│   ├── PROJECT.yaml
│   ├── daily_eligibility_snapshot.sas
│   ├── cobra_continuation_logic.sas
│   └── metadata/
│
└── provider_network/
    ├── PROJECT.yaml
    ├── credentialing_validation.sas
    └── fee_schedule_update.sas

staging/
├── claims_processing/
│   ├── 01_load_raw_claims.py            # ✅ SAME NAMES
│   ├── 02_enrich_member_data.py
│   ├── 03_apply_edits.py
│   ├── 04_calculate_risk_adjustment.py
│   ├── 05_generate_payment_file.py
│   └── CONVERSION_REPORT.html           # Summary for all files
│
├── eligibility_management/
│   ├── daily_eligibility_snapshot.py
│   ├── cobra_continuation_logic.py
│   └── CONVERSION_REPORT.html
│
└── provider_network/
    ├── credentialing_validation.py
    ├── fee_schedule_update.py
    └── CONVERSION_REPORT.html
```

**Advantages:**
- ✅ Groups related SAS programs
- ✅ Clear execution order (01, 02, 03...)
- ✅ Metadata travels with project
- ✅ One report per project

**Disadvantages:**
- Slightly more complex structure

---

## ✅ Solution: Preserve Filename Through Conversion

### **Conversion API Should Maintain Filenames:**

```python
# Current approach (notebook 03)
from sas2databricks import migrate

# Read input
sas_file = "claims_adjudication.sas"
sas_path = f"{input_base}/{sas_file}"

with open(sas_path.replace("/Volumes", "/dbfs/Volumes"), 'r') as f:
    sas_text = f.read()

# Convert
result = migrate(
    sas_text,
    target="sdp",
    model="opus-4.8",
    source_path=sas_file  # ← Pass original filename
)

# Write output with SAME BASE NAME
output_basename = sas_file.replace('.sas', '.py')  # claims_adjudication.py
output_path = f"{staging_base}/{output_basename}"

with open(output_path.replace("/Volumes", "/dbfs/Volumes"), 'w') as f:
    f.write(result.code)

print(f"✅ Converted: {sas_file} → {output_basename}")
```

**Result:**
```
input/claims_adjudication.sas  →  staging/claims_adjudication.py
                                            ↑
                                   SAME BASE NAME!
```

---

## ✅ Solution: Embed Original SAS Code in Output

### **Modified Conversion to Include Original Code:**

The converted Python file should look like this:

```python
# ==============================================================================
# CONVERTED FROM SAS TO DATABRICKS
# ==============================================================================
# Original file: claims_adjudication.sas
# Converted on:  2024-01-15 14:32:00
# Target:        Spark Declarative Pipelines (SDP)
# Model:         opus-4.8
# Confidence:    MEDIUM-HIGH (complex business logic - review required)
# ==============================================================================
#
# ORIGINAL SAS CODE (for reference):
# ------------------------------------------------------------------------------
# /*******************************************************************************
# * Program: claims_adjudication.sas
# * Purpose: Process healthcare claims with business edits and risk adjustment
# * ...
# * [FULL ORIGINAL SAS CODE EMBEDDED AS COMMENT]
# ******************************************************************************/
# ==============================================================================

from pyspark import pipelines as dp
from pyspark.sql import functions as F

# ==============================================================================
# STEP 1: Load and validate raw claims data
# ==============================================================================
# Original SAS (lines 25-60):
#   data work.raw_claims;
#       set claims.raw_837;
#       /* Validate required fields */
#       ...
#   run;
# ------------------------------------------------------------------------------

@dp.table(name="bronze_raw_claims")
@dp.comment("Load raw EDI 837 claims. Source: claims_adjudication.sas lines 25-60")
def bronze_raw_claims():
    """
    Original SAS: data work.raw_claims; set claims.raw_837;
    
    Loads raw EDI 837 claims from source system.
    Validates required fields: member_id, provider_npi, claim_date, 
    diag_code1, procedure_code.
    
    Conversion method: Deterministic (DATA step → SDP table)
    """
    return spark.read.table("`na-dbxtraining`.healthcare_claims.raw_837")


@dp.table(name="silver_validated_claims")
@dp.comment("Claims validation with business edits. Source: claims_adjudication.sas lines 25-60")
@dp.expect_or_drop("member_id_required", "member_id IS NOT NULL")
@dp.expect_or_drop("provider_npi_required", "provider_npi IS NOT NULL")
@dp.expect_or_drop("valid_claim_date", "claim_date >= '2020-01-01' AND claim_date <= current_date()")
@dp.expect_or_drop("valid_billed_amount", "billed_amount > 0 AND billed_amount <= 1000000")
def silver_validated_claims():
    """
    Original SAS (lines 30-58):
        /* Validate required fields */
        array required{*} member_id provider_npi claim_date diag_code1 procedure_code;
        edit_flag = 0;
        edit_reason = '';
        
        do i = 1 to dim(required);
            if missing(required{i}) then do;
                edit_flag = 1;
                edit_reason = catx('; ', edit_reason, ...);
            end;
        end;
    
    Conversion method: LLM-assisted (business logic → data quality expectations)
    Confidence: HIGH (validated with sample data)
    
    ⚠️  REVIEW REQUIRED: Verify edit rules match SAS behavior exactly
    """
    df = spark.read.table("bronze_raw_claims")
    
    # Flag invalid records (SAS edit_flag = 1)
    df = df.withColumn(
        "edit_reason",
        F.when(F.col("member_id").isNull(), "member_id is missing")
         .when(F.col("provider_npi").isNull(), "provider_npi is missing")
         .when(F.col("claim_date").isNull(), "claim_date is missing")
         .when((F.col("claim_date") < F.lit("2020-01-01")) | 
               (F.col("claim_date") > F.current_date()), "Invalid claim_date")
         .when((F.col("billed_amount") <= 0) | 
               (F.col("billed_amount") > 1000000), "Invalid billed_amount")
         .otherwise(F.lit(""))
    )
    
    df = df.withColumn(
        "edit_flag",
        F.when(F.col("edit_reason") != "", F.lit(1)).otherwise(F.lit(0))
    )
    
    return df

# ... rest of the pipeline ...

# ==============================================================================
# END OF CONVERTED CODE
# ==============================================================================
# For questions about the conversion, refer to:
#   - CONVERSION_REPORT.html (detailed line-by-line analysis)
#   - Original SAS: claims_adjudication.sas
#   - sas2databricks documentation: https://github.com/navintkr/sas2databricks
# ==============================================================================
```

---

## 📋 Updated config.yaml to Control This

```yaml
project_name: claims_processing
description: Healthcare claims adjudication pipeline

# File naming control
output_format:
  preserve_filename: true          # ✅ Keep same base name
  extension: .py                   # claims_adjudication.py
  add_suffix: false                # If true: claims_adjudication_sdp.py

# Original code embedding
embed_original_sas:
  enabled: true                    # ✅ Include full SAS code as comments
  location: header                 # header | inline | separate_file
  format: block_comment            # block_comment | docstring | markdown

# Traceability metadata
include_metadata:
  original_filename: true          # ✅ Header comment with source
  conversion_timestamp: true       # When converted
  line_number_mapping: true        # SAS line → Python line mapping
  confidence_scores: true          # Per-section confidence levels
  business_rules: true             # Extract and document rules

# Conversion settings
conversion:
  target: sdp
  model: opus-4.8
  validate_output: true
```

---

## 🔧 Updated Notebook 03 (Simplified)

```python
# For each SAS file in input/
for sas_file in sas_files:
    # Read SAS
    with open(f"{input_base}/{sas_file}", 'r') as f:
        sas_code = f.read()
    
    # Convert (API preserves filename internally)
    result = migrate(
        sas_code,
        target="sdp",
        model="opus-4.8",
        source_path=sas_file,
        embed_original=True  # ← Include SAS in output
    )
    
    # Write output with SAME BASE NAME
    output_file = sas_file.replace('.sas', '.py')
    with open(f"{staging_base}/{output_file}", 'w') as f:
        f.write(result.code)
    
    print(f"✅ {sas_file:40} → {output_file}")
```

**Output:**
```
✅ claims_adjudication.sas              → claims_adjudication.py
✅ eligibility_validation.sas           → eligibility_validation.py
✅ risk_adjustment_scoring.sas          → risk_adjustment_scoring.py
✅ provider_credentialing.sas           → provider_credentialing.py
```

---

## 🎯 Summary: Your Points Are Spot-On!

| Your Concern | Solution |
|--------------|----------|
| **Multiple SAS files get confusing** | ✅ Each file keeps its own unique name through conversion |
| **config.yaml all look the same** | ✅ Option 1: Use `filename.config.yaml`<br>✅ Option 2: One `PROJECT.yaml` per folder |
| **Hard to trace output back to input** | ✅ Preserve filename: `claims_adjudication.sas` → `claims_adjudication.py` |
| **Lose original SAS code context** | ✅ Embed full original SAS as comment block in header |
| **Need audit trail** | ✅ Include: source filename, conversion date, confidence scores |

---

## 📁 Recommended Production Structure

For your real migration, I recommend:

```
/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/

input/
├── claims_processing/
│   ├── PROJECT.yaml                          # Project-level config
│   ├── claims_adjudication.sas              # Original SAS
│   ├── eligibility_validation.sas
│   ├── risk_adjustment_scoring.sas
│   └── metadata/
│       ├── libname_mapping.yaml             # SAS libs → UC catalogs
│       └── table_schemas.csv                # PROC CONTENTS output
│
staging/
├── claims_processing/
│   ├── claims_adjudication.py               # ✅ SAME NAME (w/ embedded SAS)
│   ├── claims_adjudication.html             # Conversion report
│   ├── eligibility_validation.py            # ✅ SAME NAME
│   ├── eligibility_validation.html
│   ├── risk_adjustment_scoring.py           # ✅ SAME NAME
│   └── risk_adjustment_scoring.html
│
approved/
├── claims_processing/
│   ├── databricks.yml                        # DAB bundle
│   ├── src/
│   │   ├── claims_adjudication.py           # ✅ Approved version
│   │   ├── eligibility_validation.py
│   │   └── risk_adjustment_scoring.py
│   └── original_sas/                        # ✅ Archive original SAS
│       ├── claims_adjudication.sas
│       ├── eligibility_validation.sas
│       └── risk_adjustment_scoring.sas
```

**Key principles:**
1. ✅ **Preserve filenames** through the pipeline
2. ✅ **Embed original SAS** as comments for audit trail
3. ✅ **Clear 1:1 mapping** between input/staging/approved
4. ✅ **Archive original SAS** in approved/ for compliance

---

## 🚀 Want me to update notebook 03?

I can update `03_test_conversion.py` to:
1. Preserve filenames (`.sas` → `.py` with same base name)
2. Include original SAS code as header comments
3. Show the 1:1 mapping clearly in output

Let me know and I'll make those changes!
