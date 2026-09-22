# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# dependencies = [
#   "sas2databricks",
# ]
# ///
# MAGIC %md
# MAGIC # 03 - Convert SAS to Spark Declarative Pipelines
# MAGIC
# MAGIC **Purpose:** Convert SAS files to production-ready Spark Declarative Pipeline (SDP) code with intelligent layer detection and view optimization
# MAGIC
# MAGIC **Prerequisites:**
# MAGIC - ✅ Create schemas and volume (see MANUAL_UPLOAD_GUIDE.md)
# MAGIC - ✅ Upload SAS files to `staging/` folder
# MAGIC
# MAGIC **Features:**
# MAGIC 1. ✅ **Automatic layer detection** (Bronze/Silver/Gold based on table patterns)
# MAGIC 2. ✅ **Three schema variables** (SCHEMA_BRONZE, SCHEMA_SILVER, SCHEMA_GOLD)
# MAGIC 3. ✅ **View optimization** (intermediate tables → @dlt.view instead of @dlt.table)
# MAGIC 4. ✅ **Widget support** for runtime configuration
# MAGIC 5. ✅ Production template with headers, params, bronze timestamps

# COMMAND ----------

# MAGIC %md
# MAGIC ## Widgets for Runtime Configuration

# COMMAND ----------

# Create widgets for schema configuration (can be set at runtime)
dbutils.widgets.text("catalog", "na-dbxtraining", "Catalog")
dbutils.widgets.text("schema_prefix", "sas", "Schema Prefix (creates sas_bronze, sas_silver, sas_gold)")
dbutils.widgets.dropdown("enable_views", "true", ["true", "false"], "Enable Views for Intermediate Tables")
dbutils.widgets.dropdown("api_style", "dp", ["dlt", "dp"], "API Style (dlt or dp)")

# Get widget values
CATALOG = dbutils.widgets.get("catalog")
SCHEMA_PREFIX = dbutils.widgets.get("schema_prefix")
ENABLE_VIEWS = dbutils.widgets.get("enable_views") == "true"
API_STYLE = dbutils.widgets.get("api_style")

# Build schema names from prefix
SCHEMA_BRONZE = f"{SCHEMA_PREFIX}_bronze"
SCHEMA_SILVER = f"{SCHEMA_PREFIX}_silver"
SCHEMA_GOLD = f"{SCHEMA_PREFIX}_gold"

print("="*80)
print("🎛️  CONFIGURATION FROM WIDGETS")
print("="*80)
print(f"Catalog:              {CATALOG}")
print(f"Schema Prefix:        {SCHEMA_PREFIX}")
print(f"Bronze Schema:        {SCHEMA_BRONZE}")
print(f"Silver Schema:        {SCHEMA_SILVER}")
print(f"Gold Schema:          {SCHEMA_GOLD}")
print(f"Enable Views:         {ENABLE_VIEWS}")
print(f"API Style:            {API_STYLE}")
print("="*80)
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install sas2databricks

# COMMAND ----------

# MAGIC %pip install sas2databricks

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import and Configure

# COMMAND ----------

from sas2databricks import migrate
from datetime import datetime
import os
import re
import shutil

# Re-load widget values after Python restart
CATALOG = dbutils.widgets.get("catalog")
SCHEMA_PREFIX = dbutils.widgets.get("schema_prefix")
ENABLE_VIEWS = dbutils.widgets.get("enable_views") == "true"
API_STYLE = dbutils.widgets.get("api_style")

# Build schema names from prefix
SCHEMA_BRONZE = f"{SCHEMA_PREFIX}_bronze"
SCHEMA_SILVER = f"{SCHEMA_PREFIX}_silver"
SCHEMA_GOLD = f"{SCHEMA_PREFIX}_gold"

# Base paths - dynamic based on catalog
volume_base = f"/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration"
input_base = f"{volume_base}/staging"              # SAS source files
output_dir = f"{volume_base}/converted"            # Conversion output

# Ensure output directory exists
dbutils.fs.mkdirs(output_dir)

print("✅ sas2databricks imported successfully")
print(f"📁 Input (staging):   {input_base}")
print(f"📁 Output (converted): {output_dir}")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Intelligent Layer Detection

# COMMAND ----------

def detect_medallion_layer(table_name, sas_code, converted_code):
    """
    Detects whether a table should be Bronze, Silver, or Gold layer

    Args:
        table_name: Name of the table
        sas_code: Original SAS code
        converted_code: Converted Python code

    Returns:
        str: "bronze", "silver", or "gold"
    """
    table_lower = table_name.lower()

    # PRIORITY 1: Explicit naming conventions (highest confidence)
    if table_lower.startswith('bronze_') or table_lower.startswith('raw_'):
        return "bronze"
    if table_lower.startswith('gold_') or table_lower.startswith('final_'):
        return "gold"
    if table_lower.startswith('silver_'):
        return "silver"

    # PRIORITY 2: Output/final tables with library prefix (clm.*, lib.*)
    # In SAS, library.table (e.g. clm.claims_adjudicated) indicates final output
    if table_name.startswith('clm_') or '_adjudicated' in table_lower or '_final' in table_lower:
        # Check if it's aggregated/report (gold) or just final processing (gold)
        return "gold"

    # PRIORITY 3: Suffix patterns for gold
    if any(table_lower.endswith(x) for x in ['_summary', '_report', '_metrics', '_agg', '_total', '_rollup']):
        return "gold"

    # PRIORITY 4: Reference/lookup tables (formats, members, providers, plans)
    # These are typically loaded first with DATALINES and used for lookups
    if any(x in table_lower for x in ['fmt_', 'format_', '_fmt']) or \
       table_lower in ['members', 'providers', 'benefit_plans', 'plans'] or \
       table_lower.startswith('work_members') or table_lower.startswith('work_providers') or \
       table_lower.startswith('work_benefit'):
        return "bronze"

    # PRIORITY 5: Intermediate work tables (transformations, joins, enrichments)
    if table_lower.startswith('work_claims_') and not table_lower.startswith('work_claims_in'):
        # These are intermediate transformation steps in the pipeline
        return "silver"

    # PRIORITY 6: Input tables (work_claims_in, work_xxx_in)
    if '_in' in table_lower or table_lower.endswith('_input'):
        return "bronze"

    # PRIORITY 7: Sort operations and temp tables
    if 'sort' in table_lower or table_lower.startswith('sort_'):
        return "silver"  # Intermediate operation

    # PRIORITY 8: Aggregate operations (result, summary, report, running totals)
    if any(x in table_lower for x in ['result', '_running', 'running_']):
        return "gold"

    # DEFAULT: Silver (transformation layer)
    return "silver"

def detect_should_be_view(table_name, sas_code, converted_code):
    """
    Detects if a table should be a view (intermediate/temporary processing)

    Args:
        table_name: Name of the table
        sas_code: Original SAS code
        converted_code: Converted Python code

    Returns:
        bool: True if should be a view
    """
    table_lower = table_name.lower()

    # Definitely TABLE (must persist):
    # 1. Bronze layer - source data
    if table_lower.startswith('bronze_') or table_lower.startswith('raw_') or \
       table_lower in ['members', 'providers', 'benefit_plans', 'plans'] or \
       table_lower.startswith('work_members') or table_lower.startswith('work_providers') or \
       table_lower.startswith('work_benefit') or table_lower.startswith('work_claims_in'):
        return False  # Table

    # 2. Gold layer - final aggregations and reports
    if table_lower.startswith('gold_') or table_lower.startswith('final_') or \
       table_lower.startswith('clm_') or '_adjudicated' in table_lower or \
       any(table_lower.endswith(x) for x in ['_summary', '_report', '_metrics', '_final']):
        return False  # Table

    # 3. Tables with stateful processing (RETAIN, running totals)
    if '_running' in table_lower or 'running_' in table_lower:
        return False  # Table (needs RETAIN logic)

    # 4. Result tables (aggregation outputs)
    if table_lower == 'result' or table_lower.startswith('result_'):
        return False  # Table

    # 5. Format tables (reference data)
    if 'fmt_' in table_lower or 'format_' in table_lower or '_fmt' in table_lower:
        return False  # Table

    # Definitely VIEW (intermediate/temporary):
    # 1. Sort operations (just reordering, no persistence needed)
    if 'sort' in table_lower or table_lower.startswith('sort_'):
        return True  # View

    # 2. Intermediate work tables (transformations, joins)
    if table_lower.startswith('work_claims_') and \
       table_lower not in ['work_claims_in', 'work_claims_running']:
        # Examples: work_claims_elig, work_claims_network, work_claims_benefit, work_claims_dupflag
        return True  # View

    # 3. Explicit temp/staging suffixes
    if any(x in table_lower for x in ['_tmp', '_temp', '_intermediate', '_staging']):
        return True  # View

    # 4. Flag operations (simple transformations)
    if 'flag_' in table_lower or '_flag' in table_lower:
        return True  # View (or could be a UDF/macro)

    # DEFAULT: Table (safe default)
    return False

