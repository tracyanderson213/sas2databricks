# Test Suite for SAS to Databricks Converter

**Comprehensive pytest suite** that validates `sas_dbx.py` functionality outside of Databricks.

---

## Quick Start

```bash
# Install dependencies
pip install pytest

# Run all tests
pytest -v

# Run from project root
cd /path/to/sas2databricks
pytest tests/ -v
```

---

## Test Results (Baseline)

**18 PASSED** — Regression tests (existing functionality)  
**10 XFAILED** — Gap tests (known limitations, expected to fail)

```
==================== 18 passed, 10 xfailed in 2.5s ====================
```

---

## Test Categories

### ✅ Regression Tests (18 tests)

**Purpose:** Verify patterns the converter already handles correctly.

**Categories:**
- MERGE translation (2 tests)
- RETAIN translation (1 test)
- DATALINES parsing (1 test)
- PROC FORMAT extraction (1 test)
- Medallion layer detection (8 tests)
- View vs table detection (4 tests)
- Robustness (1 test)

**Status:** Should always pass. If one fails, something broke.

---

### ⚠️ Gap Tests (10 tests, marked `xfail`)

**Purpose:** Document known limitations identified in code review.

**Categories:**
1. **RETAIN gaps** (2 tests)
   - Multiple variables in one statement
   - Carry-forward pattern (no arithmetic)

2. **MERGE gaps** (2 tests)
   - 3+ table join logic
   - Filter IF not first statement

3. **LIBNAME normalization** (1 test)
   - Custom library names (edw, stg, elig)

4. **DATALINES parsing** (1 test)
   - Embedded spaces, missing-value markers

5. **PROC FORMAT** (1 test)
   - Numeric ranges (low-17, 18-64)

6. **FIRST./LAST. detection** (1 test)
   - Duplicate detection pattern

7. **Nested IF → CASE WHEN** (1 test)
   - Multi-level branching consolidation

8. **Macro detection** (1 test)
   - %macro/%mend flagging

**Status:** Marked `xfail(strict=False)` — "expected failure," not a build breaker.

**When you fix a gap:** Test flips to `XPASS` (unexpected pass) — a clear signal you closed the gap!

---

## Running Tests

### Run All Tests
```bash
pytest -v
```

### Run Only Regression Tests
```bash
pytest -v -m "not gap"
```

### Run Only Gap Tests
```bash
pytest -v -m gap
```

### Run Specific Test Class
```bash
pytest -v tests/test_sas_dbx_converter.py::TestMergeRegression
```

### Run Specific Test
```bash
pytest -v tests/test_sas_dbx_converter.py::TestMergeRegression::test_simple_left_join_detected
```

### Show Test Output (even on pass)
```bash
pytest -v -s
```

### Stop on First Failure
```bash
pytest -v -x
```

---

## How It Works

### Mock Harness (conftest.py)

**Problem:** `sas_dbx.py` is a Databricks notebook that depends on:
- `dbutils` (runtime-injected global, never imported)
- `sas2databricks` package

**Solution:** `conftest.py` stubs both so the notebook loads as a plain Python module.

**What it mocks:**
- `dbutils.widgets.text()`, `dbutils.widgets.dropdown()`, `dbutils.widgets.get()`
- `dbutils.fs.mkdirs()`
- `dbutils.library.restartPython()`
- `dbutils.notebook.exit()`
- `sas2databricks.migrate()`

**What it doesn't mock:** The actual conversion logic! Tests call the real functions from `sas_dbx.py`.

---

### Test Structure

```python
class TestMergeRegression:
    def test_simple_left_join_detected(self, sas_dbx_module):
        sas = """
        data work.claims_elig;
            merge work.claims_in (in=inclaim) work.members (in=inmember);
            by member_id;
            if inclaim;
        run;
        """
        result = sas_dbx_module.translate_merge_to_join(sas, "")
        assert len(result) == 1
        assert result[0]["join_type"] == "left"
```

**Key points:**
- `sas_dbx_module` fixture loads the real `sas_dbx.py`
- Tests call actual functions (`translate_merge_to_join`)
- Assertions verify expected behavior

---

## Fixing Gaps (Workflow)

### 1. Pick a Gap Test
```bash
# See all gaps
pytest -v -m gap

# Pick one, e.g., FIRST./LAST. detection
```

### 2. Implement the Fix
Edit `src/converter/sas_to_dbx_pipeline_converter.py` to add the missing functionality.

### 3. Run the Gap Test
```bash
pytest -v tests/test_sas_dbx_converter.py::TestFirstLastGaps::test_first_last_translator_exists
```

**Expected:** Test flips from `XFAIL` to `XPASS` (unexpected pass)

