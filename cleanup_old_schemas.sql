-- ============================================================
-- Cleanup Old Schemas (Simple Names)
-- ============================================================
-- Run this in Databricks SQL Editor to delete old schemas
-- before redeploying with developer-prefixed names
-- ============================================================

-- Check what exists first
SHOW SCHEMAS IN `na-dbxtraining` LIKE 'sas_%';

-- ============================================================
-- WARNING: This will DELETE all data in these schemas!
-- ============================================================

-- Drop old schemas (simple names without developer prefix)
DROP SCHEMA IF EXISTS `na-dbxtraining`.sas_bronze CASCADE;
DROP SCHEMA IF EXISTS `na-dbxtraining`.sas_silver CASCADE;
DROP SCHEMA IF EXISTS `na-dbxtraining`.sas_gold CASCADE;

-- Note: We keep sas2dbx_migrate schema (shared across developers)
-- DROP SCHEMA IF EXISTS `na-dbxtraining`.sas2dbx_migrate CASCADE;  -- DON'T DELETE THIS

-- Verify cleanup
SHOW SCHEMAS IN `na-dbxtraining` LIKE 'sas_%';

-- ============================================================
-- After running this, redeploy the bundle:
--   DATABRICKS_CONFIG_FILE=.databrickscfg.bundle \
--   databricks bundle deploy -t dev --var developer_id=tanderson
-- ============================================================
