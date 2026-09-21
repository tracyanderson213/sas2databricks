# ==============================================================================
# TRANSFORMED SAS PIPELINE - PRODUCTION READY (WITH INTELLIGENT LAYER DETECTION)
# ==============================================================================
# Name:           transformed_sales_summary_fixed.py
# Original File:  sales_summary_fixed.sas
# Purpose:        Transformed from SAS to Spark Declarative Pipeline (SDP)
# Author:         3Cloud SAS Migration Team
# Transformed:    2026-09-21
# Target:         Databricks SDP (Spark Declarative Pipelines)
# Model:          sas2databricks
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# 2026-09-21 | 3Cloud SAS Migration Team | Initial transformation from SAS
# ------------------------------------------------------------------------------
#
# Medallion Layer Analysis:
# ------------------------------------------------------------------------------
# - work_customers                 → silver layer (sas_tanderson_silver)  [TABLE]
# - work_orders                    → silver layer (sas_tanderson_silver)  [TABLE]
# - work_customer_metrics          → gold   layer (sas_tanderson_gold)  [TABLE]
# - work_customer_classified       → silver layer (sas_tanderson_silver)  [TABLE]
# - sas_tanderson_gold_customer_summary → gold   layer (sas_tanderson_gold)  [TABLE]
# - sas_tanderson_gold_sales_statistics → silver layer (sas_tanderson_silver)  [TABLE]
# ------------------------------------------------------------------------------
#
# Notes:
# - Layer detection: Bronze (raw), Silver (transforms), Gold (aggregates)
# - View optimization: Intermediate tables converted to views for efficiency
# - Review business logic carefully before deploying to production
# - Test with sample data before running on full dataset
#
# ==============================================================================

# ==============================================================================
# PARAMETERS (Widget-Driven)
# ==============================================================================

# Unity Catalog configuration (default values, override with widgets)
CATALOG = "na-dbxtraining"
SCHEMA_BRONZE = "sas_tanderson_bronze"    # Raw data ingestion layer (e.g., sas_tanderson_bronze)
SCHEMA_SILVER = "sas_tanderson_silver"    # Business logic transformation layer (e.g., sas_tanderson_silver)
SCHEMA_GOLD = "sas_tanderson_gold"        # Aggregated metrics and reporting layer (e.g., sas_tanderson_gold)

# Source paths
SOURCE_VOLUME = f"/Volumes/{CATALOG}/{SCHEMA_BRONZE}/sas_migration"
INPUT_PATH = f"{SOURCE_VOLUME}/input"

# Data quality settings
ENABLE_EXPECTATIONS = True
EXPECTATION_ACTION = "drop"  # Options: "drop", "fail", "warn"

# View optimization
ENABLE_VIEWS = True  # Convert intermediate tables to views

# ==============================================================================
# IMPORTS
# ==============================================================================
# API Style: dp
#
# DLT Style (backward compatible, still works):
#   from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
#   @dlt.table, @dlt.view
#
# DP/SDP Style (Apache Spark 4.1+ open standard - RECOMMENDED):
#   from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
#   @dp.table (persistent tables)
#   @dp.materialized_view (persistent views)
#   @dp.temporary_view (temporary views)
#
# Note: Databricks contributed SDP to Apache Spark as an open standard.
#       Lakeflow Pipelines (formerly Delta Live Tables) is built on SDP.
#       Both APIs work, but dp/SDP is recommended for forward compatibility.

from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
from pyspark.sql import functions as F
from pyspark.sql import types as T
from datetime import datetime

