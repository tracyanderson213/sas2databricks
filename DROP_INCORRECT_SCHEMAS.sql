-- ============================================================================
-- DROP INCORRECT SCHEMAS
-- ============================================================================
-- Purpose: Remove schemas created with wrong naming pattern
-- Pattern: sas_dbx_tracy_anderson_* (incorrect)
-- Should be: sas_tanderson_* (correct)
--
-- INSTRUCTIONS:
-- 1. Open Databricks SQL Editor
-- 2. Select warehouse: SQL Warehouse (ID: 2f51df324d05e45d)
-- 3. Copy/paste commands below
-- 4. Run each command (or run all at once)
--
-- ============================================================================

-- Drop Gold first (in case Silver/Bronze have dependencies)
DROP SCHEMA IF EXISTS `na-dbxtraining`.`sas_dbx_tracy_anderson_gold` CASCADE;

-- Drop Silver
DROP SCHEMA IF EXISTS `na-dbxtraining`.`sas_dbx_tracy_anderson_silver` CASCADE;

-- Drop Bronze
DROP SCHEMA IF EXISTS `na-dbxtraining`.`sas_dbx_tracy_anderson_bronze` CASCADE;

-- ============================================================================
-- VERIFY: Check they're gone
-- ============================================================================

SHOW SCHEMAS IN `na-dbxtraining` LIKE 'sas_dbx_tracy_anderson%';
-- Should return: Empty result set

-- ============================================================================
-- VERIFY: Check correct schemas exist
-- ============================================================================

SHOW SCHEMAS IN `na-dbxtraining` LIKE 'sas_tanderson%';
-- Should return: sas_tanderson_bronze, sas_tanderson_silver, sas_tanderson_gold

-- ============================================================================
-- OPTIONAL: Check what's in the correct schemas
-- ============================================================================

-- Bronze tables (should have 4 tables)
SHOW TABLES IN `na-dbxtraining`.`sas_tanderson_bronze`;

-- Silver views (should have ~6 views)
SHOW TABLES IN `na-dbxtraining`.`sas_tanderson_silver`;

-- Gold tables (should have 2 tables)
SHOW TABLES IN `na-dbxtraining`.`sas_tanderson_gold`;
