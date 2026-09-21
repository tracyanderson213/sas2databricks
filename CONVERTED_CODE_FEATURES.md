# SAS to Databricks Converter - Technical Reference

**Complete guide: How the converter works, how to use it, and what it produces**

---

## Powered by sas2databricks

This converter is built on **[sas2databricks](https://github.com/navintkr/sas2databricks)** — an open-source, LLM-assisted migration toolkit that converts SAS analytics, data transformations, and reports into Databricks (PySpark, Spark SQL, Delta Live Tables, and Workflows) end-to-end.

**Key capabilities:**
- Converts SAS code to Python/PySpark and SQL
- Generates Spark Declarative Pipelines (SDP) / Delta Live Tables (DLT)
- Handles complex SAS patterns (MERGE, RETAIN, PROC FORMAT, nested logic)
- LLM-assisted for intelligent pattern recognition
- Extensible and customizable for enterprise needs

**Our enhancements:**
- 13 automatic bug fixes integrated into the conversion flow
- Medallion architecture enforcement (Bronze/Silver/Gold)
- DAB-ready output with pipeline YAML generation
- Parameter-driven configuration for multi-environment deployment
- Enhanced documentation and metadata generation

---

## Quick Start for Developers

**Convert SAS to production-ready Databricks pipelines in 5 steps:**

1. **Drop SAS file into staging volume**
   - Upload your `.sas` file to `/Volumes/catalog/sas2dbx_migrate/staging/`
   - Example: `claims_adjudication.sas`

2. **Run the converter pipeline**
   - Execute: `databricks bundle run -t dev sas_dbx_code_translator`
   - Converter analyzes SAS code and generates Python/SQL

3. **Converted file created in output folder**
   - Find output in `/Volumes/catalog/sas2dbx_migrate/converted/`
   - Example: `transformed_claims_adjudication.py`
   - Includes: Medallion layers, audit columns, expectations (commented)

4. **Clone template pipeline and upload converted file**
   - Clone DAB pipeline template for your use case
   - Upload converted file to `transformations/` folder in pipeline directory
   - Update `databricks.yml` to reference your pipeline

5. **Review, debug, and test**
   - Review business logic against original SAS
   - Uncomment and validate data quality expectations
   - Test with sample data before production deployment
   - Run: `databricks pipelines start --pipeline-name your_pipeline`
   - **Note:** Silver layer objects appear as VIEWS in Unity Catalog (by design for storage optimization)

**Time:** 2-5 minutes (vs. 40-60 hours manual migration)

**Example output for claims adjudication:**
- Bronze: 4 tables (work_members, work_providers, work_benefit_plans, work_claims_in)
- Silver: 6 views (work_claims_elig, work_claims_elig2, work_claims_network, etc.)
- Gold: 2 tables (clm_claims_adjudicated, result)

**Where to find created tables/views:**
- Schema naming: `sas_{developer_id}_{layer}` (e.g., `sas_tanderson_silver`)
- **Not:** `sas_dbx_{full_name}_{layer}` ← common mistake!
- Check: `SHOW TABLES IN na-dbxtraining.sas_tanderson_silver;`

**Full guide:** See [docs/technical/AUTOMATED_WORKFLOW_GUIDE.md](docs/technical/AUTOMATED_WORKFLOW_GUIDE.md)

---

## Pre-Release Developer Checklist

**Critical review areas before deploying converted code to production:**

### 1. **Business Logic Validation**
- [ ] Compare converted code against original SAS line-by-line
- [ ] Verify all IF/THEN/ELSE conditions translate correctly
- [ ] Check calculation formulas (especially compound expressions)
- [ ] Validate aggregations (SUM, MEAN, COUNT) match SAS output
- [ ] Test edge cases (NULL handling, division by zero, date boundaries)

### 2. **Data Quality Expectations**
- [ ] Review all commented-out `# @dlt.expect_*()` decorators
- [ ] Enable expectations selectively based on business requirements
- [ ] Test expectations with known bad data to verify they trigger
- [ ] Choose appropriate action: `expect_or_drop`, `expect_or_fail`, or `expect`
- [ ] Add custom expectations for business-specific rules not in SAS

### 3. **Join Logic & Cardinality**
- [ ] Verify join types (inner vs. left vs. right vs. full)
- [ ] Check join keys are correct (especially multi-column keys)
- [ ] Test for unexpected row duplication (1:many joins)
- [ ] Validate NULL behavior in joins matches SAS MERGE logic
- [ ] Review IN= variable logic converted to proper join predicates

### 4. **NULL Handling**
- [ ] Verify `missing()` conversions use `.isNull()` correctly
- [ ] Check COALESCE/NVL for default values
- [ ] Test NULL propagation in calculations
- [ ] Validate NULL in GROUP BY produces correct results
- [ ] Review `otherwise(None)` vs `otherwise("")` vs `otherwise(0)`

### 5. **Data Types & Precision**
- [ ] Spot-check INT vs DOUBLE conversions
- [ ] Verify DATE format strings are correct
- [ ] Test numeric precision (especially currency calculations)
- [ ] Check for silent type casting issues
- [ ] Validate string truncation doesn't lose data

### 6. **Performance & Optimization**
- [ ] Review view vs. table decisions (enable views for large intermediate steps?)
- [ ] Check if expensive operations (windows, cross-joins) should be materialized
- [ ] Validate z-order columns match actual query patterns
- [ ] Test with production data volumes (not just sample data)
- [ ] Review partition strategy (bronze_ingestion_date appropriate?)

### 7. **Parameters & Configuration**
- [ ] Verify catalog and schema names for target environment
- [ ] Check `enable_views` setting matches requirements
- [ ] Update any hardcoded values to parameters
- [ ] Test with dev/test/prod configuration values
- [ ] Validate connection strings and credential references

### 8. **Incremental vs Full Reload**
- [ ] Determine if table should be full reload or incremental
- [ ] If incremental: Identify primary key column(s)
- [ ] If incremental: Identify sequence/timestamp column
- [ ] Add `@dlt.apply_changes()` if upgrading to CDC
- [ ] Test incremental logic with overlapping data

### 9. **Dependencies & Ordering**
- [ ] Review dependency graph for correctness
- [ ] Verify upstream tables exist before downstream consumption
- [ ] Check for circular dependencies
- [ ] Validate external table references (if any)
- [ ] Test pipeline with empty upstream tables

### 10. **Error Handling**
- [ ] Add try/catch for risky operations (if applicable)
- [ ] Review what happens on pipeline failure (retry? skip? fail?)
- [ ] Test recovery from partial failures
- [ ] Validate error messages are actionable
- [ ] Check logging captures enough detail for debugging

### 11. **Security & Governance**
- [ ] Remove any hardcoded credentials or sensitive data
- [ ] Verify table access permissions are correct
- [ ] Check PII/sensitive columns need masking
- [ ] Validate Unity Catalog grants are in place
- [ ] Review audit trail completeness

### 12. **Documentation**
- [ ] Update function docstrings with business context
- [ ] Document any manual changes made post-conversion
- [ ] Note any known differences from SAS behavior
- [ ] Update parameter descriptions
- [ ] Add troubleshooting notes for common issues

---

## Testing Strategy

**Before production release:**

1. **Unit test with sample data** (10-100 rows)
   - Validate logic with known inputs/outputs
   - Test all code paths (IF/THEN branches)
   
2. **Integration test with representative data** (1,000-10,000 rows)
   - Test joins produce correct cardinality
   - Validate aggregations match expectations
   
3. **Volume test with production-sized data** (full table size)
   - Verify performance is acceptable
   - Check memory/compute doesn't exceed limits
   
4. **Comparison test against SAS output**
   - Run same input through SAS and Databricks
   - Compare outputs (should match 100% or document diffs)
   - Investigate any discrepancies (type precision, NULL handling, etc.)

5. **Failure scenario testing**
   - Test with missing upstream tables
   - Test with schema changes in source
   - Test with bad data that triggers expectations
   - Verify graceful degradation

---

## Common Troubleshooting

**"I don't see any Silver/Gold tables!"**
- ✅ Check you're looking at the correct schema name
- Schema pattern: `sas_{developer_id}_{layer}` (e.g., `sas_tanderson_silver`)
- Common mistake: Looking at `sas_dbx_tracy_anderson_silver` instead of `sas_tanderson_silver`
- Silver objects appear as **VIEWS**, not tables (by design)
- Verify: `SHOW TABLES IN na-dbxtraining.sas_tanderson_silver;`

**"Tables are empty after pipeline runs"**
- Check upstream Bronze tables have data: `SELECT COUNT(*) FROM bronze.table_name;`
- Verify pipeline completed successfully (no failures in any stage)
- Check data quality expectations didn't drop all rows
- Review Bronze layer audit columns: `bronze_ingestion_timestamp` should be recent

**"Joins produce no results"**
- Verify join keys have matching values in both tables
- Check for NULL values in join columns (SAS MERGE handles NULLs differently)
- Review join type (inner vs left) matches SAS behavior
- Test with small sample: `SELECT * FROM table1 a JOIN table2 b ON a.key = b.key LIMIT 10;`

**"Converted code has syntax errors"**
- Review function names for Python reserved keywords (if, for, in, etc.)
- Check for unclosed parentheses in complex expressions
- Verify all `F.col()` references use correct column names
- Test each function independently before full pipeline run

**"Performance is slow"**
- Check if expensive operations (window functions) should be materialized
- Review z-order columns match actual query patterns
- Consider enabling more views (less storage, but recompute on read)
- Profile with Databricks query history to identify bottlenecks

---

## Technical Features of Converted Code (12 Key Features)

**What's in the generated Python files:**

---

## 1. Parameter-Driven Configuration
- All environment-specific values externalized as parameters
- No hardcoded catalog/schema names
- Same code works in all environments (dev/test/prod)
- Configuration visible in pipeline logs
- Easy to override via pipeline config (databricks.yml)
- Deploy to multiple environments with zero code changes

## 2. Comprehensive Headers & Metadata
- Every file has rich metadata for logging, auditing, and history tracking
- **Conversion timestamp** — Audit trail for when transformation occurred
- **Original file reference** — Traceability back to source SAS file
- **Converter version** — Reproducibility (which version produced this)
- **Bug fixes applied** — Transparency (13 automatic fixes documented)
- **Layer breakdown** — Architecture overview (Bronze/Silver/Gold counts)
- **Business purpose** — Original SAS intent preserved
- **Dependencies** — Input/output tables documented for impact analysis

## 3. Medallion Architecture Implementation
- Automatic three-layer separation with clear naming conventions
- **Bronze Layer** — Raw data tables
  - Always materialized (`@dp.table()` or `@dp.materialized_view()`)
  - Layer name in table definition (`bronze.work_members`)
  - Descriptive comments for each table
  - Table properties include optimization hints (z-order, CDC enabled)
  - Standard audit columns added automatically (4 columns)
  - Source of truth for all downstream transformations
- **Silver Layer** — Business logic transformations
  - Primarily views (`@dp.view()` or `@dp.materialized_view()`) for storage optimization
  - **Important:** Silver objects appear as VIEWS in catalog, not tables (by design)
  - References original SAS line numbers for traceability
  - Business logic documented in function docstrings
  - Proper JOIN syntax (converted from SAS MERGE)
  - Explicit column selection (no SELECT *)
  - Intermediate steps don't incur storage costs
  - Heavy transformations use `@dp.materialized_view()` for performance
  - Exception: Very expensive operations (window functions) may use `@dp.table()`
- **Gold Layer** — Analytics-ready tables
  - Use `@dp.materialized_view()` for read-only analytics (recommended)
  - Or `@dp.table()` if INSERT/UPDATE/DELETE operations needed
  - Optimization hints for query performance (z-order on common keys)
  - Clear business purpose documented
  - Output schema explicitly documented
  - Designed for BI tools and reporting

## 4. Modern SDP Syntax (Not Legacy DLT)
- Uses Spark Declarative Pipelines syntax, not old Delta Live Tables patterns
- **Modern SDP decorators (target state):**
  - `@dp.table()` — Full Delta table with INSERT/UPDATE/DELETE support
  - `@dp.materialized_view()` — Read-only materialized (best for analytics)
  - `@dp.view()` — Logical view (no storage, computed on read)
  - `@dp.streaming_table()` — For streaming data sources
  - Import: `import databricks.sdk.service.pipelines as dp`
- **Converter outputs `dlt` syntax for maximum compatibility:**
  - `@dlt.table()` / `@dlt.view()` decorators (works everywhere)
  - Functionally equivalent to `@dp.table()` / `@dp.view()` on modern Databricks
  - Can be upgraded to `@dp.materialized_view()` for read-only Gold tables
  - Import: `import dlt`
- **Key modern patterns:**
  - Uses `dlt.read()` or `dp.read()` for dependencies (not `spark.read.table()`)
  - Explicit table naming with `name=` parameter
  - Forward-compatible with SDP evolution
  - Automatic dependency resolution from read calls
- **Migration path:** Converter output (`@dlt.*`) → Upgrade to modern decorators (`@dp.materialized_view`) → Enhanced performance

## 5. Standard Audit Columns
- Every Bronze table gets 4 standard metadata columns added automatically
- **bronze_ingestion_timestamp** (TimestampType)
  - Exact ingestion time for debugging and SLA tracking
  - Example: `2024-09-21 14:30:45.123456`
- **bronze_source_file** (StringType)
  - Original SAS filename for traceability
  - Example: `claims_adjudication.sas`
- **bronze_ingestion_date** (DateType)
  - Partition key for query optimization
  - Enables partition pruning (100x faster queries)
  - Example: `2024-09-21`
- **medallion_layer** (StringType)
  - Current layer identifier for multi-layer queries
  - Example: `bronze`
- **Benefits:**
  - Compliance: Prove when data arrived
  - Debugging: Query specific load batches
  - Performance: Partition pruning saves query costs
  - Lineage: Trace data back to source file

## 6. Intelligent View vs Table Determination
- Converter automatically decides VIEW (storage-free) vs TABLE (materialized)
- **Decision logic (Modern SDP decorators):**
  - **Bronze Layer** → `@dp.table()` or `@dp.materialized_view()` (durable storage, source of truth)
  - **Silver Layer** → `@dp.view()` by default (intermediate transformations, no storage cost)
  - **Silver Layer exception** → `@dp.materialized_view()` if expensive transformation or reused multiple times
  - **Gold Layer** → `@dp.table()` or `@dp.materialized_view()` (analytics queries expect fast reads)
- **Modern SDP decorator options:**
  - `@dp.table()` — Full Delta table (INSERT/UPDATE/DELETE support)
  - `@dp.materialized_view()` — Read-only materialized (optimized for analytics)
  - `@dp.view()` — Logical view (no storage, computed on read)
  - `@dp.streaming_table()` — For streaming sources
- **Converter output (for compatibility):**
  - Uses `@dlt.table()` / `@dlt.view()` syntax
  - Equivalent to `@dp.table()` / `@dp.view()` on modern Databricks
  - Can be upgraded to `@dp.materialized_view()` for read-only analytics tables
- **Configuration override:**
  - `enable_views` parameter allows materializing everything for dev/testing
  - Controllable via pipeline configuration
- **Benefits:**
  - Storage savings: 40-60% reduction (intermediate views not stored)
  - Performance: Gold tables materialized for fast queries
  - Flexibility: Override via parameter when needed
  - Smart defaults: Expensive operations (window functions) get materialized

## 7. Proper Type Handling
- Automatic INT vs DOUBLE detection from SAS code
- Proper DATE conversion (STRING → DATE with correct format)
- **SAS → Spark type mapping:**
  - `LENGTH var 8;` (no decimals) → `IntegerType()`
  - `var = 123.45;` (has decimals) → `DoubleType()`
  - `var = '2024-09-21';` → `StringType()` then `to_date()`
  - `var = 'text';` → `StringType()`
  - `IF missing(var)` → `isNull()` checks
- **Benefits:**
  - Aggregations work correctly (no "can't sum strings" errors)
  - Joins on proper types run faster
  - Storage optimized (INT uses less space than DOUBLE/STRING)
  - No silent casting errors

## 8. Complex SAS Pattern Handling
- Automatic conversion of advanced SAS patterns to Spark equivalents
- **Pattern 1: MERGE → JOIN**
  - Converts SAS MERGE with BY statement to appropriate Spark JOIN
  - Determines join type from IN= logic (inner, left, right, full)
  - Preserves join keys and conditions
- **Pattern 2: RETAIN → Window Functions**
  - Converts SAS RETAIN logic to Spark window functions
  - Handles running totals and cumulative calculations
  - Properly partitions and orders windows
  - Auto-generates FIRST./LAST. logic with window functions
- **Pattern 3: Nested IF/THEN/ELSE → CASE**
  - Collapses nested IF/THEN/ELSE into single CASE expression
  - Prevents duplicate column errors (common manual migration bug)
  - Proper NULL handling with `otherwise(None)`
  - Readable single expression
  - Optimized for single-pass execution
- **Benefits:**
  - Handles patterns that break manual migrations
  - Optimized Spark code (not literal SAS translation)
  - Prevents common errors (duplicate columns, wrong join types)
  - Maintainable output code

## 9. Dependency Documentation
- Clear documentation of table dependencies in generated code
- **Visual dependency graph** included as markdown comment
  - Shows all Bronze layer source tables
  - Shows Silver layer transformations with upstream dependencies
  - Shows Gold layer analytics tables with lineage
  - Uses tree structure with arrows showing data flow
- **Benefits:**
  - Visual dependency graph for understanding data flow
  - Impact analysis: See which tables break if source changes
  - Optimization opportunities: Identify independent branches for parallelization
  - Onboarding: New team members understand flow quickly

## 10. Error Handling & Validation
- Built-in data quality checks using SDP expectations
- **Expectations generated but commented out for manual review:**
  - Converter analyzes SAS business logic and generates suggested expectations
  - All expectations commented out with `#` prefix for safety
  - User reviews and enables selectively based on business requirements
  - Example: `# @dlt.expect_or_drop("positive_amounts", "amount > 0")`
- **Modern SDP validation decorators:**
  - `@dp.expect_or_drop()` — Drop invalid rows, log to `_dlt_expectations`
  - `@dp.expect_or_fail()` — Fail pipeline on validation error
  - `@dp.expect()` — Log violation but allow row through
  - `@dp.expect_all()` — Multiple expectations in one decorator
- **Common patterns generated:**
  - Primary keys: `member_id IS NOT NULL`
  - Positive amounts: `claim_amount > 0`
  - Valid dates: `service_date >= '2020-01-01'`
  - Enum values: `status IN ('active', 'pending', 'closed')`
  - Range checks: `amount BETWEEN 0 AND 1000000`
- **Benefits:**
  - Bad data caught at ingestion (not in downstream reports)
  - Automatic logging of dropped rows for auditing
  - Configurable validation levels (warn, drop, or fail)
  - Quality metrics tracked automatically
  - Manual review prevents overly aggressive validation

## 11. Comments Preserved from SAS
- Business logic comments carried forward from original SAS code
- **Docstring content includes:**
  - Original SAS comments explaining business purpose
  - Business owner identification
  - Update frequency
  - Downstream consumers
  - References to original SAS file and line numbers
- **Benefits:**
  - Business context preserved (no knowledge loss)
  - Ownership clearly documented
  - Usage and dependencies documented
  - Eliminates "tribal knowledge" problem
  - Easier audits and compliance reviews

## 12. Incremental & Full Reload Support
- Architecture supports both incremental and full reload ingestion patterns
- **Full Reload (Batch) Pattern:**
  - Default converter output — replaces entire table on each run
  - Bronze layer: `@dp.table()` with full table replacement
  - Best for: Small tables, dimension tables, daily SAS batch jobs
  - Simple and deterministic — what you see is what you get
- **Incremental (CDC) Pattern:**
  - Bronze tables include CDC enablement: `delta.enableChangeDataFeed: true`
  - Use `@dlt.apply_changes()` for merge/upsert logic
  - Requires: Primary key column(s) and sequence/timestamp column
  - Best for: Large fact tables, event streams, frequently updated data
- **Audit columns support both patterns:**
  - `bronze_ingestion_timestamp` — Track when record arrived (for any pattern)
  - `bronze_ingestion_date` — Partition key for incremental queries
  - Query only new data: `WHERE bronze_ingestion_date >= '2024-09-20'`
- **Migration path:**
  - **Start with full reload** — Converter default, simple to validate
  - **Add incremental later** — Upgrade Bronze tables with `@dlt.apply_changes()` when needed
  - **No Silver/Gold changes** — Downstream layers work with either pattern
- **Example: Full Reload → Incremental upgrade:**
  ```python
  # Converter output (Full Reload):
  @dp.table(name="bronze.claims")
  def bronze_claims():
      return df  # Full table replacement
  
  # Upgraded to Incremental (CDC):
  @dp.table(name="bronze.claims")
  @dlt.apply_changes(
      target="bronze.claims",
      source="staging.claims_cdc",
      keys=["claim_id"],
      sequence_by="updated_timestamp"
  )
  def bronze_claims():
      return spark.readStream.table("staging.claims_cdc")
  ```
- **Benefits:**
  - Flexibility: Choose pattern based on data characteristics
  - Start simple: Full reload for validation, incremental for scale
  - Cost optimization: Incremental processing = 90%+ cost reduction for large tables
  - Future-proof: CDC enablement in Bronze tables from day one

---

## Summary: Production-Ready Features

| Feature | Benefit |
|---------|---------|
| **Parameters** | Deploy to any environment without code changes |
| **Headers** | Audit trail and traceability |
| **Medallion** | Clear architecture and data lineage |
| **Modern SDP syntax** | Forward-compatible with platform evolution |
| **Audit columns** | Compliance and debugging support |
| **Intelligent views** | 40-60% storage savings |
| **Proper types** | Correct aggregations, no silent errors |
| **Complex patterns** | MERGE/RETAIN/nested IF handled automatically |
| **Dependencies** | Visual graph for impact analysis |
| **Data quality** | Bad data caught at ingestion |
| **Preserved comments** | Knowledge retention and documentation |
| **Incremental & Full Reload** | Flexibility: Start simple, scale to incremental when needed |

---

**The converter produces enterprise-grade code with best practices built in — not just syntax translation.** 🚀
