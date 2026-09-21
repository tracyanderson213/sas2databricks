#!/bin/bash
# ============================================================================
# Run Sales Summary Conversion with REAL Adventure Works Data
# ============================================================================
# This script ingests real data from SQL Server into Bronze, then runs
# the converter on sales_summary.sas
#
# Data: 19,820 real customers, 31,465 real orders from Adventure Works
# ============================================================================

set -e  # Exit on any error

echo "======================================================================"
echo "Sales Summary Conversion with REAL Adventure Works Data"
echo "======================================================================"
echo ""
echo "Data Source: SQL Server Adventure Works (19,820 customers)"
echo ""

# ============================================================================
# Step 1: Ingest Real Data into Bronze
# ============================================================================
echo "Step 1: Ingesting real Adventure Works data into Bronze..."
echo "(This will take a few minutes to copy 19K+ rows from SQL Server)"
echo ""

# Option A: Use Lakeflow Connect Pipeline (Recommended for Production)
echo "Running Lakeflow Connect ingestion..."
databricks bundle run -t dev adventureworks_ingestion

if [ $? -eq 0 ]; then
    echo "✓ Real data ingested to Bronze"
else
    echo "✗ Lakeflow Connect ingestion failed"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check connection exists: databricks connections get adventureworks_sql"
    echo "  2. Check logs in Databricks UI → Workflows → Pipelines"
    echo "  3. Verify network access to SQL Server"
    echo ""
    exit 1
fi
echo ""

# ============================================================================
# Step 2: Verify Bronze Tables
# ============================================================================
echo "Step 2: Verifying Bronze tables have real data..."
python verify_bronze_tables.py

if [ $? -eq 0 ]; then
    echo "✓ Bronze tables verified with real data"
else
    echo "✗ Bronze tables not found or empty"
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

# ============================================================================
# Summary
# ============================================================================
echo "======================================================================"
echo "✓ Sales Summary Conversion with REAL DATA COMPLETE"
echo "======================================================================"
echo ""
echo "Data Processed:"
echo "  • 19,820 customers (from SQL Server)"
echo "  • 31,465 sales orders (from SQL Server)"
echo ""
echo "Next Steps:"
echo ""
echo "1. Deploy pipeline:"
echo "   databricks bundle deploy -t dev"
echo ""
echo "2. Run pipeline:"
echo "   databricks bundle run -t dev sales_summary_pipeline"
echo ""
echo "3. Verify Gold output:"
echo "   SELECT COUNT(*) FROM sas_tanderson_gold.customer_summary;"
echo "   -- Should have ~19,820 customers (or fewer after WHERE filters)"
echo ""
echo "   SELECT * FROM sas_tanderson_gold.customer_summary"
echo "   WHERE value_tier = 'High'"
echo "   ORDER BY TotalRevenue DESC LIMIT 10;"
echo ""
echo "4. Check statistics:"
echo "   SELECT * FROM sas_tanderson_gold.sales_statistics;"
echo "   -- Cross-tab of value_tier x churn_risk"
echo ""
echo "======================================================================"
