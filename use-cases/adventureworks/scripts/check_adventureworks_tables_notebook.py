# Databricks notebook source
# MAGIC %md
# MAGIC # Check Adventure Works Database Tables
# MAGIC
# MAGIC Query SQL Server to see what tables are available for the SAS migration demo.
# MAGIC
# MAGIC **What we're looking for:**
# MAGIC - `Sales.Customer` or `SalesLT.Customer`
# MAGIC - `Sales.SalesOrderHeader` or `SalesLT.SalesOrderHeader`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Get Password from Key Vault

# COMMAND ----------

# Get password from Azure Key Vault
password = dbutils.secrets.get("dbx-ss-kv-natraining-2", "natraining-sql-adventureworks-password")
print("✅ Password retrieved from Key Vault")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Configure JDBC Connection

# COMMAND ----------

jdbc_url = "jdbc:sqlserver://sqldbdbxtraining.database.windows.net:1433;database=sqldb-adventureworks"

connection_properties = {
    "user": "sqladministrator@sqldbdbxtraining",
    "password": password,
    "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
}

print("✅ JDBC connection configured")
print(f"   Server: sqldbdbxtraining.database.windows.net")
print(f"   Database: sqldb-adventureworks")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Query All Tables

# COMMAND ----------

# Query system tables to see what's available
# NOTE: ORDER BY removed - SQL Server prohibits ORDER BY in derived tables
# unless TOP or OFFSET is specified. Spark wraps this as a subquery.
query = """
SELECT
    TABLE_SCHEMA,
    TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
"""

df_all_tables = spark.read.jdbc(
    jdbc_url,
    f"({query}) AS tables",
    properties=connection_properties
)

print(f"📊 Found {df_all_tables.count()} tables in Adventure Works database:")
print()
display(df_all_tables)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Find Customer & SalesOrder Tables

# COMMAND ----------

# Filter to Customer and SalesOrder related tables
df_filtered = df_all_tables.filter(
    (df_all_tables.TABLE_NAME.like('%Customer%')) |
    (df_all_tables.TABLE_NAME.like('%SalesOrder%'))
)

print("🔍 Customer & SalesOrder Related Tables:")
print()
display(df_filtered)

# Store for next step
customer_sales_tables = df_filtered.collect()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Check for Exact Tables We Need

# COMMAND ----------

import pandas as pd

# Check if the exact tables we need exist
needed_tables = [
    ("Sales", "Customer"),
    ("Sales", "SalesOrderHeader"),
    ("SalesLT", "Customer"),
    ("SalesLT", "SalesOrderHeader")
]

results = []
for schema, table in needed_tables:
    exists = any(
        row.TABLE_SCHEMA == schema and row.TABLE_NAME == table
        for row in customer_sales_tables
    )
    results.append({
        "Schema": schema,
        "Table": table,
        "Full Name": f"{schema}.{table}",
        "Status": "✅ EXISTS" if exists else "❌ NOT FOUND"
    })

df_results = pd.DataFrame(results)
print("📋 Table Availability:")
print()
display(df_results)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Get Row Counts (If Tables Exist)

# COMMAND ----------

# Function to safely get row count
def get_row_count(schema, table):
    try:
        df = spark.read.jdbc(
            jdbc_url,
            f"{schema}.{table}",
            properties=connection_properties
        )
        return df.count()
    except Exception as e:
        return f"Error: {str(e)[:50]}"

# Try both Sales and SalesLT schemas
row_counts = []

for schema in ["Sales", "SalesLT"]:
    for table in ["Customer", "SalesOrderHeader"]:
        full_name = f"{schema}.{table}"
        count = get_row_count(schema, table)

        if isinstance(count, int):
            row_counts.append({
                "Table": full_name,
                "Row Count": f"{count:,}",
                "Status": "✅ Available"
            })
            print(f"✅ {full_name}: {count:,} rows")
        else:
            print(f"❌ {full_name}: Not accessible")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Summary & Recommendations

# COMMAND ----------

print("=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print()

# Determine which schema has the tables
has_sales = any(r["Schema"] == "Sales" and r["Status"] == "✅ EXISTS" for r in results)
has_saleslt = any(r["Schema"] == "SalesLT" and r["Status"] == "✅ EXISTS" for r in results)

if has_sales:
    print("✅ Adventure Works FULL version detected!")
    print()
    print("Available tables:")
    print("  • Sales.Customer")
    print("  • Sales.SalesOrderHeader")
    print()
    print("🎯 Recommended Action:")
    print("  1. Use schema: Sales")
    print("  2. Ingest: Sales.Customer, Sales.SalesOrderHeader")
    print("  3. Run sales_summary.sas (update to use Sales schema)")
    print()

elif has_saleslt:
    print("✅ AdventureWorksLT (Light) version detected!")
    print()
    print("Available tables:")
    print("  • SalesLT.Customer")
    print("  • SalesLT.SalesOrderHeader")
    print()
    print("🎯 Recommended Action:")
    print("  1. Use schema: SalesLT")
    print("  2. Ingest: SalesLT.Customer, SalesLT.SalesOrderHeader")
    print("  3. Run sales_summary.sas (update to use SalesLT schema)")
    print()

else:
    print("❌ Neither Sales nor SalesLT schema found with required tables")
    print()
    print("🎯 Recommended Action:")
    print("  1. Use existing tables instead:")
    print("     • Production.Product")
    print("     • Sales.SalesTerritory")
    print("     • HumanResources.Department")
    print("  2. Create product_territory_analysis.sas")
    print()

print("=" * 80)
print()
print("Next Steps:")
print("  1. Copy the schema name from above (Sales or SalesLT)")
print("  2. Update lakeflow_connect_adventureworks.yml with correct schema")
print("  3. Deploy and run ingestion pipeline")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: Preview Data

# COMMAND ----------

# Uncomment to preview data from available tables

# # Example: Preview Customer table
# if has_sales:
#     df_customer = spark.read.jdbc(jdbc_url, "Sales.Customer", properties=connection_properties)
#     display(df_customer.limit(10))
# elif has_saleslt:
#     df_customer = spark.read.jdbc(jdbc_url, "SalesLT.Customer", properties=connection_properties)
#     display(df_customer.limit(10))
