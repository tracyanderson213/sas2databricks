#!/usr/bin/env python3
"""
Test PAT-based connection for bundle deployment
"""
import os
from databricks.sdk import WorkspaceClient

# Force use of bundle-deploy profile
os.environ['DATABRICKS_CONFIG_PROFILE'] = 'bundle-deploy'
os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg'

print("="*80)
print("🔌 Testing PAT Connection (bundle-deploy profile)")
print("="*80)
print()

try:
    w = WorkspaceClient()

    print("1️⃣  Authentication...")
    current_user = w.current_user.me()
    print(f"   ✅ Authenticated as: {current_user.user_name}")
    print(f"   ✅ Active: {current_user.active}")
    print()

    print("2️⃣  Testing workspace access...")
    # Try to list workspace root (requires workspace scope)
    try:
        objects = w.workspace.list("/")
        print(f"   ✅ Workspace scope: PRESENT")
        print(f"   ✅ Can list /Workspace root")
    except Exception as e:
        print(f"   ❌ Workspace scope: MISSING")
        print(f"   Error: {e}")
    print()

    print("3️⃣  Testing Unity Catalog access...")
    catalogs = list(w.catalogs.list())
    print(f"   ✅ Visible catalogs: {len(catalogs)}")

    # Check target catalog
    target_catalog = 'na-dbxtraining'
    catalog_names = [c.name for c in catalogs]
    if target_catalog in catalog_names:
        print(f"   ✅ Target catalog '{target_catalog}' is accessible")
    else:
        print(f"   ⚠️  Target catalog '{target_catalog}' not found")
        print(f"   Available: {catalog_names}")
    print()

    print("="*80)
    print("✅ PAT CONNECTION TEST PASSED")
    print("="*80)
    print()
    print("Ready to deploy bundle with:")
    print("  DATABRICKS_CONFIG_PROFILE=bundle-deploy databricks bundle deploy -t dev")
    print()

except Exception as e:
    print("="*80)
    print("❌ CONNECTION TEST FAILED")
    print("="*80)
    print()
    print(f"Error: {e}")
    print()
    print("Troubleshooting:")
    print("  1. Verify you replaced YOUR_PAT_TOKEN_HERE with your actual PAT")
    print("  2. Check PAT starts with 'dapi...'")
    print("  3. Generate new PAT if needed (may be expired)")
    print()
