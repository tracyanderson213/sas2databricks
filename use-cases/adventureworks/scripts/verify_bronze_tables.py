#!/usr/bin/env python3
"""
Verify Bronze tables exist in Databricks with correct schema naming

Checks:
- Schema: sas_{developer_id}_bronze (e.g., sas_tanderson_bronze)
- Tables: customer, salesorderheader
- Row counts
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
SCHEMA_BRONZE = f"sas_{developer_id}_bronze"

print("=" * 80)
print("🔍 Verifying Bronze Tables in Databricks")
print("=" * 80)
print()
print(f"Catalog: {CATALOG}")
print(f"Schema:  {SCHEMA_BRONZE}")
print()

# Check schema exists
print("Checking schema...")
sql_check_schema = f"SHOW SCHEMAS IN `{CATALOG}` LIKE '{SCHEMA_BRONZE}'"

try:
    result = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=sql_check_schema,
        wait_timeout="30s"
    )

    if result.result and result.result.data_array:
        print(f"✓ Schema exists: {SCHEMA_BRONZE}")
    else:
        print(f"✗ Schema NOT found: {SCHEMA_BRONZE}")
        print(f"  Create it with: python create_adventureworks_mock_data.py")
        exit(1)
except Exception as e:
    print(f"✗ Error checking schema: {e}")
    exit(1)

print()

# Check tables
tables_to_check = ['customer', 'salesorderheader']

for table in tables_to_check:
    print(f"Checking table: {table}...")

    # Check if table exists
    sql_check_table = f"SHOW TABLES IN `{CATALOG}`.`{SCHEMA_BRONZE}` LIKE '{table}'"

    try:
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=sql_check_table,
            wait_timeout="30s"
        )

        if result.result and result.result.data_array:
            print(f"  ✓ Table exists: {table}")

            # Get row count
            sql_count = f"SELECT COUNT(*) as cnt FROM `{CATALOG}`.`{SCHEMA_BRONZE}`.`{table}`"

            result_count = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement=sql_count,
                wait_timeout="30s"
            )

            if result_count.result and result_count.result.data_array:
                row_count = result_count.result.data_array[0][0]
                print(f"  ✓ Row count: {row_count}")

                if row_count == 0:
                    print(f"  ⚠️  Warning: Table is empty!")
            else:
                print(f"  ⚠️  Could not get row count")
        else:
            print(f"  ✗ Table NOT found: {table}")
            print(f"    Create it with: python create_adventureworks_mock_data.py")

    except Exception as e:
        print(f"  ✗ Error checking table: {e}")

    print()

print("=" * 80)
print("✓ Verification Complete")
print("=" * 80)
print()
print("Bronze tables should be in schema:")
print(f"  {CATALOG}.{SCHEMA_BRONZE}.*")
print()
print("Expected tables:")
print(f"  - {SCHEMA_BRONZE}.customer (50 rows)")
print(f"  - {SCHEMA_BRONZE}.salesorderheader (200 rows)")
print()
