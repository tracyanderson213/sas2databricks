#!/usr/bin/env python3
"""
Verify prerequisites for Adventure Works SQL Server ingestion

Checks:
1. UC connection exists
2. Databricks CLI is working
3. Bundle is valid
"""
import os
import subprocess
import sys

os.environ['DATABRICKS_CONFIG_FILE'] = '.databrickscfg.bundle'

print("=" * 80)
print("🔍 Verifying Adventure Works SQL Prerequisites")
print("=" * 80)
print()

checks_passed = 0
checks_failed = 0

# Check 1: Databricks CLI
print("1️⃣  Checking Databricks CLI...")
try:
    result = subprocess.run(
        ['databricks', '--version'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"   ✅ Databricks CLI installed: {version}")
        checks_passed += 1
    else:
        print(f"   ❌ Databricks CLI not working")
        checks_failed += 1
except Exception as e:
    print(f"   ❌ Databricks CLI not found: {e}")
    checks_failed += 1

print()

# Check 2: UC Connection
print("2️⃣  Checking UC Connection (adventureworks_sql)...")
try:
    result = subprocess.run(
        ['databricks', 'connections', 'get', 'adventureworks_sql'],
        capture_output=True,
        text=True,
        timeout=10,
        env=os.environ
    )
    if result.returncode == 0 and 'adventureworks_sql' in result.stdout:
        print(f"   ✅ Connection 'adventureworks_sql' exists")
        if '"state": "READY"' in result.stdout or '"state":"READY"' in result.stdout:
            print(f"   ✅ Connection is READY")
        else:
            print(f"   ⚠️  Connection exists but may not be READY")
        checks_passed += 1
    else:
        print(f"   ❌ Connection 'adventureworks_sql' not found")
        print()
        print("   To create it, run:")
        print("   databricks connections create \\")
        print("     --name adventureworks_sql \\")
        print("     --connection-type sqlserver \\")
        print("     --options '{")
        print('       "host": "sqldbdbxtraining.database.windows.net",')
        print('       "port": "1433",')
        print('       "database": "sqldb-adventureworks",')
        print('       "user": "sqladministrator@sqldbdbxtraining",')
        print('       "password": "{{secrets/dbx-ss-kv-natraining-2/natraining-sql-adventureworks-password}}"')
        print("     }'")
        checks_failed += 1
except Exception as e:
    print(f"   ❌ Error checking connection: {e}")
    checks_failed += 1

print()

# Check 3: databricks.yml updated
print("3️⃣  Checking databricks.yml...")
try:
    with open('databricks.yml', 'r') as f:
        content = f.read()
        if 'adventureworks_ingestion:' in content:
            print(f"   ✅ Pipeline 'adventureworks_ingestion' found in databricks.yml")
            checks_passed += 1
        else:
            print(f"   ❌ Pipeline 'adventureworks_ingestion' not found in databricks.yml")
            print(f"   This should have been added automatically!")
            checks_failed += 1
except Exception as e:
    print(f"   ❌ Error reading databricks.yml: {e}")
    checks_failed += 1

print()

# Check 4: SAS file exists
print("4️⃣  Checking SAS file (sales_summary.sas)...")
try:
    if os.path.exists('specifications/sales_summary.sas'):
        print(f"   ✅ SAS file exists: specifications/sales_summary.sas")
        checks_passed += 1
    else:
        print(f"   ❌ SAS file not found: specifications/sales_summary.sas")
        checks_failed += 1
except Exception as e:
    print(f"   ❌ Error checking SAS file: {e}")
    checks_failed += 1

print()

# Summary
print("=" * 80)
print("📊 Summary")
print("=" * 80)
print()
print(f"✅ Passed: {checks_passed}")
print(f"❌ Failed: {checks_failed}")
print()

if checks_failed == 0:
    print("🎉 All prerequisites met! Ready to proceed with:")
    print()
    print("   Next step:")
    print("   databricks bundle deploy -t dev")
    print()
    sys.exit(0)
else:
    print("⚠️  Some prerequisites not met. Fix the issues above and try again.")
    print()
    if checks_failed == 1 and "Connection" in str(checks_failed):
        print("   Most likely issue: UC connection not created yet")
        print("   See: QUICK_START_SQL_VALIDATION.md Step 1")
    print()
    sys.exit(1)
