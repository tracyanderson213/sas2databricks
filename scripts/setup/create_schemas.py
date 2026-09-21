#!/usr/bin/env python3
"""
Create Schemas for SAS Migration
=================================
Creates bronze/silver/gold schemas with proper naming convention.

Usage:
    python scripts/setup/create_schemas.py --developer-id tanderson
    python scripts/setup/create_schemas.py --developer-id prod --catalog sas_migrate

Arguments:
    --developer-id: Your identifier (creates sas_{id}_bronze/silver/gold)
    --catalog: Target catalog (default: na-dbxtraining)
    --schema-prefix: Schema prefix (default: sas)
    --dry-run: Show what would be created without actually creating

Examples:
    # Development schemas
    python scripts/setup/create_schemas.py --developer-id tanderson

    # Production schemas
    python scripts/setup/create_schemas.py --developer-id prod --catalog sas_migrate

    # Preview only
    python scripts/setup/create_schemas.py --developer-id tanderson --dry-run
"""

from databricks.sdk import WorkspaceClient
import argparse
import sys

def create_schemas(developer_id: str, catalog: str = "na-dbxtraining",
                   schema_prefix: str = "sas", dry_run: bool = False):
    """Create bronze/silver/gold schemas"""

    print("="*80)
    print("📦 Creating SAS Migration Schemas")
    print("="*80)
    print()

    # Schema definitions
    schemas = [
        {
            'name': f'{schema_prefix}_{developer_id}_bronze',
            'comment': f'3Cloud SAS Migration — Bronze (raw SAS data) — {developer_id}'
        },
        {
            'name': f'{schema_prefix}_{developer_id}_silver',
            'comment': f'3Cloud SAS Migration — Silver (transforms) — {developer_id}'
        },
        {
            'name': f'{schema_prefix}_{developer_id}_gold',
            'comment': f'3Cloud SAS Migration — Gold (analytics-ready) — {developer_id}'
        },
        {
            'name': 'sas2dbx_migrate',
            'comment': '3Cloud SAS Migration — Configuration and metadata (shared)'
        }
    ]

    print(f"Catalog:        {catalog}")
    print(f"Developer ID:   {developer_id}")
    print(f"Schema prefix:  {schema_prefix}")
    print(f"Dry run:        {dry_run}")
    print()

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
        for schema in schemas:
            print(f"Would create: {catalog}.{schema['name']}")
            print(f"  Comment: {schema['comment']}")
            print()

        print("To create these schemas, run without --dry-run")
        return 0

    try:
        w = WorkspaceClient()

        for schema in schemas:
            full_name = f"{catalog}.{schema['name']}"

            try:
                # Check if schema exists
                existing = w.schemas.get(full_name)
                print(f"✅ Schema already exists: {full_name}")

            except Exception:
                # Schema doesn't exist, create it
                print(f"📦 Creating schema: {full_name}")
                w.schemas.create(
                    name=schema['name'],
                    catalog_name=catalog,
                    comment=schema['comment']
                )
                print(f"   ✅ Created")

        print()
        print("="*80)
        print("✅ SCHEMAS READY")
        print("="*80)
        print()
        print("Next steps:")
        print(f"  1. Deploy bundle:")
        print(f"     databricks bundle deploy -t dev --var developer_id={developer_id}")
        print(f"  2. Run converter:")
        print(f"     databricks bundle run sas_dbx_code_translator -t dev")
        print()

        return 0

    except Exception as e:
        print()
        print("="*80)
        print("❌ SCHEMA CREATION FAILED")
        print("="*80)
        print()
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print(f"  1. Verify you have CREATE SCHEMA permission on catalog '{catalog}'")
        print("  2. Check if catalog exists and is accessible")
        print("  3. Verify service principal has proper grants")
        print()

        import traceback
        traceback.print_exc()

        return 1

def main():
    parser = argparse.ArgumentParser(
        description='Create SAS migration schemas in Unity Catalog',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--developer-id', required=True,
                       help='Developer identifier (e.g., tanderson, prod)')
    parser.add_argument('--catalog', default='na-dbxtraining',
                       help='Target catalog (default: na-dbxtraining)')
    parser.add_argument('--schema-prefix', default='sas',
                       help='Schema prefix (default: sas)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be created without creating')

    args = parser.parse_args()

    return create_schemas(
        developer_id=args.developer_id,
        catalog=args.catalog,
        schema_prefix=args.schema_prefix,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    sys.exit(main())
