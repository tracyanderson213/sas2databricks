#!/usr/bin/env python3
"""
Promote a tested transformation from template to production pipeline

This script:
1. Copies current_transformation.py to a named file
2. Adds a pipeline entry to databricks.yml (shows you the config to add)
3. Guides you through deployment

Usage:
    python promote_to_production.py <pipeline_name>

Example:
    python promote_to_production.py claims_adjudication
"""
import os
import sys
import shutil

if len(sys.argv) < 2:
    print("Usage: python promote_to_production.py <pipeline_name>")
    print()
    print("Example:")
    print("  python promote_to_production.py claims_adjudication")
    print()
    print("This creates:")
    print("  • transformations/claims_adjudication.py")
    print("  • Pipeline config to add to databricks.yml")
    sys.exit(1)

pipeline_name = sys.argv[1]
transformation_filename = f"{pipeline_name}.py"

print("="*80)
print("🚀 Promote Transformation to Production")
print("="*80)
print()

# Paths
source = "/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/transformations/current_transformation.py"
target = f"/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/transformations/{transformation_filename}"

# Copy file
print(f"📄 Copying transformation file...")
print(f"   From: current_transformation.py")
print(f"   To:   {transformation_filename}")

if os.path.exists(target):
    print()
    print(f"⚠️  File already exists: {transformation_filename}")
    response = input("Overwrite? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)

shutil.copy(source, target)
print(f"✅ Created: {target}")
print()

# Generate pipeline YAML config
yaml_config = f"""
  # Production pipeline for {pipeline_name}
  {pipeline_name}_pipeline:
    name: "{pipeline_name}_${{var.developer_id}}_pipeline"
    catalog: ${{var.catalog}}
    target: default

    configuration:
      catalog: ${{var.catalog}}
      schema_bronze: ${{resources.schemas.sas_bronze.name}}
      schema_silver: ${{resources.schemas.sas_silver.name}}
      schema_gold: ${{resources.schemas.sas_gold.name}}
      enable_views: "true"

    libraries:
      - file:
          path: ./transformations/{transformation_filename}

    serverless: true
    photon: true
    continuous: false
    development: false

    tags:
      project: "sas_migration"
      developer_id: ${{var.developer_id}}
      organization: "3cloud"
      pipeline_type: "production"
"""

print("="*80)
print("📋 Pipeline Configuration")
print("="*80)
print()
print("Add this to databricks.yml under 'resources.pipelines:'")
print()
print(yaml_config)
print()

print("="*80)
print("✅ Next Steps")
print("="*80)
print()
print("1. Edit databricks.yml:")
print("   • Add the pipeline configuration above")
print()
print("2. Deploy bundle:")
print("   DATABRICKS_CONFIG_FILE=.databrickscfg.bundle \\")
print("   databricks bundle deploy -t dev --var developer_id=tanderson")
print()
print("3. Start pipeline in UI:")
print(f"   • Find: {pipeline_name}_tanderson_pipeline")
print("   • Click 'Start'")
print()
