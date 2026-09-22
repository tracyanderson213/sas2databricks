#!/usr/bin/env python3
"""
Verification script for nested IF → CASE WHEN translator.

Tests patterns:
1. Simple nested IF/ELSE (same variable, 3+ branches)
2. Nested IF without final ELSE
3. Multiple variables with nested IFs (different variables)
4. Single IF (should NOT consolidate)
"""

import sys
import re

# Test if the function exists first
print("Checking for translate_nested_if_to_case function...")

# Read the sas_dbx.py file
with open('src/converter/sas_dbx.py', 'r') as f:
    content = f.read()

# Check if function exists
if 'def translate_nested_if_to_case' not in content:
    print("❌ Function 'translate_nested_if_to_case' NOT FOUND")
    print("   This is expected - implementing now...")
    sys.exit(1)

print("✅ Function 'translate_nested_if_to_case' EXISTS")

# Extract the function
func_match = re.search(
    r'def translate_nested_if_to_case\(.*?\):(.*?)(?=\n\ndef\s|\nprint\()',
    content,
    re.DOTALL
)

if not func_match:
    print("❌ Could not extract function code")
    sys.exit(1)

func_code = 'def translate_nested_if_to_case(sas_source_text):' + func_match.group(1)

# Execute the function
exec_globals = {}
exec(func_code, exec_globals)
translate_nested_if_to_case = exec_globals['translate_nested_if_to_case']

print("✅ Function loaded successfully")

# ==============================================================================
# TEST CASES
# ==============================================================================

test_cases = [
    {
        "name": "Pattern 1: Simple nested IF/ELSE (3+ branches)",
        "sas": """
data categorized;
  set claims;
  if age < 18 then agegroup = 'Child';
  else if age < 65 then agegroup = 'Adult';
  else if age >= 65 then agegroup = 'Senior';
  else agegroup = 'Unknown';
run;
        """,
        "expected_patterns": 1,
        "expected_var": "agegroup",
        "expected_branches": 4  # 3 IF + 1 ELSE
    },
    {
        "name": "Pattern 2: Nested IF without final ELSE",
        "sas": """
data status;
  set claims;
  if amount > 10000 then priority = 'High';
  else if amount > 5000 then priority = 'Medium';
  else if amount > 1000 then priority = 'Low';
run;
        """,
        "expected_patterns": 1,
        "expected_var": "priority",
        "expected_branches": 3  # 3 IF, no ELSE
    },
    {
        "name": "Pattern 3: Multiple variables (should detect both)",
        "sas": """
data multi;
  set claims;
  if age < 18 then agegroup = 'Child';
  else if age < 65 then agegroup = 'Adult';
  else agegroup = 'Senior';

  if status = 'A' then status_desc = 'Active';
  else if status = 'I' then status_desc = 'Inactive';
  else status_desc = 'Unknown';
run;
        """,
        "expected_patterns": 2,
        "expected_vars": ["agegroup", "status_desc"]
    },
    {
        "name": "Pattern 4: Single IF (should NOT consolidate)",
        "sas": """
data simple;
  set claims;
  if age < 18 then minor_flag = 'Y';
  else minor_flag = 'N';
run;
        """,
        "expected_patterns": 0  # Only 2 branches, don't consolidate
    },
    {
        "name": "Pattern 5: Complex conditions",
        "sas": """
data risk;
  set claims;
  if age > 65 and chronic_condition = 'Y' then risk = 'Very High';
  else if age > 65 then risk = 'High';
  else if chronic_condition = 'Y' then risk = 'Medium';
  else if age < 18 then risk = 'Low';
  else risk = 'Normal';
run;
        """,
        "expected_patterns": 1,
        "expected_var": "risk",
        "expected_branches": 5
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
    print("-" * 70)

    result = translate_nested_if_to_case(test['sas'])

    # Check pattern count
    if len(result) != test['expected_patterns']:
        print(f"❌ FAIL: Expected {test['expected_patterns']} patterns, got {len(result)}")
        if len(result) > 0:
            print(f"   Found patterns for variables: {[p.get('target_var') for p in result]}")
        failed += 1
        continue

    print(f"✅ Pattern count: {len(result)} (expected {test['expected_patterns']})")

    # If no patterns expected, we're done
    if test['expected_patterns'] == 0:
        print(f"\n✅ Test {i} PASSED (correctly detected no consolidation needed)")
        passed += 1
        continue

    # Check pattern details
    all_checks_passed = True

    for j, pattern in enumerate(result):
        print(f"\n   Pattern {j+1}:")
        print(f"   • Variable: {pattern.get('target_var', 'N/A')}")
        print(f"   • Branches: {len(pattern.get('branches', []))}")

        # Check for single variable test
        if 'expected_var' in test:
            if pattern.get('target_var') != test['expected_var']:
                print(f"   ❌ Expected var '{test['expected_var']}', got '{pattern.get('target_var')}'")
                all_checks_passed = False
            else:
                print(f"   ✅ Variable matches")

            if len(pattern.get('branches', [])) != test['expected_branches']:
                print(f"   ❌ Expected {test['expected_branches']} branches, got {len(pattern.get('branches', []))}")
                all_checks_passed = False
            else:
                print(f"   ✅ Branch count matches")

        # Check for multiple variables test
        elif 'expected_vars' in test:
            if pattern.get('target_var') not in test['expected_vars']:
                print(f"   ❌ Variable '{pattern.get('target_var')}' not in expected vars {test['expected_vars']}")
                all_checks_passed = False
            else:
                print(f"   ✅ Variable in expected list")

        # Show first few branches
        branches = pattern.get('branches', [])
        for k, branch in enumerate(branches[:3]):
            condition = branch.get('condition', 'N/A')
            value = branch.get('value', 'N/A')
            print(f"   • Branch {k+1}: WHEN {condition} THEN {value}")

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
    print("\nThe nested IF → CASE WHEN translator now supports:")
    print("  ✅ Multi-branch IF/ELSE consolidation (3+ branches)")
    print("  ✅ Detection of multiple variables")
    print("  ✅ Complex conditions (AND/OR)")
    print("  ✅ Smart filtering (skips simple 2-branch IFs)")
    print("\nGap closed: Nested IF → CASE WHEN consolidation")
    print("Phase 1: COMPLETE (4 of 4 items done!)")
    sys.exit(0)
else:
    print("\n⚠️ SOME TESTS FAILED")
    print("Review the output above for details.")
    sys.exit(1)
