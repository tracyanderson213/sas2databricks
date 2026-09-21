#!/usr/bin/env python3
"""
Create a test pipeline using the fixed converter output
"""
import os
import json
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import PipelineLibrary, NotebookLibrary

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

print("=" * 80)
print("🔬 Create Test Pipeline from Converter Output")
print("=" * 80)
print()

# Configuration
pipeline_name = "sas_dbx_TEST_tanderson_pipeline"
catalog = "na-dbxtraining"
developer_id = "tanderson"

# Upload the fixed file
source_file = "/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/transformations/transformed_claims_adjudication_FIXED.py"
target_path = f"/Workspace/Users/57755c23-5f4c-45ac-b2a2-118523d0c1b5/sas2databricks/test_pipelines/transformed_claims_adjudication.py"

print(f"📤 Uploading fixed transformation file...")
print(f"   Source: {source_file}")
print(f"   Target: {target_path}")
print()

try:
    with open(source_file, 'r') as f:
        content = f.read()

    w.workspace.mkdirs(os.path.dirname(target_path))
    w.workspace.upload(target_path, content.encode('utf-8'), overwrite=True, format='SOURCE')
    print("✅ File uploaded successfully")
    print()
except Exception as e:
    print(f"❌ Upload failed: {e}")
    exit(1)

# Create the pipeline
print(f"🔧 Creating pipeline: {pipeline_name}")
print()

try:
    # Check if pipeline already exists
    existing = None
    for p in w.pipelines.list_pipelines():
        if p.name == pipeline_name:
            existing = p
            break

    if existing:
        print(f"⚠️  Pipeline already exists: {pipeline_name}")
        print(f"   ID: {existing.pipeline_id}")
        print()
        print("Options:")
        print("  1. Delete and recreate (run: databricks pipelines delete {id})")
        print("  2. Update the existing pipeline manually in the UI")
        print()
    else:
        # Create new pipeline
        response = w.pipelines.create(
            name=pipeline_name,
            catalog=catalog,
            target=f"sas_{developer_id}_bronze",
            libraries=[
                PipelineLibrary(
                    notebook=NotebookLibrary(path=target_path)
                )
            ],
            clusters=[{
                "label": "default",
                "num_workers": 1
            }],
            development=True,
            continuous=False,
            channel="CURRENT"
        )

        print(f"✅ Pipeline created successfully!")
        print()
        print(f"Pipeline ID: {response.pipeline_id}")
        print(f"Pipeline URL: https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{response.pipeline_id}")
        print()
        print("=" * 80)
        print("🎯 Next Steps:")
        print("=" * 80)
        print()
        print("1. Open the pipeline in the UI")
        print("2. Click 'Start' to run the test")
        print("3. Validate output in:")
        print(f"   • {catalog}.sas_{developer_id}_bronze.*")
        print(f"   • {catalog}.sas_{developer_id}_silver.*")
        print(f"   • {catalog}.sas_{developer_id}_gold.*")
        print()

except Exception as e:
    print(f"❌ Pipeline creation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
