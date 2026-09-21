#!/usr/bin/env python3
"""
Cleanup old schemas before redeploying with developer-prefixed names
"""
import os
from databricks.sdk import WorkspaceClient

# Use PAT auth
os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

print("="*80)
print("🗑️  Cleaning Up Old Schemas")
print("="*80)
print()

w = WorkspaceClient()

warehouse_id = "2f51df324d05e45d"
catalog = "na-dbxtraining"

schemas_to_drop = [
    "sas_bronze",
    "sas_silver",
    "sas_gold"
]

for schema in schemas_to_drop:
    print(f"Dropping schema: {catalog}.{schema}")
    try:
        sql = f"DROP SCHEMA IF EXISTS `{catalog}`.{schema} CASCADE"
        result = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=sql,
            wait_timeout="30s"
        )
        print(f"   ✅ Dropped: {schema}")
    except Exception as e:
        print(f"   ⚠️  Error dropping {schema}: {e}")
    print()

print("="*80)
print("✅ Cleanup Complete")
print("="*80)
print()
print("Next step: Redeploy bundle with developer_id=tanderson")
