#!/usr/bin/env python3
"""
Check converted files in the volume
"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

volume_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"
converted_dir = f"{volume_base}/converted"

print("="*80)
print("📁 Transformed Pipeline Files")
print("="*80)
print()

try:
    files = w.files.list_directory_contents(converted_dir)

    py_files = []
    yml_files = []

    for file in files:
        if file.name.endswith('.py'):
            py_files.append(file)
        elif file.name.endswith('.yml'):
            yml_files.append(file)

    if py_files:
        print("✅ Python Files (Transformation Pipelines):")
        for f in py_files:
            size_kb = f.file_size / 1024 if f.file_size else 0
            print(f"   • {f.name} ({size_kb:.1f} KB)")
        print()

    if yml_files:
        print("✅ Pipeline YAMLs:")
        for f in yml_files:
            print(f"   • {f.name}")
        print()

    print(f"Total: {len(py_files)} Python files, {len(yml_files)} YAML files")
    print()
    print("="*80)
    print("Next Steps:")
    print("="*80)
    print()
    print(f"1. View transformed Python:")
    print(f"   • Navigate to: Catalog → na-dbxtraining → sas2dbx_migrate → sas_migration → converted")
    print()
    print(f"2. Create pipeline in UI:")
    print(f"   • Workflows → Delta Live Tables → Create pipeline")
    print(f"   • Add notebook: {converted_dir}/transformed_claims_adjudication.py")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("The converted/ folder may be empty or not accessible.")
