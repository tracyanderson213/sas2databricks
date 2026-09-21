#!/bin/bash
# ============================================================
# Adventure Works SQL Server Validation - Commands to Run
# ============================================================
# Copy and paste these commands one by one
# Estimated time: 20 minutes
# ============================================================

echo "=========================================="
echo "Step 0: Verify Prerequisites"
echo "=========================================="
python verify_sql_prerequisites.py
echo ""
echo "Press Enter to continue to Step 1..."
read

# ============================================================
# Step 1: Create UC Connection (2 minutes)
# ============================================================
echo "=========================================="
echo "Step 1: Create UC Connection"
echo "=========================================="
echo ""
echo "Creating connection to sqldbdbxtraining.database.windows.net..."
echo ""

databricks connections create \
  --name adventureworks_sql \
  --connection-type sqlserver \
  --options '{
    "host": "sqldbdbxtraining.database.windows.net",
    "port": "1433",
    "database": "sqldb-adventureworks",
    "user": "sqladministrator@sqldbdbxtraining",
    "password": "{{secrets/dbx-ss-kv-natraining-2/natraining-sql-adventureworks-password}}"
  }'

echo ""
echo "Verifying connection..."
databricks connections get adventureworks_sql

echo ""
echo "✅ Step 1 complete!"
echo ""
echo "Press Enter to continue to Step 2..."
read

# ============================================================
# Step 2: Deploy Bundle (2 minutes)
# ============================================================
echo "=========================================="
echo "Step 2: Deploy Bundle"
echo "=========================================="
echo ""
echo "Deploying databricks.yml (includes adventureworks_ingestion pipeline)..."
echo ""

databricks bundle deploy -t dev

echo ""
echo "✅ Step 2 complete!"
echo ""
echo "Press Enter to continue to Step 3..."
read

# ============================================================
# Step 3: Run Ingestion Pipeline (5 minutes)
# ============================================================
echo "=========================================="
echo "Step 3: Run Ingestion Pipeline"
echo "=========================================="
echo ""
echo "Running ingestion from SQL Server..."
echo "This will take 3-5 minutes..."
echo ""

databricks bundle run -t dev adventureworks_ingestion

echo ""
echo "✅ Step 3 complete!"
echo ""
echo "Press Enter to continue to Step 4..."
read

# ============================================================
# Step 4: Verify Tables Created (1 minute)
# ============================================================
echo "=========================================="
echo "Step 4: Verify Bronze Tables"
echo "=========================================="
echo ""
echo "Checking for customer and salesorderheader tables..."
echo ""

databricks tables list sas_dbx_tracy_anderson_bronze | grep -E 'customer|salesorderheader'

echo ""
echo "If you see 'customer' and 'salesorderheader' above, ingestion worked!"
echo ""
echo "✅ Step 4 complete!"
echo ""
echo "Press Enter to continue to Step 5..."
read

# ============================================================
# Step 5: Manual Step - Upload SAS File
# ============================================================
echo "=========================================="
echo "Step 5: Upload SAS File to Volume"
echo "=========================================="
echo ""
echo "⚠️  MANUAL STEP REQUIRED"
echo ""
echo "Copy this file:"
echo "  specifications/sales_summary.sas"
echo ""
echo "To this location:"
echo "  /Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/"
echo ""
echo "You can do this via:"
echo "  - Databricks UI (Catalog → Volumes → Upload)"
echo "  - databricks fs cp command"
echo "  - Mount the volume locally and copy"
echo ""
echo "Press Enter when file is uploaded..."
read

# ============================================================
# Step 6: Run Converter (2 minutes)
# ============================================================
echo "=========================================="
echo "Step 6: Run SAS Converter"
echo "=========================================="
echo ""
echo "Running converter on sales_summary.sas..."
echo ""

databricks bundle run -t dev sas_dbx_code_translator

echo ""
echo "✅ Step 6 complete!"
echo ""
echo "Press Enter to continue to Step 7..."
read

# ============================================================
# Step 7: List Converted Files (30 seconds)
# ============================================================
echo "=========================================="
echo "Step 7: List Converted Files"
echo "=========================================="
echo ""
echo "Checking for transformed_sales_summary.py..."
echo ""

python list_converted_files.py

echo ""
echo "✅ Step 7 complete!"
echo ""
echo "Press Enter to continue to Step 8..."
read

# ============================================================
# Step 8: Update Pipeline (1 minute)
# ============================================================
echo "=========================================="
echo "Step 8: Update Template Pipeline"
echo "=========================================="
echo ""
echo "Updating template pipeline with sales_summary transformation..."
echo ""

python update_pipeline_file.py template transformed_sales_summary.py

echo ""
echo "✅ Step 8 complete!"
echo ""
echo "Press Enter for final instructions..."
read

# ============================================================
# Step 9: Manual Step - Run Pipeline in UI
# ============================================================
echo "=========================================="
echo "Step 9: Run Pipeline & Validate"
echo "=========================================="
echo ""
echo "⚠️  MANUAL STEPS IN DATABRICKS UI"
echo ""
echo "1. Open Databricks UI"
echo "2. Go to: Workflows → Delta Live Tables"
echo "3. Find pipeline: sas_dbx_template_tracy_anderson"
echo "4. Click 'Start'"
echo "5. Wait for completion (5-10 minutes)"
echo ""
echo "6. Validate results with SQL query:"
echo ""
echo "   SELECT * FROM \`na-dbxtraining\`.sas_dbx_tracy_anderson_gold.customer_summary"
echo "   ORDER BY TotalRevenue DESC"
echo "   LIMIT 10;"
echo ""
echo "=========================================="
echo "🎉 DONE!"
echo "=========================================="
echo ""
echo "If you see customer data with revenue/tiers/churn risk,"
echo "you've successfully validated the SAS converter with SQL Server!"
echo ""
echo "✅ External database integration: PROVEN"
echo "✅ Source-agnostic converter: VALIDATED"
echo "✅ End-to-end flow: WORKING"
echo ""
