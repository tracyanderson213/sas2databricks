#!/usr/bin/env python3
"""
Create sas_dbx_claims_adjudication_pipeline from fixed converter output
"""
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import PipelineLibrary, NotebookLibrary, PipelineCluster
from databricks.sdk.service.workspace import ImportFormat

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

print("=" * 80)
print("🚀 Create Claims Adjudication Pipeline")
print("=" * 80)
print()

# Configuration
pipeline_name = "sas_dbx_claims_adjudication_pipeline"
catalog = "na-dbxtraining"
target_schema = "sas_tanderson_bronze"

# Upload the fixed file
source_file = "/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/transformations/transformed_claims_adjudication_FIXED.py"
target_path = f"/Workspace/Users/57755c23-5f4c-45ac-b2a2-118523d0c1b5/sas2databricks/pipelines/claims_adjudication.py"

print(f"📤 Uploading transformation file...")
print(f"   Source: transformed_claims_adjudication_FIXED.py")
print(f"   Target: {target_path}")
print()

try:
    with open(source_file, 'r') as f:
        content = f.read()

    w.workspace.mkdirs(os.path.dirname(target_path))
    w.workspace.upload(target_path, content.encode('utf-8'), overwrite=True, format=ImportFormat.SOURCE)
    print("✅ File uploaded successfully")
    print()
except Exception as e:
    print(f"❌ Upload failed: {e}")
    exit(1)

# Check if pipeline already exists
print(f"🔍 Checking for existing pipeline: {pipeline_name}")
existing = None
for p in w.pipelines.list_pipelines():
    if p.name == pipeline_name:
        existing = p
        break

if existing:
    print(f"⚠️  Pipeline already exists!")
    print(f"   Name: {existing.name}")
    print(f"   ID: {existing.pipeline_id}")
    print(f"   URL: https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{existing.pipeline_id}")
    print()
    print("✅ File has been updated. Run the pipeline in the UI to use the new version.")
    print()
else:
    # Create new pipeline
    print(f"🔧 Creating new pipeline...")
    print()

    try:
        response = w.pipelines.create(
            name=pipeline_name,
            catalog=catalog,
            target=target_schema,
            libraries=[
                PipelineLibrary(
                    notebook=NotebookLibrary(path=target_path)
                )
            ],
            clusters=[
                PipelineCluster(
                    label="default",
                    num_workers=1
                )
            ],
            development=True,
            continuous=False,
            channel="CURRENT"
        )

        print(f"✅ Pipeline created successfully!")
        print()
        print(f"📋 Pipeline Details:")
        print(f"   Name: {pipeline_name}")
        print(f"   ID: {response.pipeline_id}")
        print(f"   URL: https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{response.pipeline_id}")
        print()

    except Exception as e:
        print(f"❌ Pipeline creation failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

print("=" * 80)
print("🎯 Next Steps:")
print("=" * 80)
print()
print("1. Open the pipeline in Databricks UI:")
print(f"   Workflows → Delta Live Tables → {pipeline_name}")
print()
print("2. Click 'Start' to run the transformation")
print()
print("3. Expected output:")
print(f"   • Bronze: 4 tables in {catalog}.sas_tanderson_bronze")
print(f"   • Silver: 6 views in {catalog}.sas_tanderson_silver")
print(f"   • Gold: 2 tables in {catalog}.sas_tanderson_gold")
print()
print("=" * 80)