# ==============================================================================
# ORIGINAL SAS CODE (for reference)
# ==============================================================================
"""
/********************************************
* Sales Summary Report - FIXED FOR FULL ADVENTURE WORKS SCHEMA
*
* Purpose: Demonstrate external database integration
*          with data quality checks
*
* Source: Adventure Works (SQL Server) - FULL SCHEMA
*         - Sales.Customer (with AccountNumber, not CompanyName)
*         - Sales.SalesOrderHeader
*
* Output: Customer sales summary with metrics
*
* Author: 3Cloud SAS Migration Team
* Fixed:  Schema corrected to match actual Adventure Works database
********************************************/

/********************************************
* Step 1: Load Customers from Bronze
* (Bronze data ingested from SQL Server via Lakeflow Connect)
********************************************/
DATA work.customers;
    SET sas_tanderson_bronze.customer;

    /* Filter to active customers with account numbers */
    WHERE AccountNumber IS NOT NULL;

    /* Clean account number */
    AccountNumber = STRIP(AccountNumber);

    /* EXPECTATION: All customers should have valid IDs */
    /* EXPECT CustomerID > 0 */

    /* EXPECTATION: Account numbers should be populated after filter */
    /* EXPECT AccountNumber IS NOT NULL AND LENGTH(AccountNumber) > 0 */

    /* EXPECTATION: Territory should be assigned */
    /* EXPECT TerritoryID IS NOT NULL */
RUN;

/********************************************
* Step 2: Load Orders from Bronze
********************************************/
DATA work.orders;
    SET sas_tanderson_bronze.salesorderheader;

    /* Calculate days since order */
    days_since_order = TODAY() - OrderDate;

    /* Extract order year */
    order_year = YEAR(OrderDate);

    /* Flag recent orders (last 90 days) */
    IF days_since_order <= 90 THEN recent_order = 'Y';
    ELSE recent_order = 'N';

    /* EXPECTATION: Order IDs should be unique and positive */
    /* EXPECT SalesOrderID > 0 */

    /* EXPECTATION: Order dates should be reasonable (not in future) */
    /* EXPECT OrderDate <= TODAY() */

    /* EXPECTATION: Order year should be within business range (2010-present) */
    /* EXPECT order_year >= 2010 AND order_year <= YEAR(TODAY()) */

    /* EXPECTATION: Total Due should be positive */
    /* EXPECT TotalDue > 0 */

    /* EXPECTATION: Subtotal + Tax + Freight should equal Total */
    /* EXPECT ABS((SubTotal + TaxAmt + Freight) - TotalDue) < 0.01 */
RUN;

/********************************************
* Step 3: Calculate Customer Summary Metrics
********************************************/
PROC SQL;
    CREATE TABLE work.customer_metrics AS
    SELECT
        c.CustomerID,
        c.AccountNumber,
        c.TerritoryID,
        COUNT(o.SalesOrderID) as OrderCount,
        SUM(o.TotalDue) as TotalRevenue,
        AVG(o.TotalDue) as AvgOrderValue,
        MIN(o.OrderDate) as FirstOrderDate,
        MAX(o.OrderDate) as LastOrderDate
    FROM work.customers c
    LEFT JOIN work.orders o ON c.CustomerID = o.CustomerID
    GROUP BY c.CustomerID, c.AccountNumber, c.TerritoryID
    HAVING COUNT(o.SalesOrderID) > 0;

    /* EXPECTATION: All customers in result should have at least 1 order */
    /* EXPECT OrderCount > 0 */

    /* EXPECTATION: Total revenue should be positive */
    /* EXPECT TotalRevenue > 0 */

    /* EXPECTATION: Average order value should be reasonable (> $10) */
    /* EXPECT AvgOrderValue >= 10 */

    /* EXPECTATION: First order should be before or equal to last order */
    /* EXPECT FirstOrderDate <= LastOrderDate */

    /* EXPECTATION: Customer IDs should be unique (no duplicates) */
    /* EXPECT COUNT(DISTINCT CustomerID) = COUNT(*) */
QUIT;

/********************************************
* Step 4: Classify Customers by Value
********************************************/
DATA work.customer_classified;
    SET work.customer_metrics;

    /* Customer value tier */
    IF TotalRevenue >= 10000 THEN value_tier = 'High';
    ELSE IF TotalRevenue >= 5000 THEN value_tier = 'Medium';
    ELSE value_tier = 'Low';

    /* Calculate days since last order */
    days_since_last_order = TODAY() - LastOrderDate;

    /* Churn risk flag */
    IF days_since_last_order > 180 THEN churn_risk = 'High';
    ELSE IF days_since_last_order > 90 THEN churn_risk = 'Medium';
    ELSE churn_risk = 'Low';

    /* Customer lifetime (days) */
    customer_lifetime_days = LastOrderDate - FirstOrderDate;

    /* EXPECTATION: Value tier should be one of three categories */
    /* EXPECT value_tier IN ('High', 'Medium', 'Low') */

    /* EXPECTATION: Churn risk should be one of three categories */
    /* EXPECT churn_risk IN ('High', 'Medium', 'Low') */

    /* EXPECTATION: Days since last order should be non-negative */
    /* EXPECT days_since_last_order >= 0 */

    /* EXPECTATION: Customer lifetime should be non-negative */
    /* EXPECT customer_lifetime_days >= 0 */

    /* EXPECTATION: High value tier should match revenue threshold */
    /* EXPECT (value_tier = 'High' AND TotalRevenue >= 10000) OR value_tier != 'High' */
RUN;

/********************************************
* Step 5: Create Gold Summary Table
********************************************/
PROC SQL;
    CREATE TABLE sas_tanderson_gold.customer_summary AS
    SELECT
        CustomerID,
        AccountNumber,
        TerritoryID,
        OrderCount,
        TotalRevenue,
        AvgOrderValue,
        FirstOrderDate,
        LastOrderDate,
        value_tier,
        churn_risk,
        days_since_last_order,
        customer_lifetime_days
    FROM work.customer_classified
    ORDER BY TotalRevenue DESC;

    /* EXPECTATION: Gold table should have all required columns */
    /* EXPECT COUNT(*) > 0 */

    /* EXPECTATION: No NULL values in key business fields */
    /* EXPECT AccountNumber IS NOT NULL */
    /* EXPECT value_tier IS NOT NULL */
    /* EXPECT churn_risk IS NOT NULL */
QUIT;

/********************************************
* Step 6: Create Summary Statistics
********************************************/
PROC SQL;
    CREATE TABLE sas_tanderson_gold.sales_statistics AS
    SELECT
        value_tier,
        churn_risk,
        COUNT(*) as customer_count,
        SUM(TotalRevenue) as tier_revenue,
        AVG(TotalRevenue) as avg_customer_revenue,
        AVG(OrderCount) as avg_orders_per_customer
    FROM work.customer_classified
    GROUP BY value_tier, churn_risk
    ORDER BY value_tier, churn_risk;

    /* EXPECTATION: Should have 9 combinations (3 tiers x 3 risk levels) */
    /* EXPECT COUNT(*) <= 9 */

    /* EXPECTATION: Customer count should match detail table */
    /* EXPECT SUM(customer_count) = (SELECT COUNT(*) FROM work.customer_classified) */

    /* EXPECTATION: All aggregated values should be positive */
    /* EXPECT customer_count > 0 */
    /* EXPECT tier_revenue > 0 */
QUIT;

/* End of SAS program */

"""

