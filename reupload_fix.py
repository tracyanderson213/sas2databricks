#!/usr/bin/env python3
"""Re-upload fixed file to workspace"""
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

source_file = "transformations/transformed_claims_adjudication_FIXED.py"
target_path = "/Workspace/Users/57755c23-5f4c-45ac-b2a2-118523d0c1b5/sas2databricks/pipelines/claims_adjudication.py"

print("📤 Re-uploading fixed file...")
print(f"   Source: {source_file}")
print(f"   Target: {target_path}")
print()

with open(source_file, 'r') as f:
    content = f.read()

w.workspace.upload(target_path, content.encode('utf-8'), overwrite=True, format=ImportFormat.SOURCE)

print("✅ File re-uploaded successfully!")
print()
print("🔄 Restart the pipeline to use the fixed version:")
print("   1. Stop the current run (if still running)")
print("   2. Click 'Start' again")
