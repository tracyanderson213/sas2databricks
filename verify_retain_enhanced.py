#!/usr/bin/env python3
"""
Verification script for enhanced RETAIN translator.

Tests three patterns:
1. Single variable running sum (existing)
2. Multiple variables running sum (NEW)
3. Carry-forward pattern (NEW)
"""

import sys
import re

# Read the sas_dbx.py file
with open('src/converter/sas_to_dbx_pipeline_converter.py', 'r') as f:
    content = f.read()

# Check if function exists
if 'def translate_retain_to_window' not in content:
    print("❌ Function 'translate_retain_to_window' NOT FOUND")
    sys.exit(1)

print("✅ Function 'translate_retain_to_window' EXISTS")

# Extract the function
func_match = re.search(
    r'def translate_retain_to_window\(.*?\):(.*?)(?=\n\ndef\s|\nprint\()',
    content,
    re.DOTALL
)

if not func_match:
    print("❌ Could not extract function code")
    sys.exit(1)

func_code = 'def translate_retain_to_window(sas_source_text):' + func_match.group(1)

# Execute the function
exec_globals = {}
exec(func_code, exec_globals)
translate_retain_to_window = exec_globals['translate_retain_to_window']

print("✅ Function loaded successfully")

# ==============================================================================
# TEST CASES
# ==============================================================================

test_cases = [
    {
        "name": "Pattern 1: Single variable running sum",
        "sas": """
proc sort data=claims; by member_id claim_date; run;

data running_totals;
  set claims;
  by member_id;
  retain ytd_paid 0;
  if first.member_id then ytd_paid = 0;
  ytd_paid + billed_amount;
run;
        """,
        "expected_patterns": 1,
        "expected_type": "running_sum",
        "expected_var": "ytd_paid",
        "expected_source": "billed_amount"
    },
    {
        "name": "Pattern 2: Multiple variables running sum",
        "sas": """
proc sort data=claims; by member_id claim_date; run;

data multi_totals;
  set claims;
  by member_id;
  retain ytd_paid claim_count 0 0;
  if first.member_id then do;
    ytd_paid = 0;
    claim_count = 0;
  end;
  ytd_paid + billed_amount;
  claim_count + 1;
run;
        """,
        "expected_patterns": 2,
        "expected_type": "running_sum",
        "expected_vars": ["ytd_paid", "claim_count"]
    },
    {
        "name": "Pattern 3: Carry-forward (not missing syntax)",
        "sas": """
proc sort data=claims; by member_id claim_date; run;

data carry_diag;
  set claims;
  by member_id;
  retain last_diag_code;
  if not missing(diag_code) then last_diag_code = diag_code;
run;
        """,
        "expected_patterns": 1,
        "expected_type": "carry_forward",
        "expected_var": "last_diag_code",
        "expected_source": "diag_code"
    },
    {
        "name": "Pattern 3b: Carry-forward (~= . syntax)",
        "sas": """
proc sort data=claims; by member_id claim_date; run;

data carry_provider;
  set claims;
  by member_id;
  retain last_provider;
  if provider_id ~= . then last_provider = provider_id;
run;
        """,
        "expected_patterns": 1,
        "expected_type": "carry_forward",
        "expected_var": "last_provider",
        "expected_source": "provider_id"
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

    result = translate_retain_to_window(test['sas'])

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
        print(f"   • Type: {pattern.get('pattern_type', 'N/A')}")
        print(f"   • Variable: {pattern.get('retain_var', 'N/A')}")

        # Check pattern type
        if pattern.get('pattern_type') != test['expected_type']:
            print(f"   ❌ Expected type '{test['expected_type']}', got '{pattern.get('pattern_type')}'")
            all_checks_passed = False

        # Check for running_sum patterns
        if test['expected_type'] == 'running_sum':
            # For multiple variables test, check that all vars are present
            if 'expected_vars' in test:
                if pattern.get('retain_var') not in test['expected_vars']:
                    print(f"   ❌ Variable '{pattern.get('retain_var')}' not in expected vars {test['expected_vars']}")
                    all_checks_passed = False
                else:
                    print(f"   ✅ Variable matches expected list")
            else:
                # Single variable test
                if pattern.get('retain_var') != test.get('expected_var'):
                    print(f"   ❌ Expected var '{test.get('expected_var')}', got '{pattern.get('retain_var')}'")
                    all_checks_passed = False
                else:
                    print(f"   ✅ Variable matches")

                if pattern.get('accum_source') != test.get('expected_source'):
                    print(f"   ❌ Expected source '{test.get('expected_source')}', got '{pattern.get('accum_source')}'")
                    all_checks_passed = False
                else:
                    print(f"   ✅ Source matches")

        # Check for carry_forward patterns
        elif test['expected_type'] == 'carry_forward':
            if pattern.get('retain_var') != test.get('expected_var'):
                print(f"   ❌ Expected var '{test.get('expected_var')}', got '{pattern.get('retain_var')}'")
                all_checks_passed = False
            else:
                print(f"   ✅ Variable matches")

            if pattern.get('source_var') != test.get('expected_source'):
                print(f"   ❌ Expected source '{test.get('expected_source')}', got '{pattern.get('source_var')}'")
                all_checks_passed = False
            else:
                print(f"   ✅ Source variable matches")

        print(f"   • Partition by: {pattern.get('partition_by', 'N/A')}")
        print(f"   • Order by: {pattern.get('order_by', 'N/A')}")

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
    print("\nThe enhanced RETAIN translator now supports:")
    print("  ✅ Single variable running sum")
    print("  ✅ Multiple variables running sum")
    print("  ✅ Carry-forward pattern (last non-missing value)")
    print("\nGaps closed: 2 (multiple vars + carry-forward)")
    sys.exit(0)
else:
    print("\n⚠️ SOME TESTS FAILED")
    print("Review the output above for details.")
    sys.exit(1)
