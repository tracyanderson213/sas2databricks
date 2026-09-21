#!/usr/bin/env python3
"""
Create mock Adventure Works data in Bronze layer

This script creates sample Customer and SalesOrderHeader tables
to simulate data that would be ingested from Azure SQL Server
via Lakeflow Connect.

In production, replace this with actual Lakeflow Connect pipeline.
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

WAREHOUSE_ID = "2f51df324d05e45d"
CATALOG = "na-dbxtraining"

# Get developer_id from workspace current user
user = w.current_user.me()
developer_id = user.user_name.split('@')[0].replace('.', '_')
SCHEMA_BRONZE = f"sas_{developer_id}_bronze"  # Correct naming: sas_tanderson_bronze

print("=" * 80)
print("🏗️  Creating Mock Adventure Works Data")
print("=" * 80)
print()
print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA_BRONZE}")
print()

# SQL to create mock tables
sql = f"""
-- ============================================================
-- Mock Adventure Works Customer Table
-- ============================================================
CREATE OR REPLACE TABLE `{CATALOG}`.`{SCHEMA_BRONZE}`.customer AS
SELECT
    id as CustomerID,
    concat('Company ', lpad(cast(id as string), 3, '0')) as CompanyName,
    concat('contact', id, '@company', id, '.com') as EmailAddress,
    CASE
        WHEN id % 3 = 0 THEN 'John'
        WHEN id % 3 = 1 THEN 'Jane'
        ELSE 'Alex'
    END as FirstName,
    CASE
        WHEN id % 4 = 0 THEN 'Smith'
        WHEN id % 4 = 1 THEN 'Johnson'
        WHEN id % 4 = 2 THEN 'Williams'
        ELSE 'Brown'
    END as LastName,
    CASE
        WHEN id % 5 = 0 THEN '123 Main St'
        WHEN id % 5 = 1 THEN '456 Oak Ave'
        WHEN id % 5 = 2 THEN '789 Elm Blvd'
        WHEN id % 5 = 3 THEN '321 Pine Rd'
        ELSE '654 Maple Dr'
    END as AddressLine1
FROM range(1, 101);

-- ============================================================
-- Mock Adventure Works SalesOrderHeader Table
-- ============================================================
CREATE OR REPLACE TABLE `{CATALOG}`.`{SCHEMA_BRONZE}`.salesorderheader AS
SELECT
    id as SalesOrderID,
    -- Customer IDs from 1-100
    ((id - 1) % 100) + 1 as CustomerID,
    -- Order dates spanning 2 years
    date_add('2023-01-01', cast((id % 730) as int)) as OrderDate,
    -- Ship dates 3-7 days after order
    date_add(date_add('2023-01-01', cast((id % 730) as int)), 3 + cast((id % 5) as int)) as ShipDate,
    -- Order status
    CASE
        WHEN id % 10 = 0 THEN 'Pending'
        WHEN id % 10 = 1 THEN 'Shipped'
        ELSE 'Delivered'
    END as Status,
    -- Subtotal: $100-$5000
    100 + (cast(rand(id) * 4900 as decimal(10,2))) as SubTotal,
    -- Tax: 8% of subtotal
    (100 + (cast(rand(id) * 4900 as decimal(10,2)))) * 0.08 as TaxAmt,
    -- Freight: $10-$50
    10 + (cast(rand(id * 2) * 40 as decimal(10,2))) as Freight,
    -- TotalDue = SubTotal + Tax + Freight
    (100 + (cast(rand(id) * 4900 as decimal(10,2)))) * 1.08 +
    (10 + (cast(rand(id * 2) * 40 as decimal(10,2)))) as TotalDue
FROM range(1, 501);

-- ============================================================
-- Verify data created
-- ============================================================
SELECT 'customer' as table_name, COUNT(*) as row_count
FROM `{CATALOG}`.`{SCHEMA_BRONZE}`.customer

UNION ALL

SELECT 'salesorderheader' as table_name, COUNT(*) as row_count
FROM `{CATALOG}`.`{SCHEMA_BRONZE}`.salesorderheader;
"""

print("📝 Creating tables...")
print()

try:
    result = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=sql,
        wait_timeout="50s"
    )

    # Get row counts from result
    if result.result and result.result.data_array:
        print("✅ Tables created successfully!")
        print()
        print("Row counts:")
        for row in result.result.data_array:
            table_name = row[0]
            row_count = row[1]
            print(f"  • {table_name}: {row_count} rows")

    print()
    print("=" * 80)
    print("✅ Mock Data Creation Complete!")
    print("=" * 80)
    print()
    print("Tables created:")
    print(f"  • `{CATALOG}`.`{SCHEMA_BRONZE}`.customer")
    print(f"  • `{CATALOG}`.`{SCHEMA_BRONZE}`.salesorderheader")
    print()
    print("Sample data:")
    print("  • 100 customers")
    print("  • 500 orders")
    print("  • Date range: 2023-01-01 to 2024-12-31")
    print("  • Order values: $100-$5,000")
    print()
    print("Next steps:")
    print("  1. Upload SAS file: cp specifications/sales_summary.sas /Volumes/.../staging/")
    print("  2. Run converter: databricks bundle run -t dev sas_dbx_code_translator")
    print("  3. Update pipeline: python update_pipeline_file.py sales_summary transformed_sales_summary.py")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    print()
    import traceback
    traceback.print_exc()
