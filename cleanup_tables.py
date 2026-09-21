#!/usr/bin/env python3
"""
Drop all tables from the schemas to allow new pipeline to take ownership
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

print("=" * 80)
print("🧹 Cleanup Tables Before Pipeline Run")
print("=" * 80)
print()

catalog = "na-dbxtraining"
schemas = ["sas_tanderson_bronze", "sas_tanderson_silver", "sas_tanderson_gold"]

total_dropped = 0

for schema in schemas:
    print(f"📂 Cleaning schema: {catalog}.{schema}")

    try:
        tables = list(w.tables.list(catalog_name=catalog, schema_name=schema))

        if not tables:
            print(f"   ✓ No tables found")
        else:
            for table in tables:
                full_name = f"{catalog}.{schema}.{table.name}"
                print(f"   🗑️  Dropping: {table.name}")
                try:
                    w.tables.delete(full_name)
                    total_dropped += 1
                except Exception as e:
                    print(f"      ⚠️  Warning: {e}")

    except Exception as e:
        print(f"   ⚠️  Error listing tables: {e}")

    print()

print("=" * 80)
print(f"✅ Cleanup Complete! Dropped {total_dropped} tables")
print("=" * 80)
print()
print("🎯 Next Steps:")
print("   1. Run your pipeline: sas_dbx_claims_adjudication_pipeline")
print("   2. It will create all tables with new ownership")
print()
