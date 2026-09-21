#!/usr/bin/env python3
"""
Get detailed error from latest pipeline run
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

pipeline_name = "sas_dbx_TEMPLATE_tanderson_pipeline"

print("="*80)
print(f"🔍 Getting Error Details: {pipeline_name}")
print("="*80)
print()

# Find pipeline
pipelines = list(w.pipelines.list_pipelines())
target = None
for p in pipelines:
    if p.name == pipeline_name:
        target = p
        break

if not target:
    print(f"❌ Pipeline not found: {pipeline_name}")
    exit(1)

pipeline_id = target.pipeline_id
print(f"Pipeline ID: {pipeline_id}")
print()

# Get updates
print("📊 Recent Runs:")
print()

try:
    # Get list of updates
    response = w.pipelines.list_updates(pipeline_id=pipeline_id, max_results=3)

    # Access updates from response
    if hasattr(response, 'updates') and response.updates:
        updates = response.updates

        for i, update in enumerate(updates[:3], 1):
            print(f"{i}. Update ID: {update.update_id}")
            if update.state:
                print(f"   State: {update.state}")

            if update.state and str(update.state) == "UpdateInfoState.FAILED":
                print()
                print("=" * 80)
                print("❌ FAILED RUN DETAILS")
                print("=" * 80)

                # Get full details
                full = w.pipelines.get_update(
                    pipeline_id=pipeline_id,
                    update_id=update.update_id
                )

                if full.cause:
                    print(f"\nCause: {full.cause}")

                print()
                print("View in UI:")
                print(f"https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{pipeline_id}/updates/{update.update_id}")
                print()
                break
            print()
    else:
        print("No updates found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("="*80)
