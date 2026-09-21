#!/usr/bin/env python3
"""Read the original SAS file from volume"""
import os
from databricks.sdk import WorkspaceClient

os.environ['DATABRICKS_CONFIG_FILE'] = '/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb/.databrickscfg.bundle'

w = WorkspaceClient()

volume_path = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/claims_adjudication.sas"

print("Reading SAS file...")
print()

try:
    response = w.files.download(volume_path)
    content = response.contents.read().decode('utf-8')

    # Find the sections we care about
    lines = content.split('\n')

    in_flag_elig = False
    in_report = False
    flag_elig_lines = []
    report_lines = []

    for i, line in enumerate(lines):
        # Look for flag_eligibility
        if 'flag_eligibility' in line.lower():
            in_flag_elig = True
            flag_elig_lines.append(f"Line {i+1}: {line}")
            # Get context (20 lines after)
            for j in range(1, 21):
                if i+j < len(lines):
                    flag_elig_lines.append(f"Line {i+j+1}: {lines[i+j]}")
            in_flag_elig = False

        # Look for claims_adjudicated_report
        if 'clm_claims_adjudicated_report' in line.lower() or 'claims_adjudicated_report' in line.lower():
            in_report = True
            report_lines.append(f"Line {i+1}: {line}")
            # Get context (20 lines after)
            for j in range(1, 21):
                if i+j < len(lines):
                    report_lines.append(f"Line {i+j+1}: {lines[i+j]}")
            in_report = False

    if flag_elig_lines:
        print("=" * 80)
        print("FLAG_ELIGIBILITY in SAS:")
        print("=" * 80)
        for line in flag_elig_lines:
            print(line)
        print()

    if report_lines:
        print("=" * 80)
        print("CLM_CLAIMS_ADJUDICATED_REPORT in SAS:")
        print("=" * 80)
        for line in report_lines:
            print(line)
        print()

    if not flag_elig_lines and not report_lines:
        print("⚠️  Neither flag_eligibility nor clm_claims_adjudicated_report found in SAS file")
        print()
        print("Let me search for macros and report sections...")
        print()

        # Look for macro definitions
        for i, line in enumerate(lines):
            if '%macro' in line.lower():
                print(f"Line {i+1}: {line}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
