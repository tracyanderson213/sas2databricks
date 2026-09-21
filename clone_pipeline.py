#!/usr/bin/env python3
"""
Clone an existing Databricks pipeline via CLI

Usage:
    python clone_pipeline.py <source_pipeline_name> <new_pipeline_name>
"""
import os
import sys
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

if len(sys.argv) < 3:
    print("Usage: python clone_pipeline.py <source_name> <new_name>")
    print()
    print("Example:")
    print("  python clone_pipeline.py sas_dbx_TEMPLATE_tanderson_pipeline claims_prod_pipeline")
    sys.exit(1)

source_name = sys.argv[1]
new_name = sys.argv[2]

print("="*80)
print("🔄 Cloning Pipeline")
print("="*80)
print()

w = WorkspaceClient()

# Find source pipeline
print(f"🔍 Finding source pipeline: {source_name}")
pipelines = list(w.pipelines.list_pipelines())
source = None
for p in pipelines:
    if p.name == source_name:
        source = p
        break

if not source:
    print(f"❌ Source pipeline not found: {source_name}")
    print()
    print("Available pipelines:")
    for p in pipelines:
        print(f"  • {p.name}")
    sys.exit(1)

print(f"✅ Found: {source.pipeline_id}")
print()

# Get full config
print("📋 Reading configuration...")
config = w.pipelines.get(source.pipeline_id)

# Create new pipeline with modified config
print(f"🆕 Creating clone: {new_name}")
print()

new_pipeline = w.pipelines.create(
    name=new_name,
    catalog=config.spec.catalog,
    target=config.spec.target,
    continuous=config.spec.continuous,
    development=config.spec.development,
    photon=config.spec.photon,
    serverless=config.spec.serverless,
    libraries=config.spec.libraries,
    configuration=config.spec.configuration,
    clusters=config.spec.clusters
)

print("="*80)
print("✅ Pipeline Cloned Successfully")
print("="*80)
print()
print(f"Source:  {source_name}")
print(f"Clone:   {new_name}")
print(f"ID:      {new_pipeline.pipeline_id}")
print()
print(f"View in UI:")
print(f"https://adb-1952652121322753.13.azuredatabricks.net/pipelines/{new_pipeline.pipeline_id}")
print()
