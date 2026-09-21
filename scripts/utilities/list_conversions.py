#!/usr/bin/env python3
"""
List Conversion Results
=======================
Shows all SAS files that have been converted and their output status.

Usage:
    python scripts/utilities/list_conversions.py
    python scripts/utilities/list_conversions.py --format json
    python scripts/utilities/list_conversions.py --output-dir ./transformations

Output:
    - Lists all converted Python files
    - Shows source SAS filename (from header comment)
    - Reports file size and modification time
    - Identifies pipeline YAML files
"""

import os
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

def extract_sas_source(python_file: str) -> str:
    """Extract original SAS filename from Python file header"""
    try:
        with open(python_file, 'r') as f:
            # Read first 30 lines (header should be at top)
            for line in f.readlines()[:30]:
                if 'Converted from:' in line:
                    # Extract filename from comment
                    parts = line.split('Converted from:')
                    if len(parts) > 1:
                        return parts[1].strip().strip('#').strip()
        return "Unknown"
    except Exception:
        return "Unknown"

def list_conversions(output_dir: str = "./transformations",
                    pipeline_dir: str = "./resources/pipelines",
                    format_type: str = "table"):
    """List all converted files and their metadata"""

    results = []

    # Scan transformations directory
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.py') and filename.startswith('converted_'):
                filepath = os.path.join(output_dir, filename)

                # Get file metadata
                stat = os.stat(filepath)
                size_kb = stat.st_size / 1024
                modified = datetime.fromtimestamp(stat.st_mtime)

                # Extract source SAS file
                sas_source = extract_sas_source(filepath)

                # Check for corresponding pipeline YAML
                base_name = filename.replace('converted_', '').replace('.py', '')
                yaml_file = f"pipeline_{base_name}.yml"
                yaml_path = os.path.join(pipeline_dir, yaml_file)
                has_yaml = os.path.exists(yaml_path)

                results.append({
                    'python_file': filename,
                    'sas_source': sas_source,
                    'size_kb': round(size_kb, 1),
                    'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
                    'has_pipeline_yaml': has_yaml,
                    'yaml_file': yaml_file if has_yaml else None
                })

    # Output results
    if format_type == "json":
        print(json.dumps(results, indent=2))
        return 0

    # Table format
    print("="*120)
    print("📊 SAS to Databricks Conversion Results")
    print("="*120)
    print()

    if not results:
        print("No converted files found in ./transformations/")
        print()
        print("Run the converter first:")
        print("  databricks bundle run sas_dbx_code_translator -t dev")
        print()
        return 0

    print(f"Found {len(results)} converted file(s)")
    print()

    # Header
    print(f"{'Python File':<50} {'SAS Source':<40} {'Size':<10} {'Pipeline':<10}")
    print("-"*120)

    # Rows
    for r in results:
        yaml_status = "✅ Yes" if r['has_pipeline_yaml'] else "❌ No"
        print(f"{r['python_file']:<50} {r['sas_source']:<40} {r['size_kb']:>6.1f} KB  {yaml_status:<10}")

    print()
    print("="*120)
    print()

    # Pipeline YAML summary
    yaml_count = sum(1 for r in results if r['has_pipeline_yaml'])
    print(f"Pipeline YAMLs: {yaml_count}/{len(results)}")

    if yaml_count < len(results):
        print()
        print("Missing pipeline YAMLs for:")
        for r in results:
            if not r['has_pipeline_yaml']:
                print(f"  - {r['python_file']}")

    print()
    print("Next steps:")
    print("  1. Review converted files in ./transformations/")
    print("  2. Check pipeline YAMLs in ./resources/pipelines/")
    print("  3. Deploy: databricks bundle deploy -t dev")
    print()

    return 0

def main():
    parser = argparse.ArgumentParser(
        description='List all converted SAS files and their metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--output-dir', default='./transformations',
                       help='Directory containing converted Python files')
    parser.add_argument('--pipeline-dir', default='./resources/pipelines',
                       help='Directory containing pipeline YAML files')
    parser.add_argument('--format', choices=['table', 'json'], default='table',
                       help='Output format (default: table)')

    args = parser.parse_args()

    return list_conversions(
        output_dir=args.output_dir,
        pipeline_dir=args.pipeline_dir,
        format_type=args.format
    )

if __name__ == "__main__":
    sys.exit(main())
