#!/usr/bin/env python3
"""
Copy a transformed file from volume to local transformations folder for testing

Usage:
    python copy_transformed_file.py                              # List available files
    python copy_transformed_file.py transformed_claims_adjudication.py  # Copy specific file
"""
import os
import sys
from databricks.sdk import WorkspaceClient

# Use PAT auth
os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

volume_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"
converted_dir = f"{volume_base}/converted"
local_target = "/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/transformations/current_transformation.py"

print("="*80)
print("📦 Copy Transformed File to Bundle")
print("="*80)
print()

# List available files
try:
    files = w.files.list_directory_contents(converted_dir)
    py_files = [f for f in files if f.name.endswith('.py')]

    if not py_files:
        print("❌ No transformed files found in volume")
        print(f"   Location: {converted_dir}")
        print()
        print("Run the converter first:")
        print("  databricks bundle run sas_code_translator_tanderson -t dev")
        sys.exit(1)

    print(f"📁 Available files in {converted_dir}:")
    print()
    for i, f in enumerate(py_files, 1):
        size_kb = f.file_size / 1024 if f.file_size else 0
        print(f"  {i}. {f.name} ({size_kb:.1f} KB)")
    print()

    # If filename provided, use it
    if len(sys.argv) > 1:
        target_filename = sys.argv[1]

        # Find matching file
        matching = [f for f in py_files if f.name == target_filename]
        if not matching:
            print(f"❌ File not found: {target_filename}")
            print()
            print("Available files:")
            for f in py_files:
                print(f"  • {f.name}")
            sys.exit(1)

        target_file = matching[0]
    else:
        # Interactive mode - just show list
        print("Usage:")
        print(f"  python copy_transformed_file.py <filename>")
        print()
        print("Example:")
        print(f"  python copy_transformed_file.py {py_files[0].name}")
        sys.exit(0)

    # Download from volume
    print(f"📥 Downloading: {target_file.name}")
    source_path = f"{converted_dir}/{target_file.name}"

    # Read from volume via API
    content = w.files.download(source_path).contents.read().decode('utf-8')

    # Ensure local transformations directory exists
    os.makedirs(os.path.dirname(local_target), exist_ok=True)

    # Write to local file
    with open(local_target, 'w') as f:
        f.write(content)

    print(f"✅ Copied to: {local_target}")
    print()

    print("="*80)
    print("✅ File Ready for Testing")
    print("="*80)
    print()
    print("Next steps:")
    print()
    print("1. Deploy bundle to update pipeline:")
    print("   DATABRICKS_CONFIG_FILE=.databrickscfg.bundle \\")
    print("   databricks bundle deploy -t dev --var developer_id=tanderson")
    print()
    print("2. Start pipeline in UI:")
    print("   • Workflows → Delta Live Tables")
    print("   • Find: sas_dbx_TEMPLATE_tanderson_pipeline")
    print("   • Click 'Start'")
    print()
    print("3. Validate output in schemas:")
    print("   • sas_tanderson_bronze.*")
    print("   • sas_tanderson_silver.*")
    print("   • sas_tanderson_gold.*")
    print()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
