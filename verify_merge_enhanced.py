#!/usr/bin/env python3
"""
Verification script for enhanced MERGE translator.

Tests patterns:
1. Simple 2-table merge with filter IF first (existing, should still work)
2. Filter IF NOT first (assignment IF before filter) (NEW)
3. OR condition (NEW)
4. NOT negation (NEW)
5. 3+ tables (NEW)
"""

import sys
import re

# Read the sas_dbx.py file
with open('src/converter/sas_to_dbx_pipeline_converter.py', 'r') as f:
    content = f.read()

# Check if function exists
if 'def translate_merge_to_join' not in content:
    print("❌ Function 'translate_merge_to_join' NOT FOUND")
    sys.exit(1)

print("✅ Function 'translate_merge_to_join' EXISTS")

# Extract the function (up to the next function or print statement)
func_match = re.search(
    r'def translate_merge_to_join\(.*?\):(.*?)(?=\n\ndef\s|\nprint\()',
    content,
    re.DOTALL
)

if not func_match:
    print("❌ Could not extract function code")
    sys.exit(1)

func_code = 'def translate_merge_to_join(sas_source_text, converted_code=""):' + func_match.group(1)

# Execute the function
exec_globals = {}
exec(func_code, exec_globals)
translate_merge_to_join = exec_globals['translate_merge_to_join']

print("✅ Function loaded successfully")

# ==============================================================================
# TEST CASES
# ==============================================================================

test_cases = [
    {
        "name": "Pattern 1: Simple 2-table LEFT join (filter IF first)",
        "sas": """
data combined;
  merge claims(in=a) members(in=b);
  by member_id;
  if a;
run;
        """,
        "expected_patterns": 1,
        "expected_join": "left",
        "expected_tables": 2
    },
    {
        "name": "Pattern 2: Filter IF NOT first (assignment before filter)",
        "sas": """
data combined;
  merge claims(in=a) members(in=b);
  by member_id;
  if inmember = 0 then elig_flag = 'N';
  if a and b;
run;
        """,
        "expected_patterns": 1,
        "expected_join": "inner",
        "expected_tables": 2,
        "note": "Should detect 'if a and b' not 'if inmember = 0'"
    },
    {
        "name": "Pattern 3: OR condition",
        "sas": """
data combined;
  merge claims(in=a) members(in=b);
  by member_id;
  if a or b;
run;
        """,
        "expected_patterns": 1,
        "expected_join": "full",  # OR means keep if in either table
        "expected_tables": 2
    },
    {
        "name": "Pattern 4: NOT negation",
        "sas": """
data orphans;
  merge claims(in=a) members(in=b);
  by member_id;
  if a and not b;
run;
        """,
        "expected_patterns": 1,
        "expected_join": "left_anti",  # Keep claims without matching member
        "expected_tables": 2
    },
    {
        "name": "Pattern 5: 3+ tables",
        "sas": """
data triple;
  merge claims(in=a) members(in=b) providers(in=c);
  by member_id;
  if a and b and c;
run;
        """,
        "expected_patterns": 1,
        "expected_join": "inner",  # All three must match
        "expected_tables": 3
    },
    {
        "name": "Pattern 6: Multiple assignment IFs before filter",
        "sas": """
data multi_if;
  merge claims(in=a) members(in=b);
  by member_id;
  if age < 18 then agegroup = 'Child';
  if status = 'A' then active_flag = 1;
  if a;
run;
        """,
        "expected_patterns": 1,
        "expected_join": "left",
        "expected_tables": 2,
        "note": "Should detect 'if a' as filter, not 'if age < 18'"
    }
]

# ==============================================================================
# RUN TESTS
# ==============================================================================

print("\n" + "="*70)
print("RUNNING TEST CASES")
print("="*70)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n📊 Test {i}: {test['name']}")
    if 'note' in test:
        print(f"   Note: {test['note']}")
    print("-" * 70)

    result = translate_merge_to_join(test['sas'], "")

    # Check pattern count
    if len(result) != test['expected_patterns']:
        print(f"❌ FAIL: Expected {test['expected_patterns']} patterns, got {len(result)}")
        failed += 1
        continue

    print(f"✅ Pattern count: {len(result)} (expected {test['expected_patterns']})")

    # Check pattern details
    all_checks_passed = True

    for j, pattern in enumerate(result):
        print(f"\n   Pattern {j+1}:")
        print(f"   • Join type: {pattern.get('join_type', 'N/A')}")
        print(f"   • Tables: {len(pattern.get('tables', []))}")

        # Check join type
        if pattern.get('join_type') != test['expected_join']:
            print(f"   ❌ Expected join type '{test['expected_join']}', got '{pattern.get('join_type')}'")
            all_checks_passed = False
        else:
            print(f"   ✅ Join type matches")

        # Check table count
        if len(pattern.get('tables', [])) != test['expected_tables']:
            print(f"   ❌ Expected {test['expected_tables']} tables, got {len(pattern.get('tables', []))}")
            all_checks_passed = False
        else:
            print(f"   ✅ Table count matches")

        print(f"   • BY vars: {pattern.get('by_vars', 'N/A')}")
        print(f"   • Output: {pattern.get('output_table', 'N/A')}")

    if all_checks_passed:
        print(f"\n✅ Test {i} PASSED")
        passed += 1
    else:
        print(f"\n❌ Test {i} FAILED")
        failed += 1

# ==============================================================================
# SUMMARY
# ==============================================================================

print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"\n✅ Passed: {passed}/{len(test_cases)}")
print(f"❌ Failed: {failed}/{len(test_cases)}")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED!")
    print("\nThe enhanced MERGE translator now supports:")
    print("  ✅ Filter IF detection (not just first IF)")
    print("  ✅ Assignment vs filter IF distinction")
    print("  ✅ OR conditions")
    print("  ✅ NOT negation (anti-joins)")
    print("  ✅ 3+ table merges")
    print("\nGap closed: MERGE join-type inference")
    sys.exit(0)
else:
    print("\n⚠️ SOME TESTS FAILED")
    print("Review the output above for details.")
    sys.exit(1)
