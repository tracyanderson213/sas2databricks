#!/usr/bin/env python3
"""
Update a pipeline's transformation file from converter output

Usage:
    python update_pipeline_file.py <pipeline_name> <converted_filename>

Examples:
    python update_pipeline_file.py claims_adjudication transformed_claims_adjudication.py
    python update_pipeline_file.py customer_analysis transformed_customer_analysis.py
"""
import os
import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

# Configuration
os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

CATALOG = "na-dbxtraining"
VOLUME_PATH = f"/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration/converted"
WORKSPACE_BASE = "/Workspace/Users/57755c23-5f4c-45ac-b2a2-118523d0c1b5/sas2databricks/pipelines"

# Parse arguments
if len(sys.argv) < 3:
    print("Error: Missing arguments")
    print()
    print("Usage: python update_pipeline_file.py <pipeline_name> <converted_filename>")
    print()
    print("Example:")
    print("  python update_pipeline_file.py claims_adjudication transformed_claims_adjudication.py")
    print()
    print("Tip: Run 'python list_converted_files.py' to see available files")
    sys.exit(1)

pipeline_name = sys.argv[1]
source_filename = sys.argv[2]

# Ensure .py extension
if not source_filename.endswith('.py'):
    source_filename = f"{source_filename}.py"

print("=" * 80)
print("🔄 Update Pipeline Transformation File")
print("=" * 80)
print()
print(f"Pipeline:      {pipeline_name}")
print(f"Source File:   {source_filename}")
print()

# Step 1: Download from volume
volume_file = f"{VOLUME_PATH}/{source_filename}"
print(f"📥 Downloading from volume...")
print(f"   {volume_file}")

try:
    response = w.files.download(volume_file)
    content = response.contents.read().decode('utf-8')
    print(f"   ✅ Downloaded ({len(content)} bytes)")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print()
    print("Available files:")
    try:
        files = w.files.list_directory_contents(VOLUME_PATH)
        for f in files:
            if f.name.endswith('.py'):
                print(f"  • {f.name}")
    except:
        pass
    sys.exit(1)

print()

# Step 2: Upload to workspace
workspace_file = f"{WORKSPACE_BASE}/{pipeline_name}/my_transformations.py"
print(f"📤 Uploading to workspace...")
print(f"   {workspace_file}")

try:
    # Create directory if needed
    w.workspace.mkdirs(f"{WORKSPACE_BASE}/{pipeline_name}")

    # Upload file
    w.workspace.upload(workspace_file, content.encode('utf-8'), overwrite=True, format=ImportFormat.SOURCE)
    print(f"   ✅ Uploaded successfully")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()
print("=" * 80)
print("✅ Pipeline File Updated!")
print("=" * 80)
print()
print("🎯 Next Steps:")
print(f"   1. Open pipeline in UI: sas_dbx_{pipeline_name}_pipeline")
print(f"   2. Click 'Start' to run with updated transformation")
print(f"   3. Validate output in schemas")
print()
