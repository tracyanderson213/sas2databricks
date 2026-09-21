#!/usr/bin/env python3
"""
Check pipeline status and recent run failures
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

pipeline_name = "sas_dbx_TEMPLATE_tanderson_pipeline"

print("="*80)
print(f"🔍 Checking Pipeline: {pipeline_name}")
print("="*80)
print()

# Find pipeline
pipelines = list(w.pipelines.list_pipelines())
target_pipeline = None
for p in pipelines:
    if p.name == pipeline_name:
        target_pipeline = p
        break

if not target_pipeline:
    print(f"❌ Pipeline not found: {pipeline_name}")
    print()
    print("Available pipelines:")
    for p in pipelines:
        print(f"  • {p.name}")
    exit(1)

pipeline_id = target_pipeline.pipeline_id
print(f"Pipeline ID: {pipeline_id}")
print()

# Get latest update
print("📊 Latest Status:")
try:
    updates = list(w.pipelines.list_updates(pipeline_id=pipeline_id, max_results=5))

    if not updates:
        print("  No runs found")
    else:
        latest = updates[0]
        print(f"  State: {latest.state}")
        print(f"  Update ID: {latest.update_id}")

        if latest.state and latest.state.name == "FAILED":
            print()
            print("❌ PIPELINE FAILED")
            print()
            print("Getting error details...")

            # Get full update details
            full_update = w.pipelines.get_update(pipeline_id=pipeline_id, update_id=latest.update_id)

            if full_update.cause:
                print(f"Cause: {full_update.cause}")

            print()
            print("View full logs in UI:")
            print(f"https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{pipeline_id}/updates/{latest.update_id}")
            print()

        elif latest.state and latest.state.name == "COMPLETED":
            print()
            print("✅ Pipeline completed successfully!")

except Exception as e:
    print(f"Error getting updates: {e}")

print()
print("="*80)
