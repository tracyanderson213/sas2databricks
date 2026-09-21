#!/usr/bin/env python3
"""
Check which schemas exist
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()
catalog = "na-dbxtraining"

print("="*80)
print(f"📋 Schemas in {catalog}")
print("="*80)
print()

schemas = list(w.schemas.list(catalog_name=catalog))
sas_schemas = [s for s in schemas if s.name.startswith('sas')]

for schema in sorted(sas_schemas, key=lambda s: s.name):
    print(f"✅ {schema.name}")

print()
print(f"Total SAS schemas: {len(sas_schemas)}")
print("="*80)
