#!/usr/bin/env python3
"""
Ingest real Adventure Works data from SQL Server into Bronze layer

This is a quick alternative to Lakeflow Connect for testing.
For production, use Lakeflow Connect pipeline instead.

What this does:
1. Connects to SQL Server Adventure Works database
2. Reads Sales.Customer (19,820 rows)
3. Reads Sales.SalesOrderHeader (31,465 rows)
4. Writes to Bronze tables in Databricks
"""
import os
from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession

print("=" * 80)
print("🏗️  Ingesting Real Adventure Works Data into Bronze")
print("=" * 80)
print()

# Initialize
os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

# Get developer_id
user = w.current_user.me()
developer_id = user.user_name.split('@')[0].replace('.', '_')

CATALOG = "na-dbxtraining"
SCHEMA_BRONZE = f"sas_{developer_id}_bronze"

print(f"Target Schema: {CATALOG}.{SCHEMA_BRONZE}")
print()

# SQL Server connection details
print("Retrieving password from Key Vault...")
try:
    # This assumes you're running in a Databricks notebook context
    # For CLI, you'd need to use the SDK to access secrets
    from databricks.sdk.service.workspace import ExportFormat

    # Get password from Azure Key Vault via Databricks
    # Note: This may require running in a notebook with dbutils available
    password = w.secrets.get_secret(
        scope="dbx-ss-kv-natraining-2",
        key="natraining-sql-adventureworks-password"
    )
    print("✓ Password retrieved")
except Exception as e:
    print(f"✗ Could not retrieve password: {e}")
    print()
    print("This script must run in a Databricks environment with secret access.")
    print("Alternative: Run check_adventureworks_tables_notebook.py in Databricks UI")
    exit(1)

print()

# JDBC configuration
jdbc_url = "jdbc:sqlserver://sqldbdbxtraining.database.windows.net:1433;database=sqldb-adventureworks"
connection_properties = {
    "user": "sqladministrator@sqldbdbxtraining",
    "password": password,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
}

print("Connecting to SQL Server...")
print(f"  Server: sqldbdbxtraining.database.windows.net")
print(f"  Database: sqldb-adventureworks")
print()

# Create Spark session
spark = SparkSession.builder.appName("AdventureWorks Ingestion").getOrCreate()

# ============================================================================
# Ingest Customer Table
# ============================================================================
print("=" * 80)
print("Ingesting Sales.Customer...")
print("=" * 80)

# Read from SQL Server (no ORDER BY in subquery!)
query_customer = """
SELECT
    CustomerID,
    CompanyName,
    FirstName,
    LastName,
    EmailAddress,
    Phone
FROM Sales.Customer
"""

print("Reading from SQL Server...")
df_customer = spark.read.jdbc(
    jdbc_url,
    f"({query_customer}) AS customer",
    properties=connection_properties
)

row_count = df_customer.count()
print(f"✓ Read {row_count:,} customers from SQL Server")
print()

# Write to Bronze
target_table = f"{CATALOG}.{SCHEMA_BRONZE}.customer"
print(f"Writing to {target_table}...")

df_customer.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(target_table)

print(f"✓ Wrote {row_count:,} customers to Bronze")
print()

# ============================================================================
# Ingest SalesOrderHeader Table
# ============================================================================
print("=" * 80)
print("Ingesting Sales.SalesOrderHeader...")
print("=" * 80)

# Read from SQL Server (no ORDER BY!)
query_orders = """
SELECT
    SalesOrderID,
    CustomerID,
    OrderDate,
    DueDate,
    ShipDate,
    Status,
    SubTotal,
    TaxAmt,
    Freight,
    TotalDue
FROM Sales.SalesOrderHeader
"""

print("Reading from SQL Server...")
df_orders = spark.read.jdbc(
    jdbc_url,
    f"({query_orders}) AS orders",
    properties=connection_properties
)

row_count_orders = df_orders.count()
print(f"✓ Read {row_count_orders:,} orders from SQL Server")
print()

# Write to Bronze
target_table_orders = f"{CATALOG}.{SCHEMA_BRONZE}.salesorderheader"
print(f"Writing to {target_table_orders}...")

df_orders.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(target_table_orders)

print(f"✓ Wrote {row_count_orders:,} orders to Bronze")
print()

# ============================================================================
# Summary
# ============================================================================
print("=" * 80)
print("✓ Real Adventure Works Data Ingested Successfully")
print("=" * 80)
print()
print(f"Bronze Schema: {CATALOG}.{SCHEMA_BRONZE}")
print()
print("Tables created:")
print(f"  • {SCHEMA_BRONZE}.customer ({row_count:,} rows)")
print(f"  • {SCHEMA_BRONZE}.salesorderheader ({row_count_orders:,} rows)")
print()
print("Next step: Run converter on sales_summary.sas")
print("  ./run_with_real_data.sh")
print()
