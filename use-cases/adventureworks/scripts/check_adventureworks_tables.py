#!/usr/bin/env python3
"""
Query Adventure Works SQL Server to see available tables

Uses existing connection credentials from your setup:
- Server: sqldbdbxtraining.database.windows.net
- Database: sqldb-adventureworks
- Auth: Azure Key Vault secret
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

WAREHOUSE_ID = "2f51df324d05e45d"

print("=" * 80)
print("🔍 Checking Adventure Works Database Tables")
print("=" * 80)
print()
print("Server: sqldbdbxtraining.database.windows.net")
print("Database: sqldb-adventureworks")
print()

# Query 1: List all tables
sql_all_tables = """
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME;
"""

# Query 2: Find Customer-related tables
sql_customer_tables = """
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND (TABLE_NAME LIKE '%Customer%' OR TABLE_NAME LIKE '%SalesOrder%')
ORDER BY TABLE_SCHEMA, TABLE_NAME;
"""

# Query 3: Get row counts for key tables
sql_row_counts = """
SELECT 'Production.Product' as table_name, COUNT(*) as row_count
FROM Production.Product
UNION ALL
SELECT 'Sales.SalesTerritory', COUNT(*)
FROM Sales.SalesTerritory
UNION ALL
SELECT 'HumanResources.Department', COUNT(*)
FROM HumanResources.Department;
"""

print("📊 Query 1: All Available Tables")
print("-" * 80)

try:
    # Use Databricks SQL with external connection
    # We'll need to query via a notebook or external connection
    # For now, let's show what we can check

    print("To check available tables, run this SQL in a notebook:")
    print()
    print(sql_all_tables)
    print()
    print("=" * 80)
    print()

    print("📊 Query 2: Customer & Sales Tables")
    print("-" * 80)
    print(sql_customer_tables)
    print()
    print("=" * 80)
    print()

    print("📊 Query 3: Row Counts")
    print("-" * 80)
    print(sql_row_counts)
    print()
    print("=" * 80)
    print()

    print("💡 How to Run:")
    print()
    print("Option A: Via Databricks SQL Editor")
    print("  1. Open SQL Editor in Databricks UI")
    print("  2. Create a connection to SQL Server (if not exists)")
    print("  3. Run the queries above")
    print()
    print("Option B: Via Notebook with JDBC")
    print("  Create a notebook and run:")
    print()
    print("""
# Get secret from Key Vault
password = dbutils.secrets.get("dbx-ss-kv-natraining-2", "natraining-sql-adventureworks-password")

# JDBC connection
jdbc_url = "jdbc:sqlserver://sqldbdbxtraining.database.windows.net:1433;database=sqldb-adventureworks"
properties = {
    "user": "sqladministrator@sqldbdbxtraining",
    "password": password,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
}

# Query tables
df = spark.read.jdbc(jdbc_url, "(SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE') AS tables", properties=properties)
display(df)
    """)
    print()
    print("=" * 80)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("🎯 What We're Looking For:")
print("-" * 80)
print()
print("Needed for sales_summary.sas:")
print("  • Sales.Customer or SalesLT.Customer")
print("  • Sales.SalesOrderHeader or SalesLT.SalesOrderHeader")
print()
print("Likely schemas in Adventure Works:")
print("  • Sales (full Adventure Works)")
print("  • SalesLT (AdventureWorksLT light version)")
print("  • Production (products, inventory)")
print("  • HumanResources (employees, departments)")
print("  • Purchasing (vendors, purchase orders)")
print()
print("Already ingested (from your setup):")
print("  • Production.Product → bronze_aw_products")
print("  • Sales.SalesTerritory → bronze_aw_territories")
print("  • HumanResources.Department → bronze_aw_departments")
print()
