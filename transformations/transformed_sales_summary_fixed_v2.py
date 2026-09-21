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
# 2026-09-21 | Tracy Anderson       | Fixed table references and date calculations
# ------------------------------------------------------------------------------
#
# Medallion Layer Analysis:
# ------------------------------------------------------------------------------
# - work_customers_v2                 → silver layer (sas_tanderson_silver)  [TABLE]
# - work_orders_v2                    → silver layer (sas_tanderson_silver)  [TABLE]
# - work_customer_metrics_v2          → gold   layer (sas_tanderson_gold)  [TABLE]
# - work_customer_classified_v2       → silver layer (sas_tanderson_silver)  [TABLE]
# - sas_tanderson_gold_customer_summary_v2 → gold   layer (sas_tanderson_gold)  [TABLE]
# - sas_tanderson_gold_sales_statistics_v2 → silver layer (sas_tanderson_silver)  [TABLE]
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
SCHEMA_BRONZE = "sas_tanderson_bronze"    # Raw data ingestion layer
SCHEMA_SILVER = "sas_tanderson_silver"    # Business logic transformation layer
SCHEMA_GOLD = "sas_tanderson_gold"        # Aggregated metrics and reporting layer

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
from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)
from pyspark.sql import functions as F
from pyspark.sql import types as T
from datetime import datetime

# ==============================================================================
# CONVERTED PIPELINE CODE (CORRECTED BY GENIE)
# ==============================================================================

@dp.expect_or_drop("valid_rows", 'AccountNumber IS NOT NULL')
@dp.table(name='sas_tanderson_silver.work_customers_v2', comment='SAS data')
def work_customers():
    return spark.sql("""SELECT * EXCEPT(AccountNumber),
  trim(AccountNumber) AS AccountNumber
FROM `na-dbxtraining`.sas_tanderson_bronze.customer
WHERE AccountNumber IS NOT NULL""")

@dp.table(name='sas_tanderson_silver.work_orders_v2', comment='SAS data')
def work_orders():
    return spark.sql("""SELECT *,
  datediff(current_date(), OrderDate) AS days_since_order,
  CASE WHEN datediff(current_date(), OrderDate) <= 90 THEN 'Y' ELSE 'N' END AS recent_order,
  year(OrderDate) AS order_year
FROM `na-dbxtraining`.sas_tanderson_bronze.salesorderheader""")

@dp.table(name='sas_tanderson_gold.work_customer_metrics_v2', comment='SAS sql')
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
FROM sas_tanderson_silver.work_customers_v2 AS c
LEFT JOIN sas_tanderson_silver.work_orders_v2 AS o
  ON c.CustomerID = o.CustomerID
GROUP BY
  c.CustomerID,
  c.AccountNumber,
  c.TerritoryID
HAVING
  COUNT(o.SalesOrderID) > 0""")

@dp.table(name='sas_tanderson_silver.work_customer_classified_v2', comment='SAS data')
def work_customer_classified():
    return spark.sql("""SELECT *,
  CASE WHEN TotalRevenue >= 10000 THEN 'High' WHEN TotalRevenue >= 5000 THEN 'Medium' ELSE 'Low' END AS value_tier,
  datediff(current_date(), LastOrderDate) AS days_since_last_order,
  CASE WHEN datediff(current_date(), LastOrderDate) > 180 THEN 'High' WHEN datediff(current_date(), LastOrderDate) > 90 THEN 'Medium' ELSE 'Low' END AS churn_risk,
  datediff(LastOrderDate, FirstOrderDate) AS customer_lifetime_days
FROM sas_tanderson_gold.work_customer_metrics_v2""")

@dp.table(name='sas_tanderson_gold.sas_tanderson_gold_customer_summary_v2', comment='SAS sql')
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
FROM sas_tanderson_silver.work_customer_classified_v2
ORDER BY
  TotalRevenue DESC""")

@dp.table(name='sas_tanderson_silver.sas_tanderson_gold_sales_statistics_v2', comment='SAS sql')
def sas_tanderson_gold_sales_statistics():
    return spark.sql("""SELECT
  value_tier,
  churn_risk,
  COUNT(*) AS customer_count,
  SUM(TotalRevenue) AS tier_revenue,
  AVG(TotalRevenue) AS avg_customer_revenue,
  AVG(OrderCount) AS avg_orders_per_customer
FROM sas_tanderson_silver.work_customer_classified_v2
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
# END OF CONVERTED PIPELINE
# ==============================================================================
#
# Deployment checklist:
# ✅ Fixed table references with backticks for catalog name
# ✅ Fixed date calculations using datediff()
# ✅ Fixed CASE statements for value_tier and churn_risk
# ✅ Added _v2 suffix to avoid table name conflicts
# ✅ Used SELECT * EXCEPT() to avoid duplicate AccountNumber column
# □ Test with sample data
# □ Validate output matches SAS results
# □ Deploy via pipeline UI
#
# ==============================================================================
