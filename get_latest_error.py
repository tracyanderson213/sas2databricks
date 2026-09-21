#!/usr/bin/env python3
"""Get the latest pipeline error"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

pipeline_id = "61479b4f-b380-480b-a063-97c187e4d515"

print("=" * 80)
print("🔍 Getting Latest Pipeline Error")
print("=" * 80)
print()

# Get pipeline details
pipeline = w.pipelines.get(pipeline_id=pipeline_id)
print(f"Pipeline: {pipeline.name}")
print(f"State: {pipeline.state}")
print()

# Get latest update
response = w.pipelines.list_updates(pipeline_id=pipeline_id, max_results=1)

if hasattr(response, 'updates') and response.updates:
    latest = response.updates[0]
    print(f"Latest Update ID: {latest.update_id}")
    print(f"State: {latest.state}")
    print()

    if latest.state and str(latest.state) == "UpdateInfoState.FAILED":
        print("❌ PIPELINE FAILED")
        print()

        # Get full details
        full = w.pipelines.get_update(pipeline_id=pipeline_id, update_id=latest.update_id)

        if hasattr(full, 'cause') and full.cause:
            print("Error Cause:")
            print(full.cause)

        print()
        print("View in UI:")
        print(f"https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{pipeline_id}/updates/{latest.update_id}")
else:
    print("No updates found")

print()
print("=" * 80)
