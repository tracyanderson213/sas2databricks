#!/usr/bin/env python3
"""
List all converted files available in the volume
"""
import os
from databricks.sdk import WorkspaceClient
from datetime import datetime

os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'
w = WorkspaceClient()

CATALOG = "na-dbxtraining"
VOLUME_PATH = f"/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration/converted"

print("=" * 80)
print("📂 Converted Files Available")
print("=" * 80)
print()
print(f"Location: {VOLUME_PATH}")
print()

try:
    files = list(w.files.list_directory_contents(VOLUME_PATH))

    # Filter to .py files only
    py_files = [f for f in files if f.name.endswith('.py')]

    if not py_files:
        print("⚠️  No converted files found")
        print()
        print("Run the converter first:")
        print("  databricks bundle run -t dev sas_dbx_code_translator")
    else:
        print(f"Found {len(py_files)} file(s):")
        print()

        # Sort by modification time (newest first)
        py_files.sort(key=lambda x: x.modification_time, reverse=True)

        for f in py_files:
            # Convert timestamp
            mod_time = datetime.fromtimestamp(f.modification_time / 1000) if f.modification_time else None
            mod_str = mod_time.strftime("%Y-%m-%d %H:%M:%S") if mod_time else "Unknown"

            # Format size
            size_kb = f.size / 1024 if f.size else 0
            size_str = f"{size_kb:.1f} KB"

            print(f"  📄 {f.name}")
            print(f"     Size: {size_str}")
            print(f"     Modified: {mod_str}")
            print()

        print("=" * 80)
        print("🎯 To update a pipeline:")
        print("=" * 80)
        print()
        print("  python update_pipeline_file.py <pipeline_name> <filename>")
        print()
        print("Examples:")
        for f in py_files[:3]:  # Show first 3 as examples
            # Try to extract pipeline name from filename
            # transformed_claims_adjudication.py → claims_adjudication
            name_part = f.name.replace('transformed_', '').replace('.py', '')
            print(f"  python update_pipeline_file.py {name_part} {f.name}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()