# ==============================================================================
# CONVERTED PIPELINE CODE (from sas2databricks, enhanced with view optimization)
# ==============================================================================


# ==============================================================================
# POST-PROCESSING SUMMARY
# ==============================================================================
#
# Automatic fixes applied:
#   ✓ Normalized 3 table reference(s) (lib.table → lib_table)
# ==============================================================================

# Databricks notebook source
# Generated by sas2databricks -> target: Delta Live Tables
# Source: sales_summary_fixed.sas
from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
from pyspark.sql import functions as F

@dlt.expect_or_drop("valid_rows", 'AccountNumber IS NOT NULL')
@dp.table(name='sas_tanderson_silver.work_customers', comment='SAS data')
def work_customers():
    return spark.sql("""SELECT *,
  trim(AccountNumber) AS AccountNumber
FROM sas_tanderson_bronze.customer
WHERE AccountNumber IS NOT NULL""")

@dp.table(name='sas_tanderson_silver.work_orders', comment='SAS data')
def work_orders():
    return spark.sql("""SELECT *,
  CASE WHEN days_since_order <= 90 THEN 'Y' END AS recent_order,
  current_date() - OrderDate AS days_since_order,
  year(OrderDate) AS order_year
FROM sas_tanderson_bronze.salesorderheader""")

