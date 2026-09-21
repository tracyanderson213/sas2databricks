#!/usr/bin/env python3
"""
Reset Schemas (DROP CASCADE)
============================
Drops and recreates bronze/silver/gold schemas for clean restart.

⚠️  WARNING: This deletes ALL tables and data in the schemas!

Usage:
    python scripts/utilities/reset_schemas.py --developer-id tanderson
    python scripts/utilities/reset_schemas.py --developer-id tanderson --catalog na-dbxtraining --confirm

Safety:
    - Requires --confirm flag to execute (prevents accidents)
    - Shows preview without --confirm
    - Deletes tables via DROP SCHEMA CASCADE
    - Recreates empty schemas

Use cases:
    - Clean development environment restart
    - Reset after failed migration attempt
    - Clear test data between runs
"""

from databricks.sdk import WorkspaceClient
import argparse
import sys

def reset_schemas(developer_id: str, catalog: str = "na-dbxtraining",
                 schema_prefix: str = "sas", confirm: bool = False):
    """Drop and recreate schemas"""

    print("="*80)
    print("⚠️  RESET SCHEMAS (DROP CASCADE)")
    print("="*80)
    print()

    schemas = [
        f'{schema_prefix}_{developer_id}_bronze',
        f'{schema_prefix}_{developer_id}_silver',
        f'{schema_prefix}_{developer_id}_gold'
    ]

    print(f"Catalog:        {catalog}")
    print(f"Developer ID:   {developer_id}")
    print(f"Schema prefix:  {schema_prefix}")
    print()
    print("The following schemas will be DROPPED and recreated:")
    for schema in schemas:
        print(f"  - {catalog}.{schema}")
    print()
    print("⚠️  This will DELETE ALL TABLES AND DATA in these schemas!")
    print()

    if not confirm:
        print("="*80)
        print("🔒 SAFETY CHECK: --confirm flag required")
        print("="*80)
        print()
        print("This is a destructive operation. To proceed, run:")
        print(f"  python scripts/utilities/reset_schemas.py \\")
        print(f"    --developer-id {developer_id} \\")
        print(f"    --catalog {catalog} \\")
        print(f"    --confirm")
        print()
        return 0

    print("⚠️  --confirm flag detected, proceeding with DROP CASCADE")
    print()

    try:
        w = WorkspaceClient()

        # Get default warehouse
        warehouses = list(w.warehouses.list())
        if not warehouses:
            print("❌ No SQL warehouses available")
            return 1

        warehouse_id = warehouses[0].id

        for schema in schemas:
            full_name = f"{catalog}.{schema}"

            try:
                # Check if schema exists
                existing = w.schemas.get(full_name)

                # Drop schema
                print(f"🗑️  Dropping schema: {full_name}")
                drop_sql = f"DROP SCHEMA IF EXISTS `{catalog}`.`{schema}` CASCADE"

                # Execute via SQL warehouse
                result = w.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=drop_sql,
                    wait_timeout="30s"
                )

                print(f"   ✅ Dropped")

            except Exception as e:
                # Schema doesn't exist
                print(f"ℹ️  Schema not found (OK): {full_name}")

            # Recreate schema
            print(f"📦 Creating schema: {full_name}")
            w.schemas.create(
                name=schema,
                catalog_name=catalog,
                comment=f'3Cloud SAS Migration — Reset by {developer_id}'
            )
            print(f"   ✅ Created")

        print()
        print("="*80)
        print("✅ SCHEMAS RESET COMPLETE")
        print("="*80)
        print()
        print("Schemas are now empty and ready for fresh deployment:")
        print(f"  databricks bundle deploy -t dev --var developer_id={developer_id}")
        print()

        return 0

    except Exception as e:
        print()
        print("="*80)
        print("❌ RESET FAILED")
        print("="*80)
        print()
        print(f"Error: {e}")
        print()

        import traceback
        traceback.print_exc()

        return 1

def main():
    parser = argparse.ArgumentParser(
        description='Drop and recreate SAS migration schemas (⚠️  DESTRUCTIVE)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--developer-id', required=True,
                       help='Developer identifier (e.g., tanderson)')
    parser.add_argument('--catalog', default='na-dbxtraining',
                       help='Target catalog (default: na-dbxtraining)')
    parser.add_argument('--schema-prefix', default='sas',
                       help='Schema prefix (default: sas)')
    parser.add_argument('--confirm', action='store_true',
                       help='REQUIRED to execute (safety check)')

    args = parser.parse_args()

    return reset_schemas(
        developer_id=args.developer_id,
        catalog=args.catalog,
        schema_prefix=args.schema_prefix,
        confirm=args.confirm
    )

if __name__ == "__main__":
    sys.exit(main())
