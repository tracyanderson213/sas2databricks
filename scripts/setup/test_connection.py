#!/usr/bin/env python3
"""
Test Databricks Connection
===========================
Validates authentication and connectivity to Databricks workspace.

Usage:
    python scripts/setup/test_connection.py

Validates:
    - Authentication (OAuth via service principal)
    - Workspace access
    - Catalog visibility
    - SQL Warehouse connectivity
"""

from databricks.sdk import WorkspaceClient
import sys

def test_connection():
    """Test Databricks connection and report status"""

    print("="*80)
    print("🔌 Testing Databricks Connection")
    print("="*80)
    print()

    try:
        # Initialize client (reads from DATABRICKS_CONFIG_FILE env var)
        print("1️⃣  Authenticating...")
        w = WorkspaceClient()

        # Test workspace access
        print("2️⃣  Testing workspace access...")
        current_user = w.current_user.me()
        print(f"   ✅ Authenticated as: {current_user.user_name}")
        print(f"   ✅ Active: {current_user.active}")

        # Test catalog access
        print("3️⃣  Testing Unity Catalog access...")
        catalogs = list(w.catalogs.list())
        print(f"   ✅ Visible catalogs: {len(catalogs)}")

        catalog_names = [c.name for c in catalogs]
        if "na-dbxtraining" in catalog_names:
            print(f"   ✅ Target catalog 'na-dbxtraining' is accessible")
        else:
            print(f"   ⚠️  Target catalog 'na-dbxtraining' not found")
            print(f"   Available catalogs: {', '.join(catalog_names[:5])}")

        # Test SQL Warehouse
        print("4️⃣  Testing SQL Warehouse access...")
        warehouses = list(w.warehouses.list())
        warehouse_ids = [wh.id for wh in warehouses if wh.id]

        if "2f51df324d05e45d" in warehouse_ids:
            print(f"   ✅ Target warehouse '2f51df324d05e45d' is accessible")
        else:
            print(f"   ⚠️  Target warehouse '2f51df324d05e45d' not found")
            print(f"   Available warehouses: {len(warehouse_ids)}")

        print()
        print("="*80)
        print("✅ CONNECTION TEST PASSED")
        print("="*80)
        print()
        print("Ready to deploy:")
        print("  databricks bundle deploy -t dev --var developer_id=yourname")
        print()

        return 0

    except Exception as e:
        print()
        print("="*80)
        print("❌ CONNECTION TEST FAILED")
        print("="*80)
        print()
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify .databrickscfg exists")
        print("  2. Check DATABRICKS_CONFIG_FILE environment variable")
        print("  3. Verify service principal credentials are valid")
        print("  4. Check network connectivity to workspace")
        print()

        import traceback
        traceback.print_exc()

        return 1

if __name__ == "__main__":
    sys.exit(test_connection())