@dp.table(name='sas_tanderson_gold.work_customer_metrics', comment='SAS sql')
def work_customer_metrics():
    return spark.sql("""SELECT
  c.CustomerID,
  c.AccountNumber,
  c.TerritoryID,
  COUNT(o.SalesOrderID) AS OrderCount,
  SUM(o.TotalDue) AS TotalRevenue,
  AVG(o.TotalDue) AS AvgOrderValue,
  MIN(o.OrderDate) AS FirstOrderDate,
  MAX(o.OrderDate) AS LastOrderDate
FROM sas_tanderson_silver.work_customers AS c
LEFT JOIN sas_tanderson_silver.work_orders AS o
  ON c.CustomerID = o.CustomerID
GROUP BY
  c.CustomerID,
  c.AccountNumber,
  c.TerritoryID
HAVING
  COUNT(o.SalesOrderID) > 0""")

@dp.table(name='sas_tanderson_silver.work_customer_classified', comment='SAS data')
def work_customer_classified():
    return spark.sql("""SELECT *,
  CASE WHEN TotalRevenue >= 10000 THEN 'High' END AS value_tier,
  CASE WHEN TotalRevenue >= 5000 THEN 'Medium' END AS value_tier,
  CASE WHEN days_since_last_order > 180 THEN 'High' END AS churn_risk,
  CASE WHEN days_since_last_order > 90 THEN 'Medium' END AS churn_risk,
  current_date() - LastOrderDate AS days_since_last_order,
  LastOrderDate - FirstOrderDate AS customer_lifetime_days
FROM sas_tanderson_gold.work_customer_metrics""")

@dp.table(name='sas_tanderson_gold.sas_tanderson_gold_customer_summary', comment='SAS sql')
def sas_tanderson_gold_customer_summary():
    return spark.sql("""SELECT
  CustomerID,
  AccountNumber,
  TerritoryID,
  OrderCount,
  TotalRevenue,
  AvgOrderValue,
  FirstOrderDate,
  LastOrderDate,
  value_tier,
  churn_risk,
  days_since_last_order,
  customer_lifetime_days
FROM sas_tanderson_silver.work_customer_classified
ORDER BY
  TotalRevenue DESC""")

@dp.table(name='sas_tanderson_silver.sas_tanderson_gold_sales_statistics', comment='SAS sql')
def sas_tanderson_gold_sales_statistics():
    return spark.sql("""SELECT
  value_tier,
  churn_risk,
  COUNT(*) AS customer_count,
  SUM(TotalRevenue) AS tier_revenue,
  AVG(TotalRevenue) AS avg_customer_revenue,
  AVG(OrderCount) AS avg_orders_per_customer
FROM sas_tanderson_silver.work_customer_classified
GROUP BY
  value_tier,
  churn_risk
ORDER BY
  value_tier,
  churn_risk""")


# ==============================================================================
# HELPER: Add Bronze Metadata Columns
# ==============================================================================

def add_bronze_metadata(df, source_file="sales_summary_fixed.sas", layer="bronze"):
    """
    Adds standard metadata columns for audit trail

    Args:
        df: Input DataFrame
        source_file: Name of source SAS file
        layer: Medallion layer (bronze, silver, gold)

    Returns:
        DataFrame with metadata columns
    """
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
        .withColumn("medallion_layer", F.lit(layer))
    )

