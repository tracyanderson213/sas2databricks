-- ============================================================
-- Check Adventure Works Database Tables
-- ============================================================
-- Run this in a Databricks notebook with JDBC connection
-- to see what tables are available in SQL Server
-- ============================================================

-- ============================================================
-- Setup: Get password from Key Vault
-- ============================================================
-- %python
-- password = dbutils.secrets.get("dbx-ss-kv-natraining-2", "natraining-sql-adventureworks-password")
-- spark.conf.set("sql.password", password)

-- ============================================================
-- Setup: Create temp view from SQL Server
-- ============================================================
-- %python
-- jdbc_url = "jdbc:sqlserver://sqldbdbxtraining.database.windows.net:1433;database=sqldb-adventureworks"
-- properties = {
--     "user": "sqladministrator@sqldbdbxtraining",
--     "password": password,
--     "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
-- }
--
-- # Query all tables
-- df = spark.read.jdbc(
--     jdbc_url,
--     "(SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE') AS tables",
--     properties=properties
-- )
-- df.createOrReplaceTempView("sql_server_tables")

-- ============================================================
-- Query 1: List ALL tables in Adventure Works
-- ============================================================
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    CONCAT(TABLE_SCHEMA, '.', TABLE_NAME) as full_name
FROM sql_server_tables
ORDER BY TABLE_SCHEMA, TABLE_NAME;

-- ============================================================
-- Query 2: Find Customer and SalesOrder tables
-- ============================================================
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    CONCAT(TABLE_SCHEMA, '.', TABLE_NAME) as full_name,
    CASE
        WHEN TABLE_NAME LIKE '%Customer%' THEN 'Customer-related'
        WHEN TABLE_NAME LIKE '%SalesOrder%' THEN 'SalesOrder-related'
        ELSE 'Other'
    END as category
FROM sql_server_tables
WHERE TABLE_NAME LIKE '%Customer%'
   OR TABLE_NAME LIKE '%SalesOrder%'
ORDER BY category, TABLE_SCHEMA, TABLE_NAME;

-- ============================================================
-- Query 3: Check specific tables we need
-- ============================================================
-- Run this to see if the exact tables exist
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    CASE
        WHEN TABLE_NAME = 'Customer' AND TABLE_SCHEMA IN ('Sales', 'SalesLT') THEN '✅ FOUND - Customer'
        WHEN TABLE_NAME = 'SalesOrderHeader' AND TABLE_SCHEMA IN ('Sales', 'SalesLT') THEN '✅ FOUND - SalesOrderHeader'
        ELSE '❓ Other'
    END as status
FROM sql_server_tables
WHERE (TABLE_NAME IN ('Customer', 'SalesOrderHeader') AND TABLE_SCHEMA IN ('Sales', 'SalesLT'))
   OR TABLE_NAME LIKE '%Customer%'
   OR TABLE_NAME LIKE '%SalesOrder%'
ORDER BY status DESC, TABLE_SCHEMA, TABLE_NAME;

-- ============================================================
-- Query 4: Get row counts (if tables exist)
-- ============================================================
-- Run this AFTER confirming tables exist:

-- For Sales schema:
-- %python
-- if table_exists("Sales.Customer"):
--     df_customer = spark.read.jdbc(jdbc_url, "Sales.Customer", properties=properties)
--     print(f"Sales.Customer: {df_customer.count()} rows")
--
-- if table_exists("Sales.SalesOrderHeader"):
--     df_orders = spark.read.jdbc(jdbc_url, "Sales.SalesOrderHeader", properties=properties)
--     print(f"Sales.SalesOrderHeader: {df_orders.count()} rows")

-- For SalesLT schema:
-- %python
-- if table_exists("SalesLT.Customer"):
--     df_customer = spark.read.jdbc(jdbc_url, "SalesLT.Customer", properties=properties)
--     print(f"SalesLT.Customer: {df_customer.count()} rows")
--
-- if table_exists("SalesLT.SalesOrderHeader"):
--     df_orders = spark.read.jdbc(jdbc_url, "SalesLT.SalesOrderHeader", properties=properties)
--     print(f"SalesLT.SalesOrderHeader: {df_orders.count()} rows")

-- ============================================================
-- Expected Results
-- ============================================================
--
-- If this is Adventure Works FULL version:
--   • Sales.Customer (~19,000 rows)
--   • Sales.SalesOrderHeader (~31,000 orders)
--
-- If this is AdventureWorksLT (light version):
--   • SalesLT.Customer (~800 rows)
--   • SalesLT.SalesOrderHeader (~32,000 orders)
--
-- Both versions are perfect for our demo!
-- ============================================================