print("✅ Layer detection functions ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## API Style Converter (dlt → dp)

# COMMAND ----------

# DBTITLE 1,Cell 12 - Post-Processor with Bug Fixes
def post_process_converted_code(code, table_analysis, sas_source_text="", api_style="dlt", schema_bronze="bronze", schema_silver="silver", schema_gold="gold"):
    """
    Post-processes converted code to fix common sas2databricks issues

    Fixes:
    1. Replace 'FROM src' placeholder with proper source
    2. Remove duplicate function definitions (PROC SORT artifacts)
    3. Fix broken SQL patterns (MERGE syntax, format functions)
    4. Add warnings for manual review items
    5. Detect reference data for temporary view recommendations

    Args:
        code: Converted Python code from sas2databricks
        table_analysis: List of dicts with table info
        sas_source_text: Original SAS code for context

    Returns:
        Cleaned code with fixes and warnings
    """
    import re

    fixes_applied = []
    warnings = []

    # ==============================================================================
    # NORMALIZATION PASS: Extract patterns before semantic translation
    # ==============================================================================

    # PARSE DATALINES: Extract inline data from original SAS
    datalines_parsed = parse_sas_datalines(sas_source_text)

    if datalines_parsed:
        fixes_applied.append(f"Parsed {len(datalines_parsed)} DATALINES blocks from original SAS code")
        for table, info in datalines_parsed.items():
            fixes_applied.append(f"  • {table}: {info['row_count']} rows, {len(info['columns'])} columns")

    # EXTRACT PROC FORMATS: Parse format definitions
    proc_formats = extract_proc_formats(sas_source_text)

    if proc_formats:
        fixes_applied.append(f"Extracted {len(proc_formats)} PROC FORMAT definition(s)")
        for fmt_name, fmt_info in proc_formats.items():
            fixes_applied.append(f"  • {fmt_name}: {len(fmt_info['mappings'])} mappings")

    # ==============================================================================
    # SEMANTIC TRANSLATION PASS: Detect and translate complex patterns
    # ==============================================================================

    # DETECT MERGE patterns
    merge_patterns = translate_merge_to_join(sas_source_text, code)

    if merge_patterns:
        fixes_applied.append(f"Detected {len(merge_patterns)} DATA step MERGE pattern(s)")
        for pattern in merge_patterns:
            table_count = len(pattern['tables'])
            fixes_applied.append(f"  • {pattern['output_table']}: {pattern['join_type'].upper()} JOIN ({table_count} tables) on {pattern['by_vars']}")

    # DETECT RETAIN patterns
    retain_patterns = translate_retain_to_window(sas_source_text)

    if retain_patterns:
        running_sum_count = sum(1 for p in retain_patterns if p.get('pattern_type') == 'running_sum')
        carry_forward_count = sum(1 for p in retain_patterns if p.get('pattern_type') == 'carry_forward')

        if running_sum_count > 0 and carry_forward_count > 0:
            fixes_applied.append(f"Detected {len(retain_patterns)} RETAIN pattern(s): {running_sum_count} running sum, {carry_forward_count} carry-forward")
        elif running_sum_count > 0:
            fixes_applied.append(f"Detected {running_sum_count} RETAIN pattern(s) for running totals")
        else:
            fixes_applied.append(f"Detected {carry_forward_count} RETAIN pattern(s) for carry-forward")

        for pattern in retain_patterns:
            if pattern.get('pattern_type') == 'running_sum':
                fixes_applied.append(f"  • {pattern['output_table']}: {pattern['retain_var']} accumulates {pattern.get('accum_source', 'N/A')}")
            elif pattern.get('pattern_type') == 'carry_forward':
                fixes_applied.append(f"  • {pattern['output_table']}: {pattern['retain_var']} carries forward from {pattern.get('source_var', 'N/A')}")
            else:
                # Fallback for legacy patterns
                fixes_applied.append(f"  • {pattern['output_table']}: {pattern['retain_var']}")

    # DETECT FIRST./LAST. patterns (duplicate detection)
    first_last_patterns = translate_first_last_to_window(sas_source_text)

    if first_last_patterns:
        fixes_applied.append(f"Detected {len(first_last_patterns)} FIRST./LAST. pattern(s) for duplicate detection")
        for pattern in first_last_patterns:
            fixes_applied.append(f"  • {pattern['output_table']}: Keep {pattern['filter_type']} of {pattern['partition_by']}")

    # ==============================================================================
    # INSERT MISSING DATALINES TABLES (if sas2databricks skipped them) - BUG FIX #3
    # ==============================================================================
    missing_tables = []
    if datalines_parsed:
        for table_name, datalines_info in datalines_parsed.items():
            # Check if this table exists in the converted code
            if f'def {table_name}():' not in code:
                missing_tables.append(table_name)

                # Generate the complete function for this missing table
                # Use api_style from function parameter (already set from widget)
                decorator = "@dp.temporary_view" if api_style == "dp" else "@dlt.view"

                new_function = f"\n{decorator}(name='{schema_bronze}.{table_name}', comment='Auto-generated from SAS DATALINES')\n"
                new_function += f"def {table_name}():\n"
                new_function += generate_inline_dataframe_code(table_name, datalines_info)
                new_function += "\n"

                # Insert at the end of the imports section (before first function)
                first_func = re.search(r'^@d[lp]', code, re.MULTILINE)
                if first_func:
                    insert_pos = first_func.start()
                    code = code[:insert_pos] + new_function + "\n" + code[insert_pos:]
                    fixes_applied.append(f"Auto-generated MISSING table '{table_name}' ({datalines_info['row_count']} rows)")
                else:
                    # Fallback: append at end
                    code += new_function
                    fixes_applied.append(f"Auto-generated MISSING table '{table_name}' ({datalines_info['row_count']} rows)")

    # ==============================================================================
    # CODE GENERATION PASS: Replace broken code with correct implementations
    # ==============================================================================

    # GENERATE PROC FORMAT dictionaries + UDFs - BUG FIX #4 and #5
    if proc_formats:
        # Add format dictionaries at module level (after imports)
        format_dicts = []
        format_udfs = []

        for fmt_name, fmt_info in proc_formats.items():
            dict_code, udf_code = generate_format_dict_code(fmt_name, fmt_info).split('\n\n', 1)
            format_dicts.append(dict_code)
            format_udfs.append(udf_code)

        # Insert after imports section
        format_code = "\n# ==============================================================================\n"
        format_code += "# PROC FORMAT Definitions (auto-generated)\n"
        format_code += "# ==============================================================================\n\n"
        format_code += "\n".join(format_dicts)
        format_code += "\n"
        format_code += "\n".join(format_udfs)
        format_code += "\n"

        # Find location after imports to insert - BUG FIX #5: Added fallback
        import_end = code.find("from datetime import datetime")
        if import_end == -1:
            # Fallback: find last import statement
            import_matches = list(re.finditer(r'^(?:from|import)\s+', code, re.MULTILINE))
            if import_matches:
                last_import = import_matches[-1]
                import_end = code.find("\n", last_import.start())
            else:
                import_end = -1

        if import_end != -1:
            import_end = code.find("\n", import_end) + 1
            code = code[:import_end] + format_code + code[import_end:]
            fixes_applied.append(f"Generated {len(proc_formats)} format dictionary + UDF")
        else:
            warnings.append(f"Could not find import section to insert PROC FORMAT code")

        # Remove placeholder fmt_ tables
        for fmt_name in proc_formats.keys():
            # Remove: @dlt.table(name='fmt_diagcat') def fmt_diagcat(): return spark.range(0)
            fmt_pattern = rf'@d[lp]t?\.(?:table|view)\(name=[\'"](?:bronze\.)?fmt_{fmt_name}[\'"][^)]*\)[^\n]*\ndef fmt_{fmt_name}\(\):[^\n]*\n[^@]*?return spark\.range\(0\)\s*\n'
            code = re.sub(fmt_pattern, '', code, flags=re.DOTALL)

    # ==============================================================================
    # REMOVE SAS MACRO PLACEHOLDERS - BUG FIX #6
    # ==============================================================================
    # Macros are functions in SAS, not tables. The base converter incorrectly
    # creates empty placeholder tables for them. We need to remove these.
    macro_names = []
    if sas_source_text:
        # Extract macro names: %macro name(...)
        macro_pattern = r'%macro\s+(\w+)\s*[\(;]'
        macro_matches = re.finditer(macro_pattern, sas_source_text, re.IGNORECASE)
        for match in macro_matches:
            macro_name = match.group(1).lower()
            macro_names.append(macro_name)

            # Remove empty placeholder table for this macro
            # Pattern: @dlt.table(...) def macro_name(): ... return spark.range(0)
            macro_table_pattern = rf'@d[lp]t?\.(?:table|view|materialized_view)\([^)]*name=[\'"](?:[^\'\"]*\.)?{macro_name}[\'"][^)]*\)[^\n]*\ndef {macro_name}\(\):[\s\S]*?return spark\.range\(0\)\s*\n'
            before_len = len(code)
            code = re.sub(macro_table_pattern, '', code, flags=re.DOTALL | re.MULTILINE)
            after_len = len(code)

            if before_len > after_len:
                fixes_applied.append(f"Removed SAS macro placeholder table '{macro_name}' (macros are functions, not tables)")

    # ==============================================================================
    # REMOVE PROC PRINT/REPORT PLACEHOLDERS - BUG FIX #7
    # ==============================================================================
    # PROC PRINT/REPORT are output statements, not table creation statements.
    # The base converter incorrectly creates empty tables for them.
    report_tables = []
    if sas_source_text:
        # Extract report table names: proc print data=tablename; or proc report data=tablename;
        report_pattern = r'proc\s+(?:print|report)\s+data\s*=\s*(\w+(?:\.\w+)?)'
        report_matches = re.finditer(report_pattern, sas_source_text, re.IGNORECASE)
        for match in report_matches:
            table_ref = match.group(1).lower()
            # Extract just the table name (remove schema prefix if present)
            table_name = table_ref.split('.')[-1]

            # Check if a "_report" variant exists (common pattern)
            report_variant = f"{table_name}_report"

            for name_to_check in [table_name, report_variant]:
                # Remove empty placeholder table for this report
                report_pattern = rf'@d[lp]t?\.(?:table|view|materialized_view)\([^)]*name=[\'"](?:[^\'\"]*\.)?{name_to_check}[\'"][^)]*\)[^\n]*\ndef {name_to_check}\(\):[\s\S]*?return spark\.range\(0\)\s*\n'
                before_len = len(code)
                code = re.sub(report_pattern, '', code, flags=re.DOTALL | re.MULTILINE)
                after_len = len(code)

                if before_len > after_len:
                    fixes_applied.append(f"Removed PROC PRINT/REPORT placeholder '{name_to_check}' (reports are output, not tables)")
                    report_tables.append(name_to_check)

    # GENERATE MERGE join code and replace broken SQL - BUG FIX #1
    if merge_patterns:
        # Use api_style from function parameter (already set from widget)
        # No need to detect - the parameter is passed from API_STYLE widget

        for pattern in merge_patterns:
            output_table = pattern['output_table']

            # Generate correct join code
            correct_code = generate_merge_join_code(pattern, table_analysis, api_style, schema_bronze, schema_silver, schema_gold)

            # Find and replace the broken function - BUG FIX #1: Fixed regex
            # FIXED: Use [\s\S] instead of [^@] to match any character including newlines
            # FIXED: Match complete SQL string with [\s\S]+? (at least one char, non-greedy)
            # FIXED: Allow whitespace before closing paren: \s*\)
            func_pattern = rf'(@d[lp]t?\.(?:view|materialized_view|table)\(name=[\'"](?:silver\.)?{output_table}[\'"][^)]*\)[^\n]*\ndef {output_table}\(\):[\s\S]*?return\s+spark\.sql\(\s*"""[\s\S]+?"""\s*\))'

            match = re.search(func_pattern, code, re.MULTILINE)
            if match:
                code = code.replace(match.group(1), correct_code.strip())
                fixes_applied.append(f"Generated correct JOIN for '{output_table}'")
            else:
                warnings.append(f"Could not find function '{output_table}' to replace MERGE code")

    # GENERATE RETAIN window function code and replace broken logic - BUG FIX #2
    if retain_patterns:
        # Use api_style from function parameter (already set from widget)
        # No need to detect - the parameter is passed from API_STYLE widget

        for pattern in retain_patterns:
            output_table = pattern['output_table']

            # Generate correct window code
            correct_code = generate_retain_window_code(pattern, table_analysis, api_style, schema_bronze, schema_silver, schema_gold)

            # Find and replace the broken function - BUG FIX #2: Fixed regex (same as MERGE)
            func_pattern = rf'(@d[lp]t?\.(?:table|view|materialized_view)\(name=[\'"](?:silver\.)?{output_table}[\'"][^)]*\)[^\n]*\ndef {output_table}\(\):[\s\S]*?return\s+spark\.sql\(\s*"""[\s\S]+?"""\s*\))'

            match = re.search(func_pattern, code, re.MULTILINE)
            if match:
                code = code.replace(match.group(1), correct_code.strip())
                fixes_applied.append(f"Generated correct Window function for '{output_table}'")
            else:
                warnings.append(f"Could not find function '{output_table}' to replace RETAIN code")

    # ==============================================================================
    # FIX 1: Handle 'FROM src' placeholder - Replace with auto-generated inline data!
    # ==============================================================================
    # Detect if original SAS used DATALINES (inline data)
    has_datalines = 'datalines;' in sas_source_text.lower() or 'cards;' in sas_source_text.lower()

    if 'FROM src' in code:
        # For each table, replace generic 'src' with auto-generated code or placeholder
        for t in table_analysis:
            table_name = t['name']

            # Find function definition for this table - FIXED: Match closing triple quotes!
            # Pattern explanation:
            #   (def {table_name}\(\):) - function definition line
            #   (.*?) - everything between def and return (non-greedy)
            #   (return spark\.sql\(\"\"\".*?\"\"\"\)) - COMPLETE return statement with closing """
            func_pattern = rf"(def {table_name}\(\):)(.*?)(return spark\.sql\(\"\"\".*?\"\"\"\))"

            match = re.search(func_pattern, code, re.DOTALL)
            if not match:
                continue

            func_def = match.group(1)
            func_body_before = match.group(2)
            return_statement = match.group(3)

            # Check if we have parsed DATALINES for this table
            if table_name in datalines_parsed:
                # AUTO-GENERATE inline DataFrame code!
                datalines_info = datalines_parsed[table_name]
                inline_code = generate_inline_dataframe_code(table_name, datalines_info)

                # Replace entire function body (including any comments/placeholders in SQL)
                new_function = f"{func_def}\n{inline_code}"

                # Replace the matched portion (full function from def to end of return)
                code = code.replace(match.group(0), new_function)

                fixes_applied.append(f"Auto-generated inline data for '{table_name}' ({datalines_info['row_count']} rows)")
                continue  # Skip to next table

            # If no DATALINES parsed, fall back to table-specific placeholder
            if 'FROM src' not in return_statement:
                continue

            # Create table-specific placeholder
            src_placeholder = f"SRC_{table_name}"

            # Determine if this is likely reference data (DATALINES)
            is_reference_data = (
                t['layer'] == 'bronze' and
                (table_name.startswith('work_') or table_name.startswith('fmt_') or
                 table_name in ['members', 'providers', 'benefit_plans', 'plans'])
            )

            if has_datalines and is_reference_data:
                    # DATALINES reference data → Recommend temporary view or dictionary
                    replacement = f'''FROM SRC_{table_name}
    -- ⚠️ REPLACE 'SRC_{table_name}' WITH ONE OF:
    --
    -- Option A (Small Lookup <100 rows): Python Dictionary + UDF
    --   - Best for: Format mappings, simple key-value lookups
    --   - Example: DIAGCAT_FORMAT = {{'E11': 'DIABETES', 'I10': 'HTN'}}
    --   - Use: .withColumn("category", format_udf(F.col("code")))
    --
    -- Option B (Reference Data 100-10K rows): Inline DataFrame → Temporary View
    --   - Best for: Reference tables used in joins (members, providers, plans)
    --   - Pattern:
    --     data = [("M001", "PLAN1", "2025-01-01"), ...]
    --     schema = "member_id STRING, plan_id STRING, eff_date DATE"
    --     return spark.createDataFrame(data, schema)
    --
    -- Option C (External Source): Widget-driven source table
    --   - Best for: Production external data
    --   - Pattern: spark.read.table(f"{{SOURCE_CATALOG}}.{{SOURCE_SCHEMA}}.{table_name}")
    --'''
            else:
                # Transaction data → Recommend external source
                replacement = f'''FROM SRC_{table_name}
    -- ⚠️ REPLACE 'SRC_{table_name}' WITH EXTERNAL SOURCE:
    --
    -- Option A (Unity Catalog Table):
    --   spark.read.table("{{SOURCE_CATALOG}}.{{SOURCE_SCHEMA}}.{table_name}")
    --
    -- Option B (Volume Path):
    --   spark.read.parquet("/Volumes/{{CATALOG}}/{{SCHEMA}}/landing/{table_name}/")
    --
    -- Option C (External Location):
    --   spark.read.format("delta").load("s3://bucket/path/{table_name}/")
    --
    -- Add widgets at top of file:
    --   SOURCE_CATALOG = dbutils.widgets.get("source_catalog")
    --   SOURCE_SCHEMA = dbutils.widgets.get("source_schema")
    --'''

            # Replace only for this specific function
            code = re.sub(
                rf"(def {table_name}\(\):.*?return spark\.sql\(\"\"\".*?)FROM src",
                rf"\1{replacement}",
                code,
                count=1,
                flags=re.DOTALL
            )

            if has_datalines and is_reference_data:
                warnings.append(f"'{table_name}': Replace SRC_{table_name} with inline data (DATALINES not auto-parsed)")
            else:
                warnings.append(f"'{table_name}': Replace SRC_{table_name} with external source")

        # Summary of what was done
        auto_generated_count = sum(1 for msg in fixes_applied if 'Auto-generated inline data' in msg)
        placeholder_count = sum(1 for msg in warnings if 'Replace SRC_' in msg)

        if auto_generated_count > 0:
            fixes_applied.append(f"Successfully auto-generated {auto_generated_count} table(s) from DATALINES")

        if placeholder_count > 0:
            if has_datalines:
                fixes_applied.append(f"Added table-specific placeholders for {placeholder_count} table(s)")
                fixes_applied.append("Added guidance: dictionary vs temporary view for reference data")
            else:
                fixes_applied.append(f"Added table-specific source placeholders for {placeholder_count} table(s)")

    # ==============================================================================
    # FIX 2: Remove duplicate function definitions (PROC SORT artifacts)
    # ==============================================================================
    # Remove ALL sort_raw functions - they're just PROC SORT steps (don't create tables)
    if 'def sort_raw():' in code:
        original_count = code.count('def sort_raw():')

        # Simpler, more robust pattern - match from decorator to return statement
        # Using DOTALL flag, .*? matches anything including newlines (non-greedy)
        sort_raw_pattern = (
            r'@d[lp]t?\.(?:view|table|materialized_view|temporary_view)\([^)]*sort_raw[^)]*\)'  # Decorator with sort_raw
            r'.*?'  # Everything between (non-greedy with DOTALL)
            r'def sort_raw\(\):'  # Function definition
            r'.*?'  # Everything between (non-greedy with DOTALL)
            r'return spark\.range\(0\)'  # Return statement
            r'\s*\n'  # Trailing whitespace and newline
        )

        code = re.sub(sort_raw_pattern, '', code, flags=re.DOTALL)

        removed_count = original_count - code.count('def sort_raw():')
        if removed_count > 0:
            fixes_applied.append(f"Removed {removed_count} PROC SORT artifact(s) (sort_raw functions)")

    # ==============================================================================
    # FIX 3: Fix broken SQL patterns
    # ==============================================================================

    # Pattern A: SAS MERGE syntax leaked through
    # Example: "FULL JOIN (in=inclaim)" → needs manual rewrite
    if 'FULL JOIN (in=' in code or 'FULL JOIN (keep=' in code:
        code = code.replace('FULL JOIN (in=', '-- ⚠️ SAS MERGE SYNTAX: Fix this join! -- FULL JOIN (in=')
        warnings.append("SAS MERGE syntax detected - needs manual conversion to PySpark .join()")
        fixes_applied.append("Added warning markers for SAS MERGE syntax")

    # Pattern B: SAS format function didn't convert
    # Example: cast(diag_code, $diagcat.) → needs format UDF
    # V7 FIX #6: Generate inline CASE instead of UDF calls in SQL (UDFs need registration)
    if 'cast(' in code.lower() and '$' in code:
        # If we have extracted format definitions, replace with inline CASE
        if proc_formats:
            for fmt_name, fmt_info in proc_formats.items():
                # Match: cast(column, $fmtname...) or put(column, $fmtname.)
                pattern = rf'(?:cast|put)\((\w+),\s*\${fmt_name}[^)]*\)'

                # Build inline CASE expression
                mappings = fmt_info['mappings']
                default = fmt_info.get('default', 'OTHER')

                case_expr = "CASE \\1"
                for key, value in mappings.items():
                    case_expr += f" WHEN '{key}' THEN '{value}'"
                case_expr += f" ELSE '{default}' END"

                code = re.sub(pattern, case_expr, code, flags=re.IGNORECASE)
            fixes_applied.append("Replaced SAS format functions with inline CASE expressions")
        else:
            # No format definitions found, just add warning
            code = re.sub(
                r'cast\((\w+),\s*\$\w+.*?\)',
                r'-- ⚠️ SAS FORMAT: Replace with F.when().otherwise() -- cast(\1, ...)',
                code,
                flags=re.IGNORECASE
            )
            warnings.append("SAS format function detected - needs conversion to F.when().otherwise()")
            fixes_applied.append("Added warning markers for SAS format functions")

    # Pattern C: RETAIN (running totals) - add comment
    if 'retain' in sas_source_text.lower() and not retain_patterns:
        # Only warn if we didn't already fix RETAIN patterns
        warnings.append("SAS RETAIN detected - verify running totals use Window functions correctly")

    # Pattern D: Fix SAS functions leaked into SQL - BUG FIX #8
    # ==============================================================================
    # SAS functions like missing(), coalescec(), etc. don't exist in SQL
    # Replace them with SQL equivalents

    # Fix: NOT missing(column) → column IS NOT NULL
    before_len = len(code)
    code = re.sub(
        r'NOT\s+missing\((\w+)\)',
        r'\1 IS NOT NULL',
        code,
        flags=re.IGNORECASE
    )
    if len(code) < before_len:
        fixes_applied.append("Replaced SAS missing() function with SQL IS NOT NULL")

    # Fix: missing(column) → column IS NULL
    before_len = len(code)
    code = re.sub(
        r'\bmissing\((\w+)\)',
        r'\1 IS NULL',
        code,
        flags=re.IGNORECASE
    )
    if len(code) < before_len:
        fixes_applied.append("Replaced SAS missing() function with SQL IS NULL")

    # Pattern E: Remove SAS DATA step syntax from SQL - BUG FIX #9
    # ==============================================================================
    # Remove: "then do;" and "end;" from SQL CASE statements
    before_len = len(code)
    code = re.sub(
        r'\bthen\s+do\s*;',
        'THEN',
        code,
        flags=re.IGNORECASE
    )
    if len(code) < before_len:
        fixes_applied.append("Removed SAS 'then do;' syntax from SQL")

    # Remove: standalone "if" before column comparisons in SQL
    # Example: "if eff_date <= service_date" → "eff_date <= service_date" (in WHEN clause)
    before_len = len(code)
    code = re.sub(
        r'(?<=WHEN\s)\bif\s+',
        '',
        code,
        flags=re.IGNORECASE
    )
    if len(code) < before_len:
        fixes_applied.append("Removed SAS 'if' keywords from SQL WHEN clauses")

    # Pattern F: Add limit_exceeded column after RETAIN ytd_paid - BUG FIX #10
    # ==============================================================================
    # RETAIN blocks create running totals (ytd_paid) but also need limit check column
    pattern_retain_limit = r"(\.withColumn\(\"ytd_paid\", F\.sum\(\"billed_amount\"\)\.over\(window\)\))"
    replacement_retain = r'\1 \\\n        .withColumn("limit_exceeded",\n                    F.when(F.col("ytd_paid") > F.col("annual_limit"), "Y").otherwise("N"))'
    before_len = len(code)
    code = re.sub(pattern_retain_limit, replacement_retain, code)
    if len(code) > before_len:
        fixes_applied.append("Added limit_exceeded column after RETAIN ytd_paid calculation")

    # Pattern G: Fix nested IF/THEN/ELSE → Single CASE statement - BUG FIX #11
    # ==============================================================================
    # Multiple literal assignments create duplicate columns. Convert to single CASE.
    # Pattern: Multiple lines like 'DENIED' AS adj_status, 'DENIED' AS adj_status, ...
    # This is complex, so we look for the specific pattern in clm_claims_adjudicated
    dup_col_pattern = r"""(\@dp\.table\(name='[^']*gold\.clm_claims_adjudicated'[^)]*\)\s*def clm_claims_adjudicated\(\):[\s\S]*?return spark\.sql\(\s*\"\"\"SELECT \*,[\s\S]*?)('DENIED' AS adj_status,[\s\S]*?'MEMBER NOT ELIGIBLE[^']*' AS deny_reason,[\s\S]*?'DENIED' AS adj_status,[\s\S]*?'DUPLICATE CLAIM' AS deny_reason,[\s\S]*?'PENDED' AS adj_status,[\s\S]*?'OUT OF NETWORK[^']*' AS deny_reason,[\s\S]*?'DENIED' AS adj_status,[\s\S]*?'ANNUAL BENEFIT[^']*' AS deny_reason,[\s\S]*?'APPROVED' AS adj_status,[\s\S]*?'' AS deny_reason,[\s\S]*?billed_amount - copay AS paid_amount[\s\S]*?FROM [^\"]+)"""

    # Check if we have this pattern
    if re.search(r"'DENIED' AS adj_status,[\s\S]{10,200}'DENIED' AS adj_status,", code):
        # Found duplicate column pattern - replace with CASE statements
        case_replacement = """
            CASE
                WHEN elig_flag = 'N' THEN 'DENIED'
                WHEN dup_flag = 'Y' THEN 'DENIED'
                WHEN network_status = 'OUTOFNETWORK' THEN 'PENDED'
                WHEN limit_exceeded = 'Y' THEN 'DENIED'
                ELSE 'APPROVED'
            END AS adj_status,

            CASE
                WHEN elig_flag = 'N' THEN 'MEMBER NOT ELIGIBLE ON SERVICE DATE'
                WHEN dup_flag = 'Y' THEN 'DUPLICATE CLAIM'
                WHEN network_status = 'OUTOFNETWORK' THEN 'OUT OF NETWORK - MANUAL REVIEW'
                WHEN limit_exceeded = 'Y' THEN 'ANNUAL BENEFIT LIMIT EXCEEDED'
                ELSE ''
            END AS deny_reason,

            CASE
                WHEN elig_flag = 'N' OR dup_flag = 'Y' OR network_status = 'OUTOFNETWORK' OR limit_exceeded = 'Y'
                THEN NULL
                ELSE billed_amount - copay
            END AS paid_amount

        FROM"""

        # Find and replace the duplicate column pattern
        before_len = len(code)
        code = re.sub(
            r"'DENIED' AS adj_status,\s*'MEMBER NOT ELIGIBLE[^']*' AS deny_reason,\s*'DENIED' AS adj_status,\s*'DUPLICATE CLAIM' AS deny_reason,\s*'PENDED' AS adj_status,\s*'OUT OF NETWORK[^']*' AS deny_reason,\s*'DENIED' AS adj_status,\s*'ANNUAL BENEFIT[^']*' AS deny_reason,\s*'APPROVED' AS adj_status,\s*'' AS deny_reason,\s*billed_amount - copay AS paid_amount\s*FROM",
            case_replacement,
            code,
            flags=re.DOTALL
        )
        if len(code) != before_len:
            fixes_applied.append("Fixed duplicate columns in nested IF/THEN/ELSE with CASE statements")

    # Pattern H: Add ELSE to incomplete CASE statements - BUG FIX #12
    # ==============================================================================
    # CASE WHEN ... THEN 'Y' END AS dup_flag  →  CASE WHEN ... THEN 'Y' ELSE 'N' END AS dup_flag
    before_len = len(code)
    code = re.sub(
        r"(CASE WHEN NOT \(\(row_number\(\) OVER \(PARTITION BY [^)]+\) = 1\) AND \(row_number\(\) OVER \(PARTITION BY [^)]+\) = 1\)\) THEN 'Y') END AS dup_flag",
        r"\1 ELSE 'N' END AS dup_flag",
        code
    )
    if len(code) > before_len:
        fixes_applied.append("Added ELSE 'N' to dup_flag CASE statement")

    # Pattern I: Fix SAS if syntax in SQL CASE statements - BUG FIX #13
    # ==============================================================================
    # CASE WHEN ... THEN if eff_date <= service_date ... → proper SQL
    sas_if_in_case = r"""CASE WHEN eff_date IS NOT NULL AND term_date IS NOT NULL THEN\s*if eff_date <= service_date <= term_date THEN 'Y' END AS elig_flag"""
    if re.search(sas_if_in_case, code, re.IGNORECASE):
        # Replace with proper SQL
        before_len = len(code)
        code = re.sub(
            sas_if_in_case,
            """CASE
                WHEN eff_date IS NOT NULL
                    AND term_date IS NOT NULL
                    AND service_date BETWEEN eff_date AND term_date
                THEN 'Y'
                ELSE 'N'
            END AS elig_flag""",
            code,
            flags=re.IGNORECASE
        )
        if len(code) != before_len:
            fixes_applied.append("Fixed SAS if syntax in SQL CASE statement (work_claims_elig2)")

    # ==============================================================================
    # GENIE FIXES: Production-Ready SQL Corrections
    # ==============================================================================

    # GENIE FIX #1: Table references - REVERSE the normalization!
    # The base converter creates: schema_table (wrong)
    # We need: schema.table (correct for SQL)
    table_ref_fixes = 0

    # Fix: FROM schema_table → FROM schema.table
    pattern = r'FROM\s+([a-z_]+)_([a-z_]+)_([a-z_]+)\.([\w_]+)'
    def denormalize_table_ref(match):
        # Handle: sas_tanderson_bronze_customer → sas_tanderson_bronze.customer
        schema = f"{match.group(1)}_{match.group(2)}_{match.group(3)}"
        table = match.group(4)
        return f'FROM {schema}.{table}'

    new_code = re.sub(pattern, denormalize_table_ref, code, flags=re.IGNORECASE)
    if new_code != code:
        table_ref_fixes = len(re.findall(pattern, code, re.IGNORECASE))
        code = new_code
        fixes_applied.append(f"✅ GENIE FIX #1: Fixed {table_ref_fixes} table reference(s) (schema_table → schema.table)")

    # Fix: JOIN schema_table → JOIN schema.table
    pattern = r'JOIN\s+([a-z_]+)_([a-z_]+)_([a-z_]+)\.([\w_]+)'
    new_code = re.sub(pattern, denormalize_table_ref, code, flags=re.IGNORECASE)
    if new_code != code:
        code = new_code

    # GENIE FIX #2: Add backticks for hyphenated catalog names
    # Pattern: FROM schema.table → FROM `catalog`.schema.table (when catalog has hyphen)
    catalog_pattern = r'FROM\s+([a-z_]+)\.([a-z_]+)'
    def add_catalog_backticks(match):
        schema = match.group(1)
        table = match.group(2)
        # Add backticked catalog if schema matches our pattern
        if schema in [schema_bronze, schema_silver, schema_gold]:
            # Check if catalog has hyphen
            if '-' in schema_bronze.split('.')[0] if '.' in schema_bronze else (schema_silver.split('.')[0] if '.' in schema_silver else (schema_gold.split('.')[0] if '.' in schema_gold else '')):
                return f'FROM `na-dbxtraining`.{schema}.{table}'
            else:
                return f'FROM {schema}.{table}'
        return f'FROM {schema}.{table}'

    # Simpler approach: just check if we're using na-dbxtraining catalog
    if 'na-dbxtraining' in schema_bronze or 'na-dbxtraining' in schema_silver or 'na-dbxtraining' in schema_gold:
        # Add backticks around catalog name in FROM clauses
        catalog_fix_pattern = r'FROM\s+([a-z_]+_[a-z_]+)\.([\w_]+)'
        def add_catalog_with_backticks(match):
            schema = match.group(1)
            table = match.group(2)
            return f'FROM `na-dbxtraining`.{schema}.{table}'

        new_code = re.sub(catalog_fix_pattern, add_catalog_with_backticks, code, flags=re.IGNORECASE)
        if new_code != code:
            code = new_code
            fixes_applied.append(f"✅ GENIE FIX #2: Added catalog backticks for hyphenated catalog name")

    # GENIE FIX #3: Date arithmetic - use datediff() instead of subtraction
    # Pattern: current_date() - col → datediff(current_date(), col)
    date_arith_pattern = r'current_date\(\)\s*-\s*(\w+)'
    def fix_date_arithmetic(match):
        col = match.group(1)
        return f'datediff(current_date(), {col})'

    new_code = re.sub(date_arith_pattern, fix_date_arithmetic, code, flags=re.IGNORECASE)
    if new_code != code:
        code = new_code
        fixes_applied.append(f"✅ GENIE FIX #3: Converted date arithmetic to datediff() function")

    # Also fix reverse pattern: col - current_date() → datediff(col, current_date())
    reverse_date_pattern = r'(\w+)\s*-\s*current_date\(\)'
    def fix_reverse_date_arithmetic(match):
        col = match.group(1)
        return f'datediff({col}, current_date())'

    new_code = re.sub(reverse_date_pattern, fix_reverse_date_arithmetic, code, flags=re.IGNORECASE)
    if new_code != code:
        code = new_code

    # GENIE FIX #4: Multiple CASE statements → Single CASE expression
    # Pattern: Multiple CASE statements for same column
    # Look for patterns like: CASE WHEN x THEN 'A' END AS col, CASE WHEN y THEN 'B' END AS col
    # This is already partially handled by the nested IF/THEN/ELSE fix above
    # Just ensure we're using WHEN ... THEN ... WHEN ... format instead of multiple CASEs

    # GENIE FIX #5: Duplicate columns - use SELECT * EXCEPT()
    # Pattern: SELECT *, trim(col) AS col → SELECT * EXCEPT(col), trim(col) AS col
    duplicate_col_pattern = r'SELECT\s+\*,\s*\n\s*trim\((\w+)\)\s+AS\s+(\1)'
    def fix_duplicate_column(match):
        col = match.group(1)
        return f'SELECT * EXCEPT({col}),\n  trim({col}) AS {col}'

    new_code = re.sub(duplicate_col_pattern, fix_duplicate_column, code, flags=re.IGNORECASE)
    if new_code != code:
        code = new_code
        fixes_applied.append(f"✅ GENIE FIX #5: Fixed duplicate column using SELECT * EXCEPT()")

    # Also handle other transformations with duplicate columns
    general_duplicate_pattern = r'SELECT\s+\*,\s*\n\s*([^,]+)\s+AS\s+(\w+)\nFROM\s+([^\n]+)\nWHERE\s+\2\s+IS\s+NOT\s+NULL'
    def fix_general_duplicate(match):
        expr = match.group(1)
        col = match.group(2)
        from_clause = match.group(3)
        # Check if the expression references the same column
        if col in expr:
            return f'SELECT * EXCEPT({col}),\n  {expr} AS {col}\nFROM {from_clause}\nWHERE {col} IS NOT NULL'
        return match.group(0)  # No change if not a duplicate

    new_code = re.sub(general_duplicate_pattern, fix_general_duplicate, code, flags=re.IGNORECASE)
    if new_code != code:
        code = new_code

    # ==============================================================================
    # FIX 4: Reference data detection for temporary views
    # ==============================================================================
    reference_tables = []

    for t in table_analysis:
        table_name = t['name'].lower()

        # Detect reference/lookup tables that should be temporary views
        is_reference = (
            t['layer'] == 'bronze' and
            (table_name.startswith('work_') or
             table_name.startswith('fmt_') or
             'format' in table_name or
             table_name in ['members', 'providers', 'benefit_plans', 'plans', 'contracts'])
        )

        if is_reference and has_datalines:
            reference_tables.append(t['name'])
            # Add recommendation comment
            if t['should_be_view'] == False:  # Currently marked as table
                warnings.append(f"Consider @dp.temporary_view for '{t['name']}' (small reference data from DATALINES)")

    # ==============================================================================
    # Add summary comment at top
    # ==============================================================================
    if fixes_applied or warnings or datalines_parsed:
        summary = "\n# " + "="*78 + "\n"
        summary += "# POST-PROCESSING SUMMARY\n"
        summary += "# " + "="*78 + "\n"

        # Show auto-generated tables first (big win!) - BUG FIX #6: Include inserted tables
        auto_generated = [table for table in datalines_parsed.keys() if
                         any(f"Auto-generated inline data for '{table}'" in msg or
                             f"Auto-generated MISSING table '{table}'" in msg for msg in fixes_applied)]
        if auto_generated:
            summary += "#\n# ✅ AUTO-GENERATED from SAS DATALINES (ready to use!):\n"
            for table in auto_generated:
                info = datalines_parsed[table]
                summary += f"#   ✅ {table}: {info['row_count']} rows × {len(info['columns'])} columns\n"
                summary += f"#      Columns: {', '.join(info['columns'][:5])}"
                if len(info['columns']) > 5:
                    summary += f" ... (+{len(info['columns'])-5} more)"
                summary += "\n"

        if fixes_applied:
            summary += "#\n# Automatic fixes applied:\n"
            for fix in fixes_applied:
                if not fix.startswith("Auto-generated inline data for"):  # Skip individual auto-gen messages
                    summary += f"#   ✓ {fix}\n"

        if warnings:
            summary += "#\n# ⚠️  Manual review still required:\n"
            for warning in warnings:
                summary += f"#   ⚠️  {warning}\n"

        if reference_tables:
            # Only show recommendations for tables that weren't auto-generated
            remaining_refs = [ref for ref in reference_tables if ref not in auto_generated]
            if remaining_refs:
                summary += "#\n# 💡 Recommendations:\n"
                summary += "#   - Consider using @dp.temporary_view for small reference data:\n"
                for ref in remaining_refs:
                    summary += f"#     • {ref}\n"

        summary += "# " + "="*78 + "\n\n"

        # Insert after the first comment block
        code = summary + code

    # ==============================================================================
    # V7 FIX #3: Qualify All Table Names in spark.sql() Strings
    # ==============================================================================
    # Build schema map: layer -> full schema name
    schema_map = {
        'bronze': schema_bronze,
        'silver': schema_silver,
        'gold': schema_gold,
    }

    # Build a map of table_name -> layer
    table_layer_map = {}
    for t in table_analysis:
        table_layer_map[t['name']] = t.get('layer', 'bronze')

    # Find all spark.sql(""" ... """) blocks
    sql_blocks = re.findall(r'spark\.sql\(\s*"""([\s\S]*?)"""\s*\)', code)

    for sql_block in sql_blocks:
        # Find unqualified table names in FROM/JOIN clauses
        # Pattern: FROM/JOIN <table_name> (without schema prefix)
        qualified_sql = sql_block

        for table_name, layer in table_layer_map.items():
            # Get full schema name for this layer
            full_schema = schema_map.get(layer, schema_bronze)

            # Match table name that's NOT already qualified (no dot before it)
            # Patterns to match:
            # - FROM work_claims_elig
            # - JOIN work_members
            # - FROM sas_tanderson_bronze.work_members → don't replace (already qualified)

            # Replace unqualified references
            patterns = [
                (rf'\bFROM\s+{table_name}\b', f'FROM {full_schema}.{table_name}'),
                (rf'\bJOIN\s+{table_name}\b', f'JOIN {full_schema}.{table_name}'),
                (rf'\bJOIN\s+{table_name}\s+AS\b', f'JOIN {full_schema}.{table_name} AS'),
            ]

            for pattern, replacement in patterns:
                qualified_sql = re.sub(pattern, replacement, qualified_sql, flags=re.IGNORECASE)

        # Replace in code (be careful to match exact block)
        code = code.replace(sql_block, qualified_sql)

    if sql_blocks:
        fixes_applied.append(f"Qualified {len(sql_blocks)} spark.sql() table reference(s) with full schema names")

    return code

print("✅ Post-processor ready (with all bug fixes applied)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## DATALINES Parser - Auto-Generate Inline Data

# COMMAND ----------

def parse_sas_datalines(sas_source_text):
    """
    Parse SAS DATALINES blocks and extract inline data

    Extracts:
    - Table name (from "data work.table_name;")
    - Column names and types (from "input" statement)
    - Data rows (from "datalines;" to ";")

    Args:
        sas_source_text: Original SAS code

    Returns:
        dict: {table_name: {'columns': [...], 'types': [...], 'data': [...]}}
    """
    import re

    datalines_blocks = {}

    # Pattern to find data step with datalines/cards
    # Matches: data work.table_name; ... input ...; datalines; rows... ;
    data_step_pattern = r'data\s+(work\.)?(\w+);(.*?)(?:datalines|cards);(.*?);(?:\s*run;|\s*data\s+|\s*proc\s+|\Z)'

    for match in re.finditer(data_step_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        table_name = match.group(2)  # Extract table name (e.g., "members")
        between_data_and_datalines = match.group(3)  # Code between "data" and "datalines"
        data_rows = match.group(4).strip()  # Data rows

        # Extract INPUT statement to get column names and types
        input_match = re.search(r'input\s+([^;]+);', between_data_and_datalines, re.IGNORECASE)

        if not input_match:
            continue

        input_statement = input_match.group(1).strip()

        # Parse input statement for column names and types
        columns = []
        types = []

        # Split by whitespace, handle formats like "member_id $" or "amount" or "date :mmddyy10."
        tokens = input_statement.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Skip format specifiers
            if token.startswith(':'):
                i += 1
                continue

            # Check if next token is a type indicator
            if i + 1 < len(tokens) and tokens[i + 1] in ['$', '$$']:
                # Character/string type
                columns.append(token)
                types.append('STRING')
                i += 2
            elif token.endswith('$'):
                # Character type (e.g., "member_id$")
                columns.append(token.rstrip('$'))
                types.append('STRING')
                i += 1
            elif ':' in token:
                # Has informat (e.g., "date:mmddyy10.")
                col_name = token.split(':')[0]
                informat = token.split(':')[1] if ':' in token else ''

                columns.append(col_name)

                # Determine type from informat
                if 'date' in informat.lower() or 'mmddyy' in informat.lower() or 'yymmdd' in informat.lower():
                    types.append('DATE')
                elif 'time' in informat.lower() or 'datetime' in informat.lower():
                    types.append('TIMESTAMP')
                else:
                    types.append('DOUBLE')
                i += 1
            elif i + 1 < len(tokens) and tokens[i + 1].startswith(':'):
                # Next token is informat
                columns.append(token)
                informat = tokens[i + 1][1:]  # Remove leading ':'

                if 'date' in informat.lower() or 'mmddyy' in informat.lower():
                    types.append('DATE')
                elif 'time' in informat.lower() or 'datetime' in informat.lower():
                    types.append('TIMESTAMP')
                else:
                    types.append('DOUBLE')
                i += 2
            else:
                # Numeric type (no modifier)
                columns.append(token)
                types.append('DOUBLE')
                i += 1

        # Parse data rows
        rows = []
        for line in data_rows.split('\n'):
            line = line.strip()
            if not line or line.startswith('*') or line.startswith('/*'):
                continue

            # Split by whitespace (SAS default delimiter)
            values = line.split()

            if len(values) == len(columns):
                rows.append(values)

        # Store parsed data
        if columns and rows:
            datalines_blocks[f"work_{table_name}"] = {
                'columns': columns,
                'types': types,
                'data': rows,
                'row_count': len(rows)
            }

    return datalines_blocks

def generate_inline_dataframe_code(table_name, datalines_info, indent="    "):
    """
    Generate PySpark inline DataFrame code from parsed DATALINES

    Args:
        table_name: Name of the table
        datalines_info: Dict with 'columns', 'types', 'data'
        indent: Indentation string

    Returns:
        str: Python code to create inline DataFrame
    """
    columns = datalines_info['columns']
    types = datalines_info['types']
    data = datalines_info['data']

    # ==============================================================================
    # V7 FIX #1: Smart Type Detection (INT vs DOUBLE)
    # ==============================================================================
    # For numeric columns, detect if all values are integers
    refined_types = []
    for col_idx, (col, typ) in enumerate(zip(columns, types)):
        if typ == 'DOUBLE':
            # Check if all values in this column are integers
            all_ints = True
            for row in data:
                val = row[col_idx]
                try:
                    # Check if value has decimal point or is a float
                    if '.' in str(val) or float(val) != int(float(val)):
                        all_ints = False
                        break
                except (ValueError, TypeError):
                    all_ints = False
                    break

            # Use INT if all values are integers
            refined_types.append('INT' if all_ints else 'DOUBLE')
        else:
            refined_types.append(typ)

    types = refined_types  # Use refined types

    # ==============================================================================
    # V7 FIX #2: DATE Handling (STRING schema + F.to_date() cast)
    # ==============================================================================
    # Collect DATE columns for later casting
    date_columns = [(col, typ) for col, typ in zip(columns, types) if typ in ['DATE', 'TIMESTAMP']]

    # For DATE/TIMESTAMP columns, use STRING schema and cast later
    schema_types = []
    for typ in types:
        if typ in ['DATE', 'TIMESTAMP']:
            schema_types.append('STRING')  # Use STRING, cast later
        else:
            schema_types.append(typ)

    # Build schema string
    schema_parts = [f"{col} {typ}" for col, typ in zip(columns, schema_types)]
    schema_str = ", ".join(schema_parts)

    # Build data tuples
    data_lines = []
    for row in data:
        # Format values based on type
        formatted_values = []
        for val, original_typ in zip(row, types):
            if original_typ == 'STRING' or original_typ in ['DATE', 'TIMESTAMP']:
                # Always quote strings and dates
                if original_typ in ['DATE', 'TIMESTAMP'] and '/' in val:
                    # Convert SAS date format (MM/DD/YYYY) to ISO (YYYY-MM-DD)
                    parts = val.split('/')
                    if len(parts) == 3:
                        formatted_values.append(f'"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"')
                    else:
                        formatted_values.append(f'"{val}"')
                else:
                    formatted_values.append(f'"{val}"')
            else:
                # Numeric values (INT or DOUBLE)
                formatted_values.append(val)

        data_lines.append(f"{indent}{indent}({', '.join(formatted_values)}),")

    # Build complete code
    code = f'''{indent}"""Auto-generated from SAS DATALINES"""
{indent}data = [
{chr(10).join(data_lines)}
{indent}]
{indent}schema = "{schema_str}"'''

    # Add date casting if needed
    if date_columns:
        code += f'\n{indent}return spark.createDataFrame(data, schema).select(\n'
        select_cols = []
        for col, typ in zip(columns, types):
            if typ == 'DATE':
                select_cols.append(f'{indent}{indent}F.to_date("{col}").alias("{col}")')
            elif typ == 'TIMESTAMP':
                select_cols.append(f'{indent}{indent}F.to_timestamp("{col}").alias("{col}")')
            else:
                select_cols.append(f'{indent}{indent}"{col}"')
        code += ',\n'.join(select_cols)
        code += f',\n{indent})'
    else:
        code += f'\n{indent}return spark.createDataFrame(data, schema)'

    return code

print("✅ DATALINES parser ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## PROC FORMAT Extraction - Auto-Generate Lookup Tables/Dictionaries

# COMMAND ----------

def extract_proc_formats(sas_source_text):
    """
    Parse PROC FORMAT blocks and extract format definitions

    Based on: SAS → Spark/SQL Conversion Patterns, Section 4

    Extracts:
    - Format name (e.g., $diagcat)
    - Key-value mappings ('E11' = 'DIABETES')
    - Default value (OTHER)

    Returns:
        dict: {format_name: {'type': 'char'|'num', 'mappings': {key: value}, 'default': 'OTHER'}}
    """
    import re

    formats = {}

    # Pattern to find PROC FORMAT blocks
    # Matches: proc format; value $name 'key'='value' ... other='default'; run;
    format_block_pattern = r'proc\s+format;(.*?)run;'

    for block_match in re.finditer(format_block_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        format_definitions = block_match.group(1)

        # Extract individual format definitions
        # Matches: value $diagcat 'E11'='DIABETES' 'I10'='HYPERTENSION' other='OTHER';
        value_pattern = r'value\s+(\$?)(\w+)(.*?);'

        for value_match in re.finditer(value_pattern, format_definitions, re.IGNORECASE | re.DOTALL):
            is_char = value_match.group(1) == '$'
            format_name = value_match.group(2)
            mappings_text = value_match.group(3)

            # Extract key-value pairs
            # Matches: 'E11'='DIABETES' or "E11"="DIABETES"
            pair_pattern = r"['\"]([^'\"]+)['\"][\s=]+['\"]([^'\"]+)['\"]"

            mappings = {}
            default_value = 'OTHER'

            for pair_match in re.finditer(pair_pattern, mappings_text):
                key = pair_match.group(1)
                value = pair_match.group(2)
                mappings[key] = value

            # Extract 'other' clause
            other_match = re.search(r"other[\s=]+['\"]([^'\"]+)['\"]", mappings_text, re.IGNORECASE)
            if other_match:
                default_value = other_match.group(1)

            formats[format_name] = {
                'type': 'char' if is_char else 'num',
                'mappings': mappings,
                'default': default_value
            }

    return formats

def generate_format_code(format_name, format_info, api_style="dlt"):
    """
    Generate Python code for a format definition

    Options:
    1. Python dictionary + UDF (best for small formats <100 entries)
    2. Lookup table (best for larger formats or shared across notebooks)

    Returns dictionary + UDF approach by default
    """
    mappings = format_info['mappings']
    default = format_info['default']

    # Generate dictionary
    dict_items = ', '.join([f"'{k}': '{v}'" for k, v in mappings.items()])
    dict_code = f"{format_name.upper()}_FORMAT = {{{dict_items}}}"

    # Generate UDF
    udf_code = f"""
@F.udf(returnType=StringType())
def format_{format_name}(code):
    \"\"\"Apply {format_name} format mapping (from PROC FORMAT)\"\"\"
    return {format_name.upper()}_FORMAT.get(code, '{default}')
"""

    return dict_code, udf_code

print("✅ PROC FORMAT extractor ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## MERGE Translation - Convert to FULL OUTER JOIN

# COMMAND ----------

def translate_merge_to_join(sas_source_text, converted_code):
    """
    Detect DATA step MERGE and translate to proper JOIN

    Based on: SAS → Spark/SQL Conversion Patterns, Section 2

    SAS MERGE is a coalescing outer join - matched rows combine, unmatched from either side appear.
    in= flags are boolean indicators of which side contributed.

    Translation:
    - FULL OUTER JOIN
    - COALESCE the BY variable
    - Explicit in= flags as CASE WHEN <key> IS NOT NULL
    - Filter based on subsequent IF logic
    """
    import re

    merge_translations = []

    # Find DATA step MERGE patterns in original SAS
    # Pattern: data output; merge table1 (in=flag1) table2 (in=flag2); by key; if condition; run;
    # CRITICAL FIX: Use negative lookahead (?:(?!run;).)* to NOT cross RUN; boundaries
    # This prevents matching from one DATA step to a MERGE in a different DATA step
    merge_pattern = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)merge\s+(.*?);.*?by\s+(.*?);(.*?)run;'

    for match in re.finditer(merge_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        # Group 2 is the content between DATA and MERGE (not used, just prevents crossing boundaries)
        merge_clause = match.group(3)
        by_vars = match.group(4).strip()
        post_merge_logic = match.group(5)

        # Parse merge clause: table1 (in=flag1 keep=cols) table2 (in=flag2)
        # Extract: table names, in= flags, keep= variables
        table_pattern = r'(\w+\.\w+|\w+)\s*\(([^)]*)\)|(\w+\.\w+|\w+)'

        tables = []
        for table_match in re.finditer(table_pattern, merge_clause):
            if table_match.group(1):  # Has parentheses (options)
                table_name = table_match.group(1)
                options = table_match.group(2)
            else:  # No parentheses
                table_name = table_match.group(3)
                options = ''

            # Extract in= flag
            in_match = re.search(r'in=(\w+)', options, re.IGNORECASE)
            in_flag = in_match.group(1) if in_match else None

            # Extract keep= variables
            keep_match = re.search(r'keep=([^)]+)', options, re.IGNORECASE)
            keep_vars = keep_match.group(1).strip().split() if keep_match else None

            tables.append({
                'name': table_name.replace('.', '_'),  # work.table → work_table
                'in_flag': in_flag,
                'keep_vars': keep_vars
            })

        # Determine join type from post-merge IF logic
        # if flag1; = LEFT JOIN (keep all from table1)
        # if flag1 and flag2; = INNER JOIN
        # if a or b; = FULL OUTER JOIN
        # if a and not b; = LEFT ANTI JOIN
        # No if = FULL OUTER JOIN
        join_type = 'full'
        where_clause = None

        if 'if ' in post_merge_logic.lower():
            # ==================================================================
            # ENHANCEMENT: Extract ALL IF statements, find the filter IF
            # ==================================================================
            # Collect all in= flags to identify filter IFs
            all_flags = [t['in_flag'] for t in tables if t['in_flag']]

            # Extract ALL IF statements
            all_if_statements = re.findall(r'if\s+(.*?);', post_merge_logic, re.IGNORECASE)

            # Identify the filter IF: contains ONLY in= flags, no data variables
            filter_condition = None
            for condition_raw in all_if_statements:
                condition = condition_raw.strip()

                # Check if this IF only references in= flags
                # Split by logical operators and check each token
                tokens = re.split(r'\s+(?:and|or|not)\s+', condition, flags=re.IGNORECASE)
                is_filter = True
                for token in tokens:
                    token_clean = token.strip()
                    # Skip if it's a flag
                    if token_clean in all_flags:
                        continue
                    # If it contains = or < or > or other operators, it's an assignment/comparison
                    if re.search(r'[=<>]', token_clean):
                        is_filter = False
                        break

                if is_filter and any(flag in condition for flag in all_flags):
                    filter_condition = condition
                    break

            # If we found a filter IF, determine join type
            if filter_condition:
                condition = filter_condition.lower()

                # Build flag lookup (case-insensitive)
                flag_map = {t['in_flag'].lower(): i for i, t in enumerate(tables) if t['in_flag']}

                # ==============================================================
                # Parse join logic: AND, OR, NOT
                # ==============================================================

                # Pattern 1: Single flag → LEFT JOIN
                # if a;
                if len(flag_map) >= 1:
                    # Check if it's a single flag with no operators
                    if condition in flag_map:
                        join_type = 'left'
                        table_idx = flag_map[condition]
                        where_clause = f"{tables[table_idx]['name']}.{by_vars} IS NOT NULL"

                    # Pattern 2: flag1 AND flag2 → INNER JOIN
                    # if a and b;
                    elif 'and' in condition and 'not' not in condition:
                        # Check if all flags are present
                        flags_in_condition = [flag for flag in flag_map if flag in condition]
                        if len(flags_in_condition) >= 2:
                            join_type = 'inner'

                    # Pattern 3: flag1 OR flag2 → FULL OUTER JOIN
                    # if a or b;
                    elif 'or' in condition:
                        join_type = 'full'

                    # Pattern 4: flag1 AND NOT flag2 → LEFT ANTI JOIN
                    # if a and not b;
                    elif 'and' in condition and 'not' in condition:
                        join_type = 'left_anti'

        merge_translations.append({
            'output_table': output_table.replace('.', '_'),
            'tables': tables,
            'by_vars': by_vars,
            'join_type': join_type,
            'where_clause': where_clause,
            'post_merge_logic': post_merge_logic
        })

    return merge_translations

print("✅ MERGE translator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## RETAIN Translation - Convert to Window Functions

# COMMAND ----------

def translate_retain_to_window(sas_source_text):
    """
    Detect RETAIN patterns and translate to Window functions

    Based on: SAS → Spark/SQL Conversion Patterns, Section 3

    RETAIN preserves variable across rows - needs window with proper ORDER BY.

    Patterns supported:
    1. Single variable running sum: retain var; var+amount;
    2. Multiple variables running sum: retain var1 var2 0 0; var1+amt1; var2+amt2;
    3. Carry-forward (last non-missing): retain var; if not missing(src) then var=src;

    Translation: SUM(amount) OVER (PARTITION BY key ORDER BY sort_col ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
              OR: LAST_VALUE(src, true) OVER (PARTITION BY key ORDER BY sort_col ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    """
    import re

    retain_patterns = []

    # =========================================================================
    # PATTERN 1 & 2: RUNNING SUM (single or multiple variables)
    # =========================================================================
    # Pattern: data output; set input; by key; retain var1 var2 ...; var1 + amount1; var2 + amount2; run;
    # First, find DATA steps with RETAIN statements
    data_step_pattern = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)set\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)by\s+(\w+(?:\s+\w+)*)\s*;((?:(?!run;).)*?)retain\s+([\w\s\d]+)\s*;((?:(?!run;).)*?)run;'

    for match in re.finditer(data_step_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        input_table = match.group(3)
        by_vars = match.group(5).strip()
        retain_statement = match.group(7).strip()  # e.g., "ytd_paid 0" or "ytd_paid claim_count 0 0"
        data_step_body = match.group(8)  # Everything after RETAIN until run;

        # Parse RETAIN statement to extract all variables
        # Format: var1 [init1] var2 [init2] ...
        # Initial values are optional and can be numeric (0, 0.0) or variable names
        retain_parts = retain_statement.split()
        retained_vars = []
        i = 0
        while i < len(retain_parts):
            var = retain_parts[i]
            # Check if this looks like a variable name (starts with letter or underscore)
            if re.match(r'^[a-zA-Z_]\w*$', var):
                retained_vars.append(var)
                # Skip next token if it's a numeric initial value
                if i + 1 < len(retain_parts) and re.match(r'^-?\d+\.?\d*$', retain_parts[i + 1]):
                    i += 2  # Skip both var and init value
                else:
                    i += 1  # Just skip var, no init value
            else:
                i += 1  # Skip non-variable tokens

        # Now find accumulation statements for each retained variable
        # Pattern: var + source  or  var = var + source
        for retain_var in retained_vars:
            # Look for: var + source; (shorthand)
            accum_pattern = rf'\b{retain_var}\s*\+\s*(\w+)\s*;'
            accum_match = re.search(accum_pattern, data_step_body, re.IGNORECASE)

            if accum_match:
                accum_source = accum_match.group(1).strip()

                # Determine ordering - look for PROC SORT before this DATA step
                sort_pattern = rf'proc\s+sort\s+data\s*=\s*{re.escape(input_table)}.*?by\s+(.*?);'
                sort_match = re.search(sort_pattern, sas_source_text[:match.start()], re.IGNORECASE | re.DOTALL)
                order_by = sort_match.group(1).strip() if sort_match else by_vars

                retain_patterns.append({
                    'output_table': output_table.replace('.', '_'),
                    'input_table': input_table.replace('.', '_'),
                    'partition_by': by_vars,
                    'order_by': order_by,
                    'retain_var': retain_var,
                    'accum_source': accum_source,
                    'pattern_type': 'running_sum'
                })

    # =========================================================================
    # PATTERN 3: CARRY-FORWARD (last non-missing value)
    # =========================================================================
    # Pattern: retain var; if not missing(source) then var = source;
    #       OR: retain var; if source ~= . then var = source;  (SAS ~= means "not equal")
    # Split into two separate patterns for clarity

    # Pattern 3a: if not missing(source) then var = source;
    carry_forward_pattern_a = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)set\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)by\s+(\w+(?:\s+\w+)*)\s*;((?:(?!run;).)*?)retain\s+(\w+)\s*;((?:(?!run;).)*?)if\s+not\s+missing\((\w+)\)\s+then\s+(\w+)\s*=\s*(\w+)\s*;'

    for match in re.finditer(carry_forward_pattern_a, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        input_table = match.group(3)
        by_vars = match.group(5).strip()
        retain_var = match.group(7).strip()
        source_var = match.group(9).strip()  # from not missing(source)
        target_var = match.group(10).strip()  # left side of =
        assigned_var = match.group(11).strip()  # right side of =

        # Verify that target matches retained variable, and assigned matches source
        # Pattern: if not missing(source) then retain_var = source;
        if target_var == retain_var and assigned_var == source_var:
            # Determine ordering - look for PROC SORT before this DATA step
            sort_pattern = rf'proc\s+sort\s+data\s*=\s*{re.escape(input_table)}.*?by\s+(.*?);'
            sort_match = re.search(sort_pattern, sas_source_text[:match.start()], re.IGNORECASE | re.DOTALL)
            order_by = sort_match.group(1).strip() if sort_match else by_vars

            retain_patterns.append({
                'output_table': output_table.replace('.', '_'),
                'input_table': input_table.replace('.', '_'),
                'partition_by': by_vars,
                'order_by': order_by,
                'retain_var': retain_var,  # Use retain_var, not target_var
                'source_var': source_var,
                'pattern_type': 'carry_forward'
            })

    # Pattern 3b: if var ~= . then target = var;  (SAS ~= means "not equal to")
    carry_forward_pattern_b = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)set\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)by\s+(\w+(?:\s+\w+)*)\s*;((?:(?!run;).)*?)retain\s+(\w+)\s*;((?:(?!run;).)*?)if\s+(\w+)\s*~=\s*\.\s+then\s+(\w+)\s*=\s*(\w+)\s*;'

    for match in re.finditer(carry_forward_pattern_b, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        input_table = match.group(3)
        by_vars = match.group(5).strip()
        retain_var = match.group(7).strip()
        source_var = match.group(9).strip()  # from var ~= .
        target_var = match.group(10).strip()  # left side of =
        assigned_var = match.group(11).strip()  # right side of =

        # Verify that target matches retained variable, and assigned matches source
        # Pattern: if source ~= . then retain_var = source;
        if target_var == retain_var and assigned_var == source_var:
            # Determine ordering - look for PROC SORT before this DATA step
            sort_pattern = rf'proc\s+sort\s+data\s*=\s*{re.escape(input_table)}.*?by\s+(.*?);'
            sort_match = re.search(sort_pattern, sas_source_text[:match.start()], re.IGNORECASE | re.DOTALL)
            order_by = sort_match.group(1).strip() if sort_match else by_vars

            retain_patterns.append({
                'output_table': output_table.replace('.', '_'),
                'input_table': input_table.replace('.', '_'),
                'partition_by': by_vars,
                'order_by': order_by,
                'retain_var': retain_var,
                'source_var': source_var,
                'pattern_type': 'carry_forward'
            })

    return retain_patterns

print("✅ RETAIN translator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## FIRST./LAST. Detection - Duplicate Detection & Row Filtering

# COMMAND ----------

def translate_first_last_to_window(sas_source_text):
    """
    Detect FIRST./LAST. patterns and translate to Window functions

    Based on: SAS → Spark/SQL Conversion Patterns, Section 5

    FIRST./LAST. are automatic variables in SAS BY groups that mark the first/last
    observation in each group. Commonly used for duplicate detection.

    Pattern: if first.key; or if last.key;
    Translation: ROW_NUMBER() OVER (PARTITION BY key ORDER BY ...) = 1  (for FIRST)
                 ROW_NUMBER() OVER (PARTITION BY key ORDER BY ... DESC) = 1  (for LAST)

    Returns:
        list: [{'output_table': ..., 'input_table': ..., 'partition_by': ...,
                'order_by': ..., 'filter_type': 'first'|'last', 'window_func': 'ROW_NUMBER'}]
    """
    import re

    first_last_patterns = []

    # Pattern 1: if first.variable; (keep first occurrence in group)
    # Pattern: data output; set input; by key; if first.key;
    first_pattern = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)set\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)by\s+(\w+(?:\s+\w+)*)\s*;((?:(?!run;).)*?)if\s+first\.(\w+)\s*;'

    for match in re.finditer(first_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        input_table = match.group(3)
        by_vars = match.group(5).strip()
        first_var = match.group(7).strip()

        # Verify that the FIRST variable is in the BY list
        by_list = [v.strip() for v in by_vars.split()]
        if first_var in by_list:
            # Determine ordering - look for PROC SORT before this DATA step
            sort_pattern = rf'proc\s+sort\s+data\s*=\s*{re.escape(input_table)}.*?by\s+(.*?);'
            sort_match = re.search(sort_pattern, sas_source_text[:match.start()], re.IGNORECASE | re.DOTALL)
            order_by = sort_match.group(1).strip() if sort_match else by_vars

            first_last_patterns.append({
                'output_table': output_table.replace('.', '_'),
                'input_table': input_table.replace('.', '_'),
                'partition_by': first_var,  # The variable we're grouping by
                'order_by': order_by,       # From PROC SORT
                'filter_type': 'first',
                'window_func': 'ROW_NUMBER'
            })

    # Pattern 2: if last.variable; (keep last occurrence in group)
    # Pattern: data output; set input; by key; if last.key;
    last_pattern = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)set\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)by\s+(\w+(?:\s+\w+)*)\s*;((?:(?!run;).)*?)if\s+last\.(\w+)\s*;'

    for match in re.finditer(last_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        input_table = match.group(3)
        by_vars = match.group(5).strip()
        last_var = match.group(7).strip()

        # Verify that the LAST variable is in the BY list
        by_list = [v.strip() for v in by_vars.split()]
        if last_var in by_list:
            # Determine ordering - look for PROC SORT before this DATA step
            sort_pattern = rf'proc\s+sort\s+data\s*=\s*{re.escape(input_table)}.*?by\s+(.*?);'
            sort_match = re.search(sort_pattern, sas_source_text[:match.start()], re.IGNORECASE | re.DOTALL)
            order_by = sort_match.group(1).strip() if sort_match else by_vars

            first_last_patterns.append({
                'output_table': output_table.replace('.', '_'),
                'input_table': input_table.replace('.', '_'),
                'partition_by': last_var,   # The variable we're grouping by
                'order_by': order_by,        # From PROC SORT
                'filter_type': 'last',
                'window_func': 'ROW_NUMBER'
            })

    return first_last_patterns

print("✅ FIRST./LAST. translator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Code Generation - Generate Correct PySpark from Detected Patterns

# COMMAND ----------

def generate_merge_join_code(merge_pattern, table_analysis, api_style="dp", schema_bronze="bronze", schema_silver="silver", schema_gold="gold"):
    """
    Generate correct PySpark join code from detected MERGE pattern

    Based on: SAS → Spark/SQL Conversion Patterns, Section 2

    V7 Enhancement: Layer-aware table references with schema suffix support
    """
    output_table = merge_pattern['output_table']
    tables = merge_pattern['tables']
    by_vars = merge_pattern['by_vars']
    join_type = merge_pattern['join_type']

    # Helper: Get layer for a table name
    def get_table_layer(table_name):
        for t in table_analysis:
            if t['name'] == table_name:
                return t.get('layer', 'bronze')
        return 'bronze'  # Default

    # Schema map: layer -> full schema name
    schema_map = {
        'bronze': schema_bronze,
        'silver': schema_silver,
        'gold': schema_gold,
    }

    # Generate function header
    output_layer = get_table_layer(output_table)
    output_schema = schema_map.get(output_layer, schema_bronze)
    decorator = "@dp.materialized_view" if api_style == "dp" else "@dlt.view"
    code = f'{decorator}(name=\'{output_schema}.{output_table}\')\n'
    code += f'def {output_table}():\n'
    code += f'    """Converted from SAS DATA step MERGE"""\n'

    # Read tables (V7: Layer-aware with full schema names)
    for i, table in enumerate(tables):
        var_name = f"table{i+1}" if len(tables) > 2 else ["left_df", "right_df"][i] if len(tables) == 2 else "df"
        table_layer = get_table_layer(table["name"])
        table_schema = schema_map.get(table_layer, schema_bronze)
        code += f'    {var_name} = spark.read.table("{table_schema}.{table["name"]}")'

        # Add select for keep= variables
        if table.get('keep_vars'):
            keep_cols = ', '.join([f'"{col}"' for col in table['keep_vars']])
            # Quote the by_vars if it's not already in keep_vars to avoid duplication
            if by_vars not in table['keep_vars']:
                code += f'.select("{by_vars}", {keep_cols})'
            else:
                code += f'.select({keep_cols})'
        code += '\n'

    # Generate join
    if len(tables) == 2:
        code += f'    \n'
        code += f'    # {join_type.upper()} JOIN (from SAS MERGE)\n'
        code += f'    result = left_df.join(right_df, "{by_vars}", "{join_type}")\n'

        # Add in= flags if referenced
        # V7 FIX #5: Avoid ambiguous column references after join
        if tables[0].get('in_flag') or tables[1].get('in_flag'):
            code += f'    \n'
            code += f'    # Add in= flags (from SAS MERGE options)\n'
            if tables[0].get('in_flag'):
                # Left side always present (it's the base table), use F.lit(1)
                code += f'    result = result.withColumn("{tables[0]["in_flag"]}", F.lit(1))\n'
            if tables[1].get('in_flag'):
                # Right side: check a non-join-key column to avoid ambiguity
                # Find first non-join-key column from right table
                right_cols = tables[1].get('keep_vars') or []
                check_col = None
                for col in right_cols:
                    if col != by_vars:
                        check_col = col
                        break

                if check_col:
                    code += f'    result = result.withColumn("{tables[1]["in_flag"]}", \n'
                    code += f'        F.when(F.col("{check_col}").isNotNull(), F.lit(1)).otherwise(F.lit(0))\n'
                    code += f'    )\n'
                else:
                    # Fallback: check if join key came from right (may be ambiguous in some edge cases)
                    code += f'    result = result.withColumn("{tables[1]["in_flag"]}", \n'
                    code += f'        F.when(F.col("{by_vars}").isNotNull(), F.lit(1)).otherwise(F.lit(0))\n'
                    code += f'    )\n'

    code += f'    return result\n'

    return code

def generate_retain_window_code(retain_pattern, table_analysis, api_style="dp", schema_bronze="bronze", schema_silver="silver", schema_gold="gold"):
    """
    Generate correct Window function code from detected RETAIN pattern

    Based on: SAS → Spark/SQL Conversion Patterns, Section 3

    V7 Enhancement: Layer-aware table references with schema suffix support
    """
    output_table = retain_pattern['output_table']
    input_table = retain_pattern['input_table']
    partition_by = retain_pattern['partition_by']
    order_by = retain_pattern['order_by']
    retain_var = retain_pattern['retain_var']
    accum_source = retain_pattern['accum_source']

    # Helper: Get layer for a table name
    def get_table_layer(table_name):
        for t in table_analysis:
            if t['name'] == table_name:
                return t.get('layer', 'silver')
        return 'silver'  # Default

    # Schema map: layer -> full schema name
    schema_map = {
        'bronze': schema_bronze,
        'silver': schema_silver,
        'gold': schema_gold,
    }

    decorator = "@dp.table" if api_style == "dp" else "@dlt.table"

    # Split partition_by and order_by columns (space-separated) and quote each
    partition_cols = ', '.join([f'"{col.strip()}"' for col in partition_by.split()])
    order_cols = ', '.join([f'"{col.strip()}"' for col in order_by.split()])

    # V7: Layer-aware output with full schema names
    output_layer = get_table_layer(output_table)
    input_layer = get_table_layer(input_table)
    output_schema = schema_map.get(output_layer, schema_silver)
    input_schema = schema_map.get(input_layer, schema_silver)

    code = f'{decorator}(name=\'{output_schema}.{output_table}\')\n'
    code += f'def {output_table}():\n'
    code += f'    """Converted from SAS RETAIN - running total per {partition_by}"""\n'
    code += f'    from pyspark.sql.window import Window\n'
    code += f'    \n'
    code += f'    # Window for running total (ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)\n'
    code += f'    window = Window.partitionBy({partition_cols}) \\\n'
    code += f'                   .orderBy({order_cols}) \\\n'
    code += f'                   .rowsBetween(Window.unboundedPreceding, Window.currentRow)\n'
    code += f'    \n'
    code += f'    # V7: Layer-aware table reference with full schema name\n'
    code += f'    return spark.read.table("{input_schema}.{input_table}") \\\n'
    code += f'        .withColumn("{retain_var}", F.sum("{accum_source}").over(window))\n'

    return code

def generate_format_dict_code(format_name, format_info):
    """
    Generate dictionary + UDF from PROC FORMAT definition

    Based on: SAS → Spark/SQL Conversion Patterns, Section 4
    """
    mappings = format_info['mappings']
    default = format_info['default']

    # Generate dictionary
    dict_items = ', '.join([f"'{k}': '{v}'" for k, v in mappings.items()])
    dict_code = f"{format_name.upper()}_FORMAT = {{{dict_items}}}\n"

    # Generate UDF - BUG FIX #4: Use T.StringType() instead of StringType()
    udf_code = f"""
@F.udf(returnType=T.StringType())
def format_{format_name}(code):
    \"\"\"Apply {format_name} format (from PROC FORMAT)\"\"\"
    return {format_name.upper()}_FORMAT.get(code, '{default}')
"""

    return dict_code + udf_code

print("✅ Code generation functions ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## API Converter (DLT → SDP/dp)

# COMMAND ----------

def convert_dlt_to_dp_api(code, table_analysis):
    """
    Converts DLT API to Apache Spark 4.1+ SDP (Spark Declarative Pipelines) API

    Apache Spark 4.1+ introduced SDP as the open standard for declarative pipelines.
    Databricks Lakeflow Pipelines is built on top of SDP.

    Official API Mappings (Apache Spark 4.1+):
    - import dlt → from pyspark import pipelines as dp
    - @dlt.table → @dp.table (for persistent tables, streaming or batch)
    - @dlt.view → @dp.temporary_view (for intermediate views)

    Note: @dp.materialized_view is for persistent views (like our intermediate Silver layer)

    Args:
        code: Python code using dlt API
        table_analysis: List of dicts with table info (name, layer, should_be_view)

    Returns:
        Code converted to SDP (dp) API style with layer prefixes
    """

    # Replace imports
    code = code.replace("import dlt", "from pyspark import pipelines as dp")

    # Add comment about Apache Spark 4.1+ SDP
    code = code.replace(
        "from pyspark import pipelines as dp",
        "from pyspark import pipelines as dp  # Apache Spark 4.1+ Declarative Pipelines (SDP)"
    )

    # Replace @dlt.table and @dlt.view with SDP equivalents
    for t in table_analysis:
        layer_prefix = f"{t['schema']}."

        if t['should_be_view']:
            # Intermediate views → @dp.materialized_view (persistent, queryable)
            # These are Silver layer transformations that should be materialized for downstream use
            old_decorator = f"@dlt.view(name='{t['name']}'"
            new_decorator = f"@dp.materialized_view(name='{layer_prefix}{t['name']}'"
            code = code.replace(old_decorator, new_decorator)

            # Also handle double quotes
            old_decorator_dq = f'@dlt.view(name="{t["name"]}"'
            new_decorator_dq = f'@dp.materialized_view(name="{layer_prefix}{t["name"]}"'
            code = code.replace(old_decorator_dq, new_decorator_dq)
        else:
            # Persistent tables → @dp.table (Bronze inputs, Gold outputs)
            old_decorator = f"@dlt.table(name='{t['name']}'"
            new_decorator = f"@dp.table(name='{layer_prefix}{t['name']}'"
            code = code.replace(old_decorator, new_decorator)

            # Also handle double quotes
            old_decorator_dq = f'@dlt.table(name="{t["name"]}"'
            new_decorator_dq = f'@dp.table(name="{layer_prefix}{t["name"]}"'
            code = code.replace(old_decorator_dq, new_decorator_dq)

    return code

print("✅ API converter ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Enhanced Template Generator

# COMMAND ----------

def generate_intelligent_template(
    original_sas_filename,
    converted_code,
    sas_source_text,
    catalog,
    schema_bronze,
    schema_silver,
    schema_gold,
    enable_views=True,
    api_style="dlt",
    author="3Cloud SAS Migration Team"
):
    """
    Generates production-ready template with layer detection and view optimization

    Args:
        api_style: "dlt" (standard) or "dp" (pyspark.pipelines style)
    """

    base_name = original_sas_filename.replace('.sas', '')
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Analyze converted code to detect tables and their layers
    table_analysis = []

    # Simple pattern to find @dlt.table or @dlt.view declarations
    table_pattern = r'@dlt\.(table|view)\s*\(\s*name\s*=\s*["\']([^"\']+)["\']'
    matches = re.finditer(table_pattern, converted_code)

    for match in matches:
        table_type = match.group(1)
        table_name = match.group(2)

        # Detect layer
        layer = detect_medallion_layer(table_name, sas_source_text, converted_code)

        # Detect if should be view
        should_be_view = enable_views and detect_should_be_view(table_name, sas_source_text, converted_code)

        # Determine schema
        if layer == "bronze":
            schema = schema_bronze
        elif layer == "gold":
            schema = schema_gold
        else:
            schema = schema_silver

        table_analysis.append({
            'name': table_name,
            'layer': layer,
            'schema': schema,
            'should_be_view': should_be_view,
            'original_type': table_type
        })

    # Build analysis summary
    analysis_summary = "\n".join([
        f"# - {t['name']:30} → {t['layer']:6} layer ({t['schema']})  [{'VIEW' if t['should_be_view'] else 'TABLE'}]"
        for t in table_analysis
    ])

    if not analysis_summary:
        analysis_summary = "# No tables detected in converted code"

    # STEP 1: Post-process converted code to fix common issues
    transformed_code = post_process_converted_code(converted_code, table_analysis, sas_source_text, api_style=api_style, schema_bronze=schema_bronze, schema_silver=schema_silver, schema_gold=schema_gold)

    # STEP 2: Transform the converted code: replace @dlt.table with @dlt.view where appropriate
    for t in table_analysis:
        if t['should_be_view']:
            # Replace @dlt.table with @dlt.view for this specific table
            old_decorator = f"@dlt.table(name='{t['name']}'"
            new_decorator = f"@dlt.view(name='{t['name']}'"
            transformed_code = transformed_code.replace(old_decorator, new_decorator)

            # Also handle double quotes
            old_decorator_dq = f'@dlt.table(name="{t["name"]}"'
            new_decorator_dq = f'@dlt.view(name="{t["name"]}"'
            transformed_code = transformed_code.replace(old_decorator_dq, new_decorator_dq)

    # Build the template
    template = f'''# ==============================================================================
# TRANSFORMED SAS PIPELINE - PRODUCTION READY (WITH INTELLIGENT LAYER DETECTION)
# ==============================================================================
# Name:           transformed_{base_name}.py
# Original File:  {original_sas_filename}
# Purpose:        Transformed from SAS to Spark Declarative Pipeline (SDP)
# Author:         {author}
# Transformed:    {current_date}
# Target:         Databricks SDP (Spark Declarative Pipelines)
# Model:          sas2databricks
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# {current_date} | {author} | Initial transformation from SAS
# ------------------------------------------------------------------------------
#
# Medallion Layer Analysis:
# ------------------------------------------------------------------------------
{analysis_summary}
# ------------------------------------------------------------------------------
#
# Notes:
# - Layer detection: Bronze (raw), Silver (transforms), Gold (aggregates)
# - View optimization: Intermediate tables converted to views for efficiency
# - Review business logic carefully before deploying to production
# - Test with sample data before running on full dataset
#
# ==============================================================================

# ==============================================================================
# PARAMETERS (Widget-Driven)
# ==============================================================================

# Unity Catalog configuration (default values, override with widgets)
CATALOG = "{catalog}"
SCHEMA_BRONZE = "{schema_bronze}"    # Raw data ingestion layer (e.g., sas_tanderson_bronze)
SCHEMA_SILVER = "{schema_silver}"    # Business logic transformation layer (e.g., sas_tanderson_silver)
SCHEMA_GOLD = "{schema_gold}"        # Aggregated metrics and reporting layer (e.g., sas_tanderson_gold)

# Source paths
SOURCE_VOLUME = f"/Volumes/{{CATALOG}}/{{SCHEMA_BRONZE}}/sas_migration"
INPUT_PATH = f"{{SOURCE_VOLUME}}/input"

# Data quality settings
ENABLE_EXPECTATIONS = True
EXPECTATION_ACTION = "drop"  # Options: "drop", "fail", "warn"

# View optimization
ENABLE_VIEWS = {enable_views}  # Convert intermediate tables to views

# ==============================================================================
# IMPORTS
# ==============================================================================
# API Style: {api_style}
#
# DLT Style (backward compatible, still works):
#   import dlt
#   @dlt.table, @dlt.view
#
# DP/SDP Style (Apache Spark 4.1+ open standard - RECOMMENDED):
#   from pyspark import pipelines as dp
#   @dp.table (persistent tables)
#   @dp.materialized_view (persistent views)
#   @dp.temporary_view (temporary views)
#
# Note: Databricks contributed SDP to Apache Spark as an open standard.
#       Lakeflow Pipelines (formerly Delta Live Tables) is built on SDP.
#       Both APIs work, but dp/SDP is recommended for forward compatibility.

import dlt
from pyspark.sql import functions as F
from pyspark.sql import types as T
from datetime import datetime

# ==============================================================================
# ORIGINAL SAS CODE (for reference)
# ==============================================================================
"""
{sas_source_text}
"""

# ==============================================================================
# CONVERTED PIPELINE CODE (from sas2databricks, enhanced with view optimization)
# ==============================================================================

{transformed_code}

# ==============================================================================
# HELPER: Add Bronze Metadata Columns
# ==============================================================================

def add_bronze_metadata(df, source_file="{original_sas_filename}", layer="bronze"):
    """
    Adds standard metadata columns for audit trail

    Args:
        df: Input DataFrame
        source_file: Name of source SAS file
        layer: Medallion layer (bronze, silver, gold)

    Returns:
        DataFrame with metadata columns
    """
    return (df
        .withColumn("bronze_ingestion_timestamp", F.current_timestamp())
        .withColumn("bronze_source_file", F.lit(source_file))
        .withColumn("bronze_ingestion_date", F.current_date())
        .withColumn("medallion_layer", F.lit(layer))
    )

# ==============================================================================
# LAYER-SPECIFIC SCHEMAS
# ==============================================================================

def get_schema_for_layer(layer):
    """Returns appropriate schema based on medallion layer"""
    if layer == "bronze":
        return SCHEMA_BRONZE
    elif layer == "gold":
        return SCHEMA_GOLD
    else:
        return SCHEMA_SILVER

# ==============================================================================
# ENHANCED TABLES/VIEWS (with layer-specific schemas and metadata)
# ==============================================================================

# TODO: Review the tables above and enhance with:
# 1. Correct schema based on detected layer
# 2. Bronze metadata for audit trail
# 3. Data quality expectations
#
# Example pattern:
#
# @dlt.view(  # Changed from table to view for intermediate processing
#     name="silver_intermediate_claims",
#     comment="Intermediate transformation - Silver layer"
# )
# def silver_intermediate_claims():
#     df = spark.table("LIVE.bronze_claims")
#     # Add transformation logic
#     return df.filter(F.col("status") == "active")
#
# @dlt.table(
#     name="gold_claims_summary",
#     comment="Final aggregated metrics - Gold layer",
#     schema=f"`{{CATALOG}}`.{{SCHEMA_GOLD}}"  # Write to Gold schema
# )
# @dlt.expect_or_drop("valid_count", "claim_count > 0")
# def gold_claims_summary():
#     df = spark.table("LIVE.silver_intermediate_claims")
#     result = df.groupBy("region").agg(
#         F.count("*").alias("claim_count"),
#         F.sum("amount").alias("total_amount")
#     )
#     return add_bronze_metadata(result, layer="gold")

# ==============================================================================
# DETECTED TABLE ANALYSIS
# ==============================================================================
"""
Intelligent layer detection results:

Table Name                     | Layer  | Schema               | Type
---------------------------------------------------------------------------
'''

    # Build table analysis section
    for t in table_analysis:
        template += f"{t['name']:30} | {t['layer']:6} | {t['schema']:20} | {'VIEW' if t['should_be_view'] else 'TABLE':5}\n"

    if not table_analysis:
        template += "No tables detected\n"

    template += '''
Recommendations:
- Bronze tables: Add bronze_metadata for audit trail
- Silver tables: Add data quality expectations
- Gold tables: Verify aggregation logic matches SAS
- Views: Use for intermediate transformations (no persistence)

# ==============================================================================
# DATA QUALITY EXPECTATIONS
# ==============================================================================

# Add expectations based on SAS validation rules
# Example patterns by layer:
#
# Bronze (data quality at ingestion):
# @dlt.expect_or_drop("valid_dates", "date_col >= '2020-01-01'")
# @dlt.expect_or_drop("no_nulls_in_key", "key_col IS NOT NULL")
#
# Silver (business rule validation):
# @dlt.expect_or_warn("valid_status", "status IN ('active', 'pending', 'closed')")
# @dlt.expect_or_drop("positive_amounts", "amount > 0")
#
# Gold (aggregation validation):
# @dlt.expect("min_record_count", "count > 0")
# @dlt.expect("valid_totals", "total_amount >= 0")

# ==============================================================================
# END OF CONVERTED PIPELINE
# ==============================================================================
#
# Deployment checklist:
# □ Review layer assignments (Bronze/Silver/Gold)
# □ Verify schema configuration for each layer
# □ Update view vs table decisions
# □ Add bronze metadata to appropriate tables
# □ Test with sample data
# □ Validate output matches SAS results
# □ Update widgets for prod deployment
# □ Deploy via DAB or pipeline UI
#
# ==============================================================================
"""
'''

    # Convert to dp API style if requested
    if api_style == "dp":
        template = convert_dlt_to_dp_api(template, table_analysis)

    return template

print("✅ Enhanced template generator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate DAB Pipeline YAML

# COMMAND ----------

def generate_dab_pipeline_yaml(
    sas_filename: str,
    python_filename: str,
    project_name: str = "sas_migration",
    output_dir: str = "./resources/pipelines"
):
    """
    Auto-generate Databricks Asset Bundle pipeline YAML for a converted SAS file.

    Args:
        sas_filename: Original SAS filename (e.g., "claims_adjudication_comprehensive.sas")
        python_filename: Generated Python filename (e.g., "converted_claims_adjudication_comprehensive.py")
        project_name: Project identifier for tagging
        output_dir: Directory to write YAML file

    Returns:
        Path to generated YAML file
    """
    import os
    import re

    # Create pipeline name from SAS filename
    base_name = sas_filename.replace('.sas', '').replace('_', ' ').title().replace(' ', '')
    pipeline_key = f"pipeline_{base_name.lower()}"
    pipeline_display_name = f"sas_{base_name.lower()}_${{var.developer_id}}_pipeline"

    yaml_content = f"""# ══════════════════════════════════════════════════════════════════
# Pipeline: {base_name}
# ══════════════════════════════════════════════════════════════════
# Auto-generated from: {sas_filename}
# Converted to: {python_filename}
# Organization: 3Cloud Solutions
# ══════════════════════════════════════════════════════════════════

resources:
  pipelines:
    {pipeline_key}:
      name: "{pipeline_display_name}"
      catalog: ${{var.catalog}}
      target: default

      configuration:
        catalog_name: ${{var.catalog}}
        schema_bronze: ${{resources.schemas.sas_bronze.name}}
        schema_silver: ${{resources.schemas.sas_silver.name}}
        schema_gold: ${{resources.schemas.sas_gold.name}}
        enable_expectations: "true"
        expectation_action: "drop"
        enable_views: "true"

      libraries:
        - file:
            path: ./transformations/{python_filename}

      serverless: true
      photon: true

      tags:
        project: "{project_name}"
        source_file: "{sas_filename}"
        developer_id: ${{var.developer_id}}
        organization: "3cloud"
        pipeline_type: "data_transformation"
        auto_generated: "true"

      development: true

# ══════════════════════════════════════════════════════════════════
# Usage:
#   1. Merge this into databricks.yml under resources.pipelines
#   2. Deploy: databricks bundle deploy -t dev --var developer_id=yourname
#   3. Run: databricks pipelines start {pipeline_display_name}
#
# Or keep as separate file and include in databricks.yml:
#   include:
#     - ./resources/pipelines/{pipeline_key}.yml
# ══════════════════════════════════════════════════════════════════
"""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Write YAML file
    yaml_filename = f"{pipeline_key}.yml"
    yaml_path = os.path.join(output_dir, yaml_filename)

    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    return yaml_path

print("✅ DAB pipeline YAML generator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Scan for SAS Files

# COMMAND ----------

# Re-import after Python restart
from sas2databricks import migrate
from datetime import datetime
import os
import re
import shutil

# Get widget values (after restart)
CATALOG = dbutils.widgets.get("catalog")
SCHEMA_PREFIX = dbutils.widgets.get("schema_prefix")
ENABLE_VIEWS = dbutils.widgets.get("enable_views") == "true"
API_STYLE = dbutils.widgets.get("api_style")

# Build schema names from prefix
SCHEMA_BRONZE = f"{SCHEMA_PREFIX}_bronze"
SCHEMA_SILVER = f"{SCHEMA_PREFIX}_silver"
SCHEMA_GOLD = f"{SCHEMA_PREFIX}_gold"

# Redefine paths after Python restart
volume_base = f"/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration"
input_base = f"{volume_base}/staging"
output_dir = f"{volume_base}/converted"
archive_dir = f"{volume_base}/archive"

# ==============================================================================
# ARCHIVE ON SUCCESS - Move processed files to prevent reprocessing
# ==============================================================================
# Set to True to enable archival (disabled for testing)
# When enabled: successfully converted files are moved to archive/ with timestamp
# This prevents reprocessing the same file on subsequent runs
#
# Toggle: Set to True in production
# Files archived as: <filename>_YYYYMMDD_HHMMSS.sas
ARCHIVE_ON_SUCCESS = False  # ← Set to True in production
# ==============================================================================

print("="*80)
print("🔍 SCANNING FOR SAS FILES")
print("="*80)
print()
print(f"📁 Looking in: {input_base}")
print()

# Scan staging/ for SAS files
sas_files = []
for root, dirs, files in os.walk(input_base):
    for file in files:
        if file.endswith('.sas'):
            full_path = os.path.join(root, file)
            rel = os.path.relpath(root, input_base)
            project = rel if rel != '.' else 'root'
            sas_files.append({
                'filename': file,
                'full_path': full_path,
                'project': project,
            })

if len(sas_files) == 0:
    print("❌ No SAS files found in staging/")
    print()
    print("👉 Upload SAS files to:")
    print(f"   {input_base}")
    print()
    print("Then re-run this notebook.")
    print()
    dbutils.notebook.exit("No files to convert")

print(f"✅ Found {len(sas_files)} SAS file(s):")
for f in sas_files:
    print(f"  - {f['filename']}")
print()

print("="*80)
print()

for i, f in enumerate(sas_files, 1):
    print(f"{i}. {f['filename']}")

print()
print("="*80)

if len(sas_files) == 0:
    print("⚠️  No files to convert")
    dbutils.notebook.exit("No files to convert")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Convert with Intelligent Layer Detection

# COMMAND ----------

print("="*80)
print("🔄 CONVERTING WITH INTELLIGENT LAYER DETECTION + BUG FIXES")
print("="*80)
print()

results = []

for i, sas_file in enumerate(sas_files, 1):
    print(f"\n[{i}/{len(sas_files)}] Processing: {sas_file['filename']}")
    print("-"*80)

    try:
        # Read SAS source
        with open(sas_file['full_path'], 'r') as f:
            sas_text = f.read()

        print(f"📄 Size: {len(sas_text)} bytes")

        # Convert with sas2databricks
        result = migrate(
            sas_text,
            target="dlt",
            source_path=sas_file['filename']
        )

        print(f"✅ Conversion complete")

        # Generate intelligent template
        production_code = generate_intelligent_template(
            original_sas_filename=sas_file['filename'],
            converted_code=result.code,
            sas_source_text=sas_text,
            catalog=CATALOG,
            schema_bronze=SCHEMA_BRONZE,
            schema_silver=SCHEMA_SILVER,
            schema_gold=SCHEMA_GOLD,
            enable_views=ENABLE_VIEWS,
            api_style=API_STYLE,
            author="3Cloud SAS Migration Team"
        )

        # Create output filename
        base_name = sas_file['filename'].replace('.sas', '')
        output_filename = f"transformed_{base_name}.py"
        output_path = os.path.join(output_dir, output_filename)

        # Write enhanced code
        with open(output_path, 'w') as f:
            f.write(production_code)

        print(f"📄 Input:  {sas_file['filename']}")
        print(f"📄 Output: {output_filename}")
        print(f"✨ Enhanced with:")
        print(f"   - Intelligent layer detection (Bronze/Silver/Gold)")
        print(f"   - Three schema variables")
        print(f"   - View optimization for intermediate tables")
        print(f"   - Bronze metadata helper")
        print(f"   - ✅ ALL 5 GENIE FIXES APPLIED:")
        print(f"     ✓ Fix #1: Table references (schema_table → schema.table)")
        print(f"     ✓ Fix #2: Catalog backticks for hyphenated names")
        print(f"     ✓ Fix #3: Date arithmetic (datediff function)")
        print(f"     ✓ Fix #4: Single CASE expressions")
        print(f"     ✓ Fix #5: Duplicate columns (SELECT * EXCEPT)")

        # Generate DAB pipeline YAML
        try:
            yaml_path = generate_dab_pipeline_yaml(
                sas_filename=sas_file['filename'],
                python_filename=output_filename,
                project_name=sas_file['project']
            )
            yaml_filename = os.path.basename(yaml_path)
            print(f"📋 Pipeline YAML: {yaml_filename}")
        except Exception as yaml_err:
            print(f"⚠️  Failed to generate pipeline YAML: {yaml_err}")

        results.append({
            'input': sas_file['filename'],
            'output': output_filename,
            'status': 'success',
            'project': sas_file['project']
        })

        # ==============================================================================
        # ARCHIVE SUCCESSFULLY PROCESSED FILE (if enabled)
        # ==============================================================================
        if ARCHIVE_ON_SUCCESS:
            try:
                # Ensure archive directory exists
                os.makedirs(archive_dir, exist_ok=True)

                # Add timestamp suffix to filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.splitext(sas_file['filename'])[0]
                ext = os.path.splitext(sas_file['filename'])[1]
                archived_filename = f"{base_name}_{timestamp}{ext}"

                # Source and destination paths
                source_path = os.path.join(input_base, sas_file['filename'])
                archive_path = os.path.join(archive_dir, archived_filename)

                # Move file to archive with timestamp
                shutil.move(source_path, archive_path)
                print(f"📦 Archived: {sas_file['filename']} → archive/{archived_filename}")

            except Exception as e:
                print(f"⚠️  Failed to archive {sas_file['filename']}: {e}")
                print(f"   File will remain in staging/")
        # else:
        #     print(f"ℹ️  Archive disabled - file remains in staging/ (testing mode)")
        # ==============================================================================

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'input': sas_file['filename'],
            'output': None,
            'status': 'failed',
            'error': str(e),
            'project': sas_file['project']
        })

print()
print("="*80)
print("✅ INTELLIGENT CONVERSION COMPLETE (WITH BUG FIXES)!")
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Report

# COMMAND ----------

print("="*80)
print("📊 CONVERSION SUMMARY")
print("="*80)
print()

success_count = sum(1 for r in results if r['status'] == 'success')
failed_count = sum(1 for r in results if r['status'] == 'failed')

print(f"Total files:     {len(results)}")
print(f"✅ Successful:   {success_count}")
print(f"❌ Failed:       {failed_count}")
print()

# Archival status
if ARCHIVE_ON_SUCCESS:
    print(f"📦 Archival:     ENABLED - Successful files moved to archive/")
else:
    print(f"📦 Archival:     DISABLED (testing mode) - Files remain in staging/")
    print(f"   → Set ARCHIVE_ON_SUCCESS = True to enable archival in production")
print()

if success_count > 0:
    print("="*80)
    print("✅ SUCCESSFUL CONVERSIONS (with intelligent enhancements + bug fixes)")
    print("="*80)
    print()

    for r in results:
        if r['status'] == 'success':
            print(f"  {r['input']:40} → {r['output']}")
    print()

if failed_count > 0:
    print("="*80)
    print("❌ FAILED CONVERSIONS")
    print("="*80)
    print()

    for r in results:
        if r['status'] == 'failed':
            print(f"  {r['input']:40} - {r['error']}")
    print()

print("="*80)
print(f"📁 All converted files saved to:")
print(f"   {output_dir}")
print("="*80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps

# COMMAND ----------

print("="*80)
print("✅ INTELLIGENT CONVERSION COMPLETE (WITH ALL BUG FIXES)!")
print("="*80)
print()
print("📋 What you have now:")
print(f"  ✅ {success_count} SAS files converted with intelligent enhancements")
print(f"  ✅ Automatic Bronze/Silver/Gold layer detection")
print(f"  ✅ Three schema variables (widget-driven)")
print(f"  ✅ View optimization for intermediate tables")
print(f"  ✅ Bronze metadata helper")
print(f"  ✅ ALL 13 BUG FIXES (Fully Automatic):")
print(f"     • MERGE replacement regex fixed")
print(f"     • RETAIN replacement regex fixed")
print(f"     • Missing DATALINES tables auto-inserted")
print(f"     • PROC FORMAT UDF import corrected")
print(f"     • Summary shows all generated tables")
print(f"  ✅ All saved to: {output_dir}")
print()
print("="*80)
print("🎯 NEXT STEPS")
print("="*80)
print()
print("1️⃣  Review Layer Assignments")
print("   - Open converted files")
print("   - Check 'Medallion Layer Analysis' section")
print("   - Verify Bronze/Silver/Gold assignments")
print()
print("2️⃣  Configure Schemas (Optional)")
print("   - Update widgets to use separate schemas:")
print("     • Bronze: your_catalog.bronze_layer")
print("     • Silver: your_catalog.silver_layer")
print("     • Gold: your_catalog.gold_layer")
print("   - Re-run conversion with new values")
print()
print("3️⃣  Review View vs Table Decisions")
print("   - Check which tables were marked as views")
print("   - Intermediate 'work.' tables → views")
print("   - Final output tables → tables")
print()
print("4️⃣  Test and Deploy")
print("   - Test converted code")
print("   - Deploy via DAB or UI")
print()
print("="*80)
