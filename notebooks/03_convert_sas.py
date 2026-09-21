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
# MAGIC - ✅ Run `01_setup_volumes.py` first
# MAGIC - ✅ Upload SAS files to `00_inbound/` or `01_staging/`
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
dbutils.widgets.text("schema_bronze", "sas2dbx_migrate", "Bronze Schema")
dbutils.widgets.text("schema_silver", "sas2dbx_migrate", "Silver Schema")
dbutils.widgets.text("schema_gold", "sas2dbx_migrate", "Gold Schema")
dbutils.widgets.text("schema_suffix", "_sas", "Schema Suffix (e.g., _sas for bronze_sas)")
dbutils.widgets.dropdown("enable_views", "true", ["true", "false"], "Enable Views for Intermediate Tables")
dbutils.widgets.dropdown("api_style", "dp", ["dlt", "dp"], "API Style (dlt or dp)")

# Get widget values
CATALOG = dbutils.widgets.get("catalog")
SCHEMA_BRONZE = dbutils.widgets.get("schema_bronze")
SCHEMA_SILVER = dbutils.widgets.get("schema_silver")
SCHEMA_GOLD = dbutils.widgets.get("schema_gold")
SCHEMA_SUFFIX = dbutils.widgets.get("schema_suffix")
ENABLE_VIEWS = dbutils.widgets.get("enable_views") == "true"
API_STYLE = dbutils.widgets.get("api_style")

print("="*80)
print("🎛️  CONFIGURATION FROM WIDGETS")
print("="*80)
print(f"Catalog:              {CATALOG}")
print(f"Bronze Schema:        {SCHEMA_BRONZE}{SCHEMA_SUFFIX}")
print(f"Silver Schema:        {SCHEMA_SILVER}{SCHEMA_SUFFIX}")
print(f"Gold Schema:          {SCHEMA_GOLD}{SCHEMA_SUFFIX}")
print(f"Schema Suffix:        {SCHEMA_SUFFIX}")
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

# Base paths - using new production structure
volume_base = "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"
input_base = f"{volume_base}/01_staging"          # Validated files ready for conversion
output_base = f"{volume_base}/03_converted"        # Conversion output

# Output to needs_review subfolder (quality gate)
output_dir = f"{output_base}/needs_review"
dbutils.fs.mkdirs(output_dir)