# ==============================================================================
# LAYER-SPECIFIC SCHEMAS
# ==============================================================================

def get_schema_for_layer(layer):
    """Returns appropriate schema based on medallion layer"""
    if layer == "bronze":
        return SCHEMA_BRONZE
    elif layer == "gold":
        return SCHEMA_GOLD
    else:
        return SCHEMA_SILVER

# ==============================================================================
# ENHANCED TABLES/VIEWS (with layer-specific schemas and metadata)
# ==============================================================================

# TODO: Review the tables above and enhance with:
# 1. Correct schema based on detected layer
# 2. Bronze metadata for audit trail
# 3. Data quality expectations
#
# Example pattern:
#
# @dlt.view(  # Changed from table to view for intermediate processing
#     name="silver_intermediate_claims",
#     comment="Intermediate transformation - Silver layer"
# )
# def silver_intermediate_claims():
#     df = spark.table("LIVE.bronze_claims")
#     # Add transformation logic
#     return df.filter(F.col("status") == "active")
#
# @dlt.table(
#     name="gold_claims_summary",
#     comment="Final aggregated metrics - Gold layer",
#     schema=f"`{CATALOG}`.{SCHEMA_GOLD}"  # Write to Gold schema
# )
# @dlt.expect_or_drop("valid_count", "claim_count > 0")
# def gold_claims_summary():
#     df = spark.table("LIVE.silver_intermediate_claims")
#     result = df.groupBy("region").agg(
#         F.count("*").alias("claim_count"),
#         F.sum("amount").alias("total_amount")
#     )
#     return add_bronze_metadata(result, layer="gold")

# ==============================================================================
# DETECTED TABLE ANALYSIS
# ==============================================================================
"""
Intelligent layer detection results:

Table Name                     | Layer  | Schema               | Type
---------------------------------------------------------------------------
work_customers                 | silver | sas_tanderson_silver | TABLE
work_orders                    | silver | sas_tanderson_silver | TABLE
work_customer_metrics          | gold   | sas_tanderson_gold   | TABLE
work_customer_classified       | silver | sas_tanderson_silver | TABLE
sas_tanderson_gold_customer_summary | gold   | sas_tanderson_gold   | TABLE
sas_tanderson_gold_sales_statistics | silver | sas_tanderson_silver | TABLE

Recommendations:
- Bronze tables: Add bronze_metadata for audit trail
- Silver tables: Add data quality expectations
- Gold tables: Verify aggregation logic matches SAS
- Views: Use for intermediate transformations (no persistence)

# ==============================================================================
# DATA QUALITY EXPECTATIONS
# ==============================================================================

# Add expectations based on SAS validation rules
# Example patterns by layer:
#
# Bronze (data quality at ingestion):
# @dlt.expect_or_drop("valid_dates", "date_col >= '2020-01-01'")
# @dlt.expect_or_drop("no_nulls_in_key", "key_col IS NOT NULL")
#
# Silver (business rule validation):
# @dlt.expect_or_warn("valid_status", "status IN ('active', 'pending', 'closed')")
# @dlt.expect_or_drop("positive_amounts", "amount > 0")
#
# Gold (aggregation validation):
# @dlt.expect("min_record_count", "count > 0")
# @dlt.expect("valid_totals", "total_amount >= 0")

# ==============================================================================
# END OF CONVERTED PIPELINE
# ==============================================================================
#
# Deployment checklist:
# □ Review layer assignments (Bronze/Silver/Gold)
# □ Verify schema configuration for each layer
# □ Update view vs table decisions
# □ Add bronze metadata to appropriate tables
# □ Test with sample data
# □ Validate output matches SAS results
# □ Update widgets for prod deployment
# □ Deploy via DAB or pipeline UI
#
# ==============================================================================
"""