### 4. Expand the Test
Once the basic function exists, expand the test with real assertions:

```python
@pytest.mark.gap  # Remove this marker once fully implemented
def test_first_last_translator(self, sas_dbx_module):
    sas = """
    data work.dedup;
        set work.claims;
        by member_id;
        if first.member_id;
    run;
    """
    result = sas_dbx_module.translate_first_last_to_window(sas)
    assert len(result) == 1
    assert result[0]["partition_by"] == "member_id"
    assert result[0]["window_func"] == "ROW_NUMBER"
```

### 5. Remove `@gap` Marker
Once fully working, remove the `@gap(...)` decorator so it becomes a normal enforced test.

### 6. Run All Tests
```bash
pytest -v
```

**Expected:** 19 passed, 9 xfailed (gap closed!)

---

## File Locations

### Option 1: Tests in `tests/` Directory (Recommended)
```
sas2databricks/
├── src/
│   └── converter/
│       └── sas_dbx.py
├── tests/
│   ├── conftest.py              ← Mock harness
│   ├── test_sas_dbx_converter.py ← Test suite
│   └── README.md                 ← This file
```

**Run:** `pytest tests/ -v`

### Option 2: Tests Alongside sas_dbx.py
```
sas2databricks/
├── src/
│   └── converter/
│       ├── sas_dbx.py
│       ├── conftest.py
│       └── test_sas_dbx_converter.py
```

**Run:** `pytest src/converter/ -v`

### Option 3: Custom Location (Use Environment Variable)
```bash
export SAS_DBX_PATH=/custom/path/to/sas_dbx.py
pytest /anywhere/tests/ -v
```

---

## Dependencies

**Required:**
- `pytest` — Test framework

**Optional:**
- `pytest-xdist` — Run tests in parallel: `pytest -v -n auto`
- `pytest-cov` — Code coverage: `pytest --cov=src/converter --cov-report=html`

**Install all:**
```bash
pip install pytest pytest-xdist pytest-cov
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Converter

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install pytest
      - run: pytest tests/ -v
```

**Build status badges:**
- ✅ 18 passed, 10 xfailed — Baseline
- ✅ 19 passed, 9 xfailed — Gap closed!
- ❌ 17 passed, 1 failed, 10 xfailed — Regression!

---

## Adding New Tests

### Regression Test (Should Always Pass)

```python
class TestMyFeatureRegression:
    def test_my_pattern_works(self, sas_dbx_module):
        sas = """
        /* Your SAS code here */
        """
        result = sas_dbx_module.my_translator_function(sas)
        assert len(result) == 1
        assert result[0]["expected_key"] == "expected_value"
```

### Gap Test (Known Limitation)

```python
class TestMyFeatureGaps:
    @gap("Description of why this doesn't work yet")
    @pytest.mark.gap
    def test_edge_case_not_handled(self, sas_dbx_module):
        sas = """
        /* Edge case SAS code */
        """
        result = sas_dbx_module.my_translator_function(sas)
        # Assertion that WILL fail today but SHOULD pass once fixed
        assert result[0]["handles_edge_case"] == True
```

---

## Troubleshooting

### Test Discovery Issues

**Problem:** `pytest` can't find tests

**Solution:** Run from project root:
```bash
cd /path/to/sas2databricks
pytest tests/ -v
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'sas_dbx_converter'`

**Solution:** Check `SAS_DBX_PATH` or move files:
```bash
export SAS_DBX_PATH=/path/to/sas_dbx.py
pytest -v
```

### sas_dbx.py Not Found

**Problem:** `sas_dbx.py not found at /path/...`

**Solution:** Place files in same directory or set environment variable:
```bash
# Option 1: Place alongside tests
cp src/converter/sas_to_dbx_pipeline_converter.py tests/

# Option 2: Set environment variable
export SAS_DBX_PATH=src/converter/sas_to_dbx_pipeline_converter.py
```

---

## References

- **Code Review Findings:** `../CONVERTER_REVIEW_FINDINGS.md`
- **Coverage Matrix:** `../CONVERTER_STATUS.md`
- **Original 5 Fixes:** `../GENIE_FIXES_APPLIED.md`
- **Converter Source:** `../src/converter/sas_to_dbx_pipeline_converter.py`

---

## Status

**Current:** 18 passed, 10 xfailed (baseline)  
**Target:** 28 passed, 0 xfailed (all gaps closed)  
**Progress:** 64% complete

**Next Gap to Close:** FIRST./LAST. detection (most common pattern in claims processing)

---

**Last Updated:** 2026-09-22  
**Test Suite Version:** 1.0  
**Converter Version:** With 5 Genie fixes applied