print("✅ sas2databricks imported successfully")
print(f"📁 Input (staging):      {input_base}")
print(f"📁 Output (needs_review): {output_dir}")
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
def post_process_converted_code(code, table_analysis, sas_source_text="", api_style="dlt", schema_suffix=""):
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
            fixes_applied.append(f"  • {pattern['output_table']}: {pattern['join_type'].upper()} JOIN on {pattern['by_vars']}")

    # DETECT RETAIN patterns
    retain_patterns = translate_retain_to_window(sas_source_text)

    if retain_patterns:
        fixes_applied.append(f"Detected {len(retain_patterns)} RETAIN pattern(s) for running totals")
        for pattern in retain_patterns:
            fixes_applied.append(f"  • {pattern['output_table']}: {pattern['retain_var']} accumulates {pattern['accum_source']}")

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

                new_function = f"\n{decorator}(name='bronze{schema_suffix}.{table_name}', comment='Auto-generated from SAS DATALINES')\n"
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

    # GENERATE MERGE join code and replace broken SQL - BUG FIX #1
    if merge_patterns:
        # Use api_style from function parameter (already set from widget)
        # No need to detect - the parameter is passed from API_STYLE widget

        for pattern in merge_patterns:
            output_table = pattern['output_table']

            # Generate correct join code
            correct_code = generate_merge_join_code(pattern, table_analysis, api_style, schema_suffix)

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
            correct_code = generate_retain_window_code(pattern, table_analysis, api_style, schema_suffix)

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

    # Pattern D: Table reference normalization (work.table → work_table)
    # Fix broken table references in SQL FROM clauses
    table_ref_fixes = 0

    # Fix: FROM work.table → FROM work_table
    pattern = r'FROM\s+(work|clm|lib)\.(\w+)'
    def normalize_table_ref(match):
        return f'FROM {match.group(1)}_{match.group(2)}'

    new_code = re.sub(pattern, normalize_table_ref, code, flags=re.IGNORECASE)
    if new_code != code:
        table_ref_fixes = len(re.findall(pattern, code, re.IGNORECASE))
        code = new_code
        fixes_applied.append(f"Normalized {table_ref_fixes} table reference(s) (lib.table → lib_table)")

    # Fix: JOIN work.table → JOIN work_table
    pattern = r'JOIN\s+(work|clm|lib)\.(\w+)'
    def normalize_join_ref(match):
        return f'JOIN {match.group(1)}_{match.group(2)}'

    new_code = re.sub(pattern, normalize_join_ref, code, flags=re.IGNORECASE)
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
            # Match table name that's NOT already qualified (no dot before it)
            # Patterns to match:
            # - FROM work_claims_elig
            # - JOIN work_members
            # - FROM bronze.work_members → don't replace (already qualified)

            # Replace unqualified references
            patterns = [
                (rf'\bFROM\s+{table_name}\b', f'FROM {layer}{schema_suffix}.{table_name}'),
                (rf'\bJOIN\s+{table_name}\b', f'JOIN {layer}{schema_suffix}.{table_name}'),
                (rf'\bJOIN\s+{table_name}\s+AS\b', f'JOIN {layer}{schema_suffix}.{table_name} AS'),
            ]

            for pattern, replacement in patterns:
                qualified_sql = re.sub(pattern, replacement, qualified_sql, flags=re.IGNORECASE)

        # Replace in code (be careful to match exact block)
        code = code.replace(sql_block, qualified_sql)

    if sql_blocks:
        fixes_applied.append(f"Qualified {len(sql_blocks)} spark.sql() table reference(s) with layer+suffix")

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
        # No if = FULL OUTER JOIN
        join_type = 'full'
        where_clause = None

        if 'if ' in post_merge_logic.lower():
            # Extract IF condition
            if_match = re.search(r'if\s+(.*?);', post_merge_logic, re.IGNORECASE)
            if if_match:
                condition = if_match.group(1).strip()
                # Check for simple flag tests
                if len(tables) >= 2:
                    flag1 = tables[0]['in_flag']
                    flag2 = tables[1]['in_flag'] if len(tables) > 1 else None

                    if condition == flag1 and flag2:
                        join_type = 'left'
                        where_clause = f"{tables[0]['name']}.{by_vars} IS NOT NULL"
                    elif 'and' in condition.lower() and flag1 and flag2:
                        join_type = 'inner'

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

    Pattern: retain var; if first.key then var=0; var+amount;
    Translation: SUM(amount) OVER (PARTITION BY key ORDER BY sort_col ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    """
    import re

    retain_patterns = []

    # Find DATA step with RETAIN
    # Pattern: data output; set input; by key; retain var; if first.key then var=initial; var + amount; run;
    # CRITICAL FIX: Use negative lookahead ((?:(?!run;).)* to prevent crossing DATA step boundaries
    # AND use (\w+(?:\s+\w+)*) for BY vars to only match word tokens
    retain_pattern = r'data\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)set\s+(\w+\.\w+|\w+);((?:(?!run;).)*?)by\s+(\w+(?:\s+\w+)*)\s*;((?:(?!run;).)*?)retain\s+(\w+)((?:(?!run;).)*?)(\w+)\s*\+\s*(\w+)((?:(?!run;).)*?)run;'

    for match in re.finditer(retain_pattern, sas_source_text, re.IGNORECASE | re.DOTALL):
        output_table = match.group(1)
        input_table = match.group(3)  # Updated: was group(2)
        by_vars = match.group(5).strip()  # Updated: was group(3)
        retain_var = match.group(7).strip()  # Updated: was group(4)
        # Group 9 is the variable being incremented (e.g., ytd_paid)
        # Group 10 is the accumulation source (e.g., billed_amount)
        accum_var = match.group(9).strip()  # Updated: was group(5)
        accum_source = match.group(10).strip()  # Updated: was group(6)

        # Verify the accumulation variable matches the retain variable
        if accum_var == retain_var:

            # Determine ordering - look for PROC SORT before this DATA step
            sort_pattern = rf'proc\s+sort\s+data={input_table}.*?by\s+(.*?);'
            sort_match = re.search(sort_pattern, sas_source_text[:match.start()], re.IGNORECASE | re.DOTALL)
            order_by = sort_match.group(1).strip() if sort_match else by_vars

            retain_patterns.append({
                'output_table': output_table.replace('.', '_'),
                'input_table': input_table.replace('.', '_'),
                'partition_by': by_vars,
                'order_by': order_by,
                'retain_var': retain_var,
                'accum_source': accum_source
            })

    return retain_patterns

print("✅ RETAIN translator ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Code Generation - Generate Correct PySpark from Detected Patterns

# COMMAND ----------

def generate_merge_join_code(merge_pattern, table_analysis, api_style="dp", schema_suffix=""):
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

    # Generate function header
    output_layer = get_table_layer(output_table)
    decorator = "@dp.materialized_view" if api_style == "dp" else "@dlt.view"
    code = f'{decorator}(name=\'{output_layer}{schema_suffix}.{output_table}\')\n'
    code += f'def {output_table}():\n'
    code += f'    """Converted from SAS DATA step MERGE"""\n'

    # Read tables (V7: Layer-aware with schema suffix)
    for i, table in enumerate(tables):
        var_name = f"table{i+1}" if len(tables) > 2 else ["left_df", "right_df"][i] if len(tables) == 2 else "df"
        table_layer = get_table_layer(table["name"])
        code += f'    {var_name} = spark.read.table("{table_layer}{schema_suffix}.{table["name"]}")'

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
                right_cols = tables[1].get('keep_vars', [])
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

def generate_retain_window_code(retain_pattern, table_analysis, api_style="dp", schema_suffix=""):
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

    decorator = "@dp.table" if api_style == "dp" else "@dlt.table"

    # Split partition_by and order_by columns (space-separated) and quote each
    partition_cols = ', '.join([f'"{col.strip()}"' for col in partition_by.split()])
    order_cols = ', '.join([f'"{col.strip()}"' for col in order_by.split()])

    # V7: Layer-aware output
    output_layer = get_table_layer(output_table)
    input_layer = get_table_layer(input_table)

    code = f'{decorator}(name=\'{output_layer}{schema_suffix}.{output_table}\')\n'
    code += f'def {output_table}():\n'
    code += f'    """Converted from SAS RETAIN - running total per {partition_by}"""\n'
    code += f'    from pyspark.sql.window import Window\n'
    code += f'    \n'
    code += f'    # Window for running total (ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)\n'
    code += f'    window = Window.partitionBy({partition_cols}) \\\n'
    code += f'                   .orderBy({order_cols}) \\\n'
    code += f'                   .rowsBetween(Window.unboundedPreceding, Window.currentRow)\n'
    code += f'    \n'
    code += f'    # V7: Layer-aware table reference\n'
    code += f'    return spark.read.table("{input_layer}{schema_suffix}.{input_table}") \\\n'
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
        layer_prefix = f"{t['layer']}."

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
    schema_suffix="",
    enable_views=True,
    api_style="dlt",
    author="SAS Migration Team"
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
    transformed_code = post_process_converted_code(converted_code, table_analysis, sas_source_text, api_style=api_style, schema_suffix=schema_suffix)

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
# CONVERTED SAS PIPELINE - PRODUCTION READY (WITH INTELLIGENT LAYER DETECTION)
# ==============================================================================
# Name:           converted_{base_name}.py
# Original File:  {original_sas_filename}
# Purpose:        Converted from SAS to Spark Declarative Pipeline (SDP)
# Author:         {author}
# Converted:      {current_date}
# Target:         Databricks SDP (Spark Declarative Pipelines)
# Model:          sas2databricks
#
# Change History:
# ------------------------------------------------------------------------------
# Date       | Author              | Description
# ------------------------------------------------------------------------------
# {current_date} | {author} | Initial conversion from SAS
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
SCHEMA_BRONZE = "{schema_bronze}"    # Raw data ingestion layer
SCHEMA_SILVER = "{schema_silver}"    # Business logic transformation layer
SCHEMA_GOLD = "{schema_gold}"        # Aggregated metrics and reporting layer
SCHEMA_SUFFIX = "{schema_suffix}"    # Schema suffix (e.g., "_sas" for bronze_sas/silver_sas/gold_sas)

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
# MAGIC ## Validate and Stage Files from Inbound

# COMMAND ----------

# Re-import after Python restart
from sas2databricks import migrate
from datetime import datetime
import os
import re
import shutil

# Get widget values (after restart)
CATALOG = dbutils.widgets.get("catalog")
SCHEMA_BRONZE = dbutils.widgets.get("schema_bronze")
SCHEMA_SILVER = dbutils.widgets.get("schema_silver")
SCHEMA_GOLD = dbutils.widgets.get("schema_gold")
SCHEMA_SUFFIX = dbutils.widgets.get("schema_suffix")
ENABLE_VIEWS = dbutils.widgets.get("enable_views") == "true"
API_STYLE = dbutils.widgets.get("api_style")

# Redefine paths after Python restart
volume_base = f"/Volumes/{CATALOG}/sas2dbx_migrate/sas_migration"
input_base = f"{volume_base}/01_staging"
output_dir = f"{volume_base}/03_converted/needs_review"
archive_dir = f"{volume_base}/04_archive"

# ==============================================================================
# ARCHIVE ON SUCCESS - Move processed files to prevent reprocessing
# ==============================================================================
# Set to True to enable archival (disabled for testing)
# When enabled: successfully converted files are moved to 04_archive/
# This prevents reprocessing the same file on subsequent runs
ARCHIVE_ON_SUCCESS = False  # ← Set to True in production
# ==============================================================================

print("="*80)
print("🔍 STEP 1: CHECK FOR CONCURRENT RUNS")
print("="*80)
print()

# Check if another conversion is running (02_processing has files)
processing_dir = f"{volume_base}/02_processing"
try:
    processing_files = [f for f in os.listdir(processing_dir) if f.endswith('.sas')]
    if len(processing_files) > 0:
        print(f"⚠️  LOCK DETECTED: {len(processing_files)} files in 02_processing/")
        print()
        print("Another conversion run may be in progress.")
        print("Files found:")
        for pf in processing_files[:5]:
            print(f"  - {pf}")
        if len(processing_files) > 5:
            print(f"  ... and {len(processing_files) - 5} more")
        print()
        print("⚠️  If this is a stale lock (crashed run), manually clean 02_processing/")
        print("⚠️  Otherwise, wait for the other run to complete.")
        print()
        dbutils.notebook.exit("LOCKED: Another conversion in progress")
except FileNotFoundError:
    print("✅ No lock detected (02_processing/ is empty)")
    print()

print("="*80)
print("🔍 STEP 2: SCAN INBOUND FOR NEW FILES")
print("="*80)
print()

# Scan 00_inbound/ recursively for SAS files
inbound_dir = f"{volume_base}/00_inbound"


def scan_for_sas_files(directory):
    """Recursively find all .sas files"""
    sas_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.sas'):
                full_path = os.path.join(root, file)
                sas_files.append({
                    'filename': file,
                    'full_path': full_path,
                    'size': os.path.getsize(full_path)
                })
    return sas_files

inbound_files = scan_for_sas_files(inbound_dir)

print(f"Found {len(inbound_files)} SAS files in 00_inbound/")
if inbound_files:
    for f in inbound_files[:10]:
        print(f"  - {f['filename']:45} ({f['size']:>8} bytes)")
    if len(inbound_files) > 10:
        print(f"  ... and {len(inbound_files) - 10} more")
print()

# Also check staging
staging_files = scan_for_sas_files(input_base)

print(f"Found {len(staging_files)} SAS files already in 01_staging/")
print()

if len(inbound_files) == 0 and len(staging_files) == 0:
    print("❌ No SAS files found in 00_inbound/ or 01_staging/")
    print()
    print("👉 Upload SAS files to:")
    print(f"   {inbound_dir}/manual_uploads/")
    print()
    print("   Or run: 02_upload_sas_files.py")
    print()
    dbutils.notebook.exit("No files to convert")

print("="*80)
print("🔄 STEP 3: VALIDATE AND MOVE TO STAGING")
print("="*80)
print()

validated = 0
skipped = 0

for f in inbound_files:
    print(f"Validating: {f['filename']}")

    # Basic validation
    if f['size'] == 0:
        print(f"  ⚠️  SKIP: Zero size")
        skipped += 1
        continue

    # Move to staging
    staging_path = os.path.join(input_base, f['filename'])

    # Check if already exists in staging
    if os.path.exists(staging_path):
        print(f"  ⚠️  SKIP: Already in staging")
        skipped += 1
        continue

    try:
        # Move file
        os.rename(f['full_path'], staging_path)
        print(f"  ✅ Moved to staging")
        validated += 1
    except Exception as e:
        print(f"  ❌ Move failed: {e}")
        skipped += 1

print()
print(f"✅ Validated and staged: {validated} files")
print(f"⚠️  Skipped: {skipped} files")
print()

# Now scan staging for all files (old + newly moved)
print("="*80)
print("🔍 STEP 4: SCAN STAGING FOR CONVERSION")
print("="*80)
print()

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

print(f"🔍 FOUND {len(sas_files)} SAS FILES IN STAGING")
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
            schema_suffix=SCHEMA_SUFFIX,
            enable_views=ENABLE_VIEWS,
            api_style=API_STYLE,
            author="SAS Migration Team"
        )

        # Create output filename
        base_name = sas_file['filename'].replace('.sas', '')
        output_filename = f"converted_{base_name}.py"
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
        print(f"   - ✅ ALL 5 BUG FIXES APPLIED")

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

                # Source and destination paths
                source_path = os.path.join(input_base, sas_file['filename'])
                archive_path = os.path.join(archive_dir, sas_file['filename'])

                # Move file to archive
                shutil.move(source_path, archive_path)
                print(f"📦 Archived: {sas_file['filename']} → 04_archive/")

            except Exception as e:
                print(f"⚠️  Failed to archive {sas_file['filename']}: {e}")
                print(f"   File will remain in 01_staging/")
        # else:
        #     print(f"ℹ️  Archive disabled - file remains in 01_staging/ (testing mode)")
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
    print(f"📦 Archival:     ENABLED - Successful files moved to 04_archive/")
else:
    print(f"📦 Archival:     DISABLED (testing mode) - Files remain in 01_staging/")
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
print(f"  ✅ ALL 5 CRITICAL BUG FIXES:")
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
