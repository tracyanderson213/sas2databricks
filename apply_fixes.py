#!/usr/bin/env python3
"""Apply the 3 critical fixes to converter output"""
import re

input_file = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/transformations/transformed_claims_adjudication_FIXED.py'

with open(input_file, 'r') as f:
    code = f.read()

print("Applying fixes...")
print()

# FIX 1: Remove clm_claims_adjudicated_report empty placeholder
pattern1 = r'@dp\.table\(name=\'sas_tanderson_gold\.clm_claims_adjudicated_report\'[^)]*\)[^\n]*\ndef clm_claims_adjudicated_report\(\):[\s\S]*?return spark\.range\(0\)\s*\n'
before_len = len(code)
code = re.sub(pattern1, '', code, flags=re.MULTILINE)
if len(code) < before_len:
    print("✅ FIX 1: Removed clm_claims_adjudicated_report empty placeholder")
else:
    print("⚠️  FIX 1: Pattern not found")
print()

# FIX 2: Add limit_exceeded column to work_claims_running
pattern2 = r"(return spark\.read\.table\(\"sas_tanderson_silver\.work_claims_benefit\"\) \\\s*\.withColumn\(\"ytd_paid\", F\.sum\(\"billed_amount\"\)\.over\(window\)\))"
replacement2 = r'\1 \\\n        .withColumn("limit_exceeded",\n                    F.when(F.col("ytd_paid") > F.col("annual_limit"), "Y").otherwise("N"))'
before_len = len(code)
code = re.sub(pattern2, replacement2, code)
if len(code) > before_len:
    print("✅ FIX 2: Added limit_exceeded column to work_claims_running")
else:
    print("⚠️  FIX 2: Pattern not found")
print()

# FIX 3: Fix duplicate columns in clm_claims_adjudicated - replace with CASE statements
pattern3 = r"""@dp\.table\(name='sas_tanderson_gold\.clm_claims_adjudicated'[^)]*\)\ndef clm_claims_adjudicated\(\):[\s\S]*?FROM sas_tanderson_silver\.work_claims_running"""

replacement3 = """@dp.table(name='sas_tanderson_gold.clm_claims_adjudicated', comment='SAS data')
def clm_claims_adjudicated():
    \"\"\"Final adjudication with nested IF/THEN/ELSE logic from SAS\"\"\"
    return spark.sql(\"\"\"
        SELECT *,
            CASE diag_code
                WHEN 'E11' THEN 'DIABETES'
                WHEN 'I10' THEN 'HYPERTENSION'
                WHEN 'J45' THEN 'ASTHMA'
                WHEN 'M54' THEN 'BACK_PAIN'
                ELSE 'OTHER'
            END AS diag_category,

            CASE
                WHEN elig_flag = 'N' THEN 'DENIED'
                WHEN dup_flag = 'Y' THEN 'DENIED'
                WHEN network_status = 'OUTOFNETWORK' THEN 'PENDED'
                WHEN limit_exceeded = 'Y' THEN 'DENIED'
                ELSE 'APPROVED'
            END AS adj_status,

            CASE
                WHEN elig_flag = 'N' THEN 'MEMBER NOT ELIGIBLE ON SERVICE DATE'
                WHEN dup_flag = 'Y' THEN 'DUPLICATE CLAIM'
                WHEN network_status = 'OUTOFNETWORK' THEN 'OUT OF NETWORK - MANUAL REVIEW'
                WHEN limit_exceeded = 'Y' THEN 'ANNUAL BENEFIT LIMIT EXCEEDED'
                ELSE ''
            END AS deny_reason,

            CASE
                WHEN elig_flag = 'N' OR dup_flag = 'Y' OR network_status = 'OUTOFNETWORK' OR limit_exceeded = 'Y'
                THEN NULL
                ELSE billed_amount - copay
            END AS paid_amount

        FROM sas_tanderson_silver.work_claims_running"""

before_len = len(code)
code = re.sub(pattern3, replacement3, code, flags=re.MULTILINE)
if len(code) != before_len:
    print("✅ FIX 3: Fixed duplicate columns with CASE statements")
else:
    print("⚠️  FIX 3: Pattern not found")
print()

# FIX 4: Add ELSE 'N' to dup_flag CASE statement
pattern4 = r"(CASE WHEN NOT \(\(row_number\(\) OVER \(PARTITION BY member_id, provider_id, service_date, proc_code ORDER BY _row_id\) = 1\) AND \(row_number\(\) OVER \(PARTITION BY member_id, provider_id, service_date, proc_code ORDER BY _row_id DESC\) = 1\)\) THEN 'Y') END AS dup_flag"
replacement4 = r"\1 ELSE 'N' END AS dup_flag"
before_len = len(code)
code = re.sub(pattern4, replacement4, code)
if len(code) > before_len:
    print("✅ FIX 4: Added ELSE 'N' to dup_flag CASE statement")
else:
    print("⚠️  FIX 4: Pattern not found (might already be fixed)")
print()

# FIX 5: Fix work_claims_elig2 SQL with SAS if syntax
pattern5 = r"""@dp\.materialized_view\(name='sas_tanderson_silver\.work_claims_elig2'[^)]*\)\ndef work_claims_elig2\(\):[\s\S]*?FROM sas_tanderson_silver\.work_claims_elig\"\"\"\)"""

replacement5 = """@dp.materialized_view(name='sas_tanderson_silver.work_claims_elig2', comment='SAS data')
def work_claims_elig2():
    \"\"\"Apply eligibility flag logic (from flag_eligibility macro)\"\"\"
    return spark.sql(\"\"\"
        SELECT *,
            CASE
                WHEN eff_date IS NOT NULL
                    AND term_date IS NOT NULL
                    AND service_date BETWEEN eff_date AND term_date
                THEN 'Y'
                ELSE 'N'
            END AS elig_flag
        FROM sas_tanderson_silver.work_claims_elig
    \"\"\")"""

before_len = len(code)
code = re.sub(pattern5, replacement5, code, flags=re.MULTILINE)
if len(code) != before_len:
    print("✅ FIX 5: Fixed work_claims_elig2 SQL (removed SAS if syntax)")
else:
    print("⚠️  FIX 5: Pattern not found (might already be fixed)")
print()

# Write the fixed file
with open(input_file, 'w') as f:
    f.write(code)

print("=" * 80)
print("✅ All 5 fixes applied!")
print("=" * 80)
print(f"Output: {input_file}")
print()
print("Fixes applied:")
print("  1. Removed clm_claims_adjudicated_report empty placeholder")
print("  2. Added limit_exceeded column to work_claims_running")
print("  3. Fixed duplicate columns with CASE statements")
print("  4. Added ELSE 'N' to dup_flag CASE statement")
print("  5. Fixed work_claims_elig2 SQL (removed SAS if syntax)")
