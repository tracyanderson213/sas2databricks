#!/bin/bash
# ============================================================================
# Sales Summary Conversion Test - One-Command Execution
# ============================================================================
# This script runs the complete workflow to test sales_summary.sas conversion
#
# Prerequisites:
#   - Databricks CLI configured
#   - DAB bundle deployed (databricks bundle deploy -t dev)
#   - Python environment with databricks-sdk
#
# Usage:
#   chmod +x run_sales_summary_test.sh
#   ./run_sales_summary_test.sh
# ============================================================================

set -e  # Exit on any error

echo "======================================================================"
echo "Sales Summary Conversion Test"
echo "======================================================================"
echo ""

# ============================================================================
# Step 1: Create Mock Bronze Data
# ============================================================================
echo "Step 1: Creating mock Adventure Works data in Bronze..."
python create_adventureworks_mock_data.py

if [ $? -eq 0 ]; then
    echo "✓ Bronze data created successfully"
else
    echo "✗ Failed to create Bronze data"
    exit 1
fi
echo ""

# ============================================================================
# Step 2: Verify Bronze Tables
# ============================================================================
echo "Step 2: Verifying Bronze tables exist..."
python verify_bronze_tables.py

if [ $? -eq 0 ]; then
    echo "✓ Bronze tables verified"
else
    echo "✗ Bronze tables not found"
    exit 1
fi
echo ""

# ============================================================================
# Step 3: Upload SAS File to Volume
# ============================================================================
echo "Step 3: Uploading sales_summary.sas to staging volume..."
databricks fs cp specifications/sales_summary.sas \
  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/sales_summary.sas \
  --overwrite

if [ $? -eq 0 ]; then
    echo "✓ SAS file uploaded"
else
    echo "✗ Failed to upload SAS file"
    exit 1
fi
echo ""

# ============================================================================
# Step 4: Run Converter
# ============================================================================
echo "Step 4: Running converter job..."
echo "(This may take 2-5 minutes...)"
databricks bundle run -t dev sas_dbx_code_translator

if [ $? -eq 0 ]; then
    echo "✓ Converter completed"
else
    echo "✗ Converter failed"
    exit 1
fi
echo ""

# ============================================================================
# Step 5: Download Converted File
# ============================================================================
echo "Step 5: Downloading converted file..."
mkdir -p transformations

databricks fs cp \
  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/converted/transformed_sales_summary.py \
  transformations/transformed_sales_summary.py \
  --overwrite

if [ $? -eq 0 ]; then
    echo "✓ Converted file downloaded to transformations/transformed_sales_summary.py"
else
    echo "✗ Failed to download converted file"
    exit 1
fi
echo ""

# ============================================================================
# Step 6: Analyze Converted Output
# ============================================================================
echo "Step 6: Analyzing converted output..."
echo ""

echo "Layer breakdown:"
grep -E "# - .*→.*(bronze|silver|gold)" transformations/transformed_sales_summary.py | head -15
echo ""

echo "Tables/Views created:"
grep "@dp\.\(table\|view\|materialized_view\)(name=" transformations/transformed_sales_summary.py
echo ""

echo "Expectations generated (commented):"
grep "# @dp.expect" transformations/transformed_sales_summary.py | wc -l
echo "expectations found (review and enable as needed)"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "======================================================================"
echo "✓ Sales Summary Conversion Test COMPLETE"
echo "======================================================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Review converted file:"
echo "   cat transformations/transformed_sales_summary.py | less"
echo ""
echo "2. Create pipeline configuration:"
echo "   See: resources/pipelines/sales_summary_pipeline.yml (example)"
echo ""
echo "3. Deploy and run pipeline:"
echo "   databricks bundle deploy -t dev"
echo "   databricks bundle run -t dev sales_summary_pipeline"
echo ""
echo "4. Verify results:"
echo "   SELECT * FROM sas_tanderson_gold.customer_summary LIMIT 10;"
echo "   SELECT * FROM sas_tanderson_gold.sales_statistics;"
echo ""
echo "Full guide: RUN_SALES_SUMMARY_CONVERSION.md"
echo "======================================================================"
