# Scripts Directory

Utility scripts for SAS to Databricks migration setup, validation, and troubleshooting.

## Directory Structure

```
scripts/
├── setup/              # Initial configuration and connection testing
├── validation/         # Pre-deployment validation checks
├── utilities/          # Operational helpers
└── development/        # Development-time tools (future)
```

## Setup Scripts

**Location:** `scripts/setup/`

### test_connection.py

Test Databricks connectivity and authentication.

```bash
python scripts/setup/test_connection.py
```

Validates:
- OAuth authentication via service principal
- Workspace access
- Unity Catalog visibility
- SQL Warehouse connectivity

**When to use:** First step after cloning the repository, or when troubleshooting auth issues.

---

### create_schemas.py

Create bronze/silver/gold schemas with proper naming convention.

```bash
# Development schemas
python scripts/setup/create_schemas.py --developer-id tanderson

# Production schemas  
python scripts/setup/create_schemas.py --developer-id prod --catalog sas_migrate

# Preview only (dry-run)
python scripts/setup/create_schemas.py --developer-id tanderson --dry-run
```

**Arguments:**
- `--developer-id`: Your identifier (creates `sas_{id}_bronze/silver/gold`)
- `--catalog`: Target catalog (default: `na-dbxtraining`)
- `--schema-prefix`: Schema prefix (default: `sas`)
- `--dry-run`: Preview without creating

**When to use:** Before deploying DAB bundle, or when manually creating schemas in a new catalog.

---

## Validation Scripts

**Location:** `scripts/validation/`

### dry_run_pipeline.py

Validate pipeline configuration without executing data transformations.

```bash
python scripts/validation/dry_run_pipeline.py sas_claims_adjudication_tanderson_pipeline
```

**What it checks:**
- Pipeline exists in workspace
- Configuration is valid
- Library paths are accessible
- Schema references are correct
- Python syntax (import check)

**What it DOESN'T check:**
- Runtime data issues (require actual execution)
- Table existence (happens at runtime)

**When to use:** After deploying a pipeline, before running it for the first time.

---

## Utility Scripts

**Location:** `scripts/utilities/`

### list_conversions.py

Show all converted SAS files and their output status.

```bash
# Table format (default)
python scripts/utilities/list_conversions.py

# JSON format
python scripts/utilities/list_conversions.py --format json

# Custom directories
python scripts/utilities/list_conversions.py \
  --output-dir ./transformations \
  --pipeline-dir ./resources/pipelines
```

**Output includes:**
- All converted Python files
- Source SAS filename (from header)
- File size and modification time
- Pipeline YAML status

**When to use:** 
- After running the converter to see what was generated
- Before deployment to verify all files have pipeline YAMLs
- Troubleshooting missing conversions

---

### reset_schemas.py

Drop and recreate schemas for clean restart (⚠️ DESTRUCTIVE).

```bash
# Preview (safe, no changes)
python scripts/utilities/reset_schemas.py --developer-id tanderson

# Execute (requires --confirm)
python scripts/utilities/reset_schemas.py \
  --developer-id tanderson \
  --confirm
```

**Arguments:**
- `--developer-id`: Developer identifier
- `--catalog`: Target catalog (default: `na-dbxtraining`)
- `--schema-prefix`: Schema prefix (default: `sas`)
- `--confirm`: REQUIRED to execute (safety check)

⚠️ **WARNING:** This deletes ALL tables and data in the schemas via `DROP SCHEMA CASCADE`.

**When to use:**
- Clean development environment restart
- Reset after failed migration attempt
- Clear test data between runs

**When NOT to use:**
- Production environments (never!)
- Schemas with data you need to keep

---

## Common Workflows

### First-Time Setup

```bash
# 1. Test connection
python scripts/setup/test_connection.py

# 2. Create schemas
python scripts/setup/create_schemas.py --developer-id yourname

# 3. Deploy bundle
databricks bundle deploy -t dev --var developer_id=yourname

# 4. Run converter
databricks bundle run sas_dbx_code_translator -t dev

# 5. List results
python scripts/utilities/list_conversions.py

# 6. Validate pipeline
python scripts/validation/dry_run_pipeline.py sas_claims_adjudication_yourname_pipeline
```

### Clean Restart

```bash
# 1. Reset schemas (⚠️ deletes data)
python scripts/utilities/reset_schemas.py --developer-id yourname --confirm

# 2. Redeploy
databricks bundle deploy -t dev --var developer_id=yourname

# 3. Re-run converter
databricks bundle run sas_dbx_code_translator -t dev
```

### Troubleshooting

```bash
# Connection issues
python scripts/setup/test_connection.py

# Schema issues
python scripts/setup/create_schemas.py --developer-id yourname --dry-run

# Pipeline issues
python scripts/validation/dry_run_pipeline.py <pipeline_name>

# Conversion status
python scripts/utilities/list_conversions.py
```

---

## Development Scripts

**Location:** `scripts/development/` (planned)

Future additions:
- Local testing harness
- Mock data generators for unit tests
- Performance profiling tools
- Conversion accuracy validators

---

## Environment Requirements

All scripts require:
- Python 3.10+
- `databricks-sdk` package
- Valid `.databrickscfg` with OAuth credentials
- `DATABRICKS_CONFIG_FILE` environment variable set

The DAB bundle automatically sets these when deployed.

---

## Script Conventions

All scripts follow these patterns:

**Exit codes:**
- `0` = Success
- `1` = Failure

**Output style:**
- Clear headers with emoji indicators
- Actionable error messages
- Next-step recommendations

**Safety:**
- Destructive operations require `--confirm`
- Dry-run modes available where applicable
- Preview output before execution

---

## Adding New Scripts

When adding scripts:

1. **Choose the right directory:**
   - `setup/` — One-time configuration
   - `validation/` — Pre-execution checks
   - `utilities/` — Operational helpers
   - `development/` — Dev-time tools

2. **Follow naming conventions:**
   - Use snake_case
   - Verbs for actions: `test_`, `create_`, `reset_`, `list_`
   - Clear, descriptive names

3. **Include docstrings:**
   - Module-level docstring with usage examples
   - Function-level docstrings with argument descriptions

4. **Make them CLI-friendly:**
   - Use `argparse` for arguments
   - Return proper exit codes
   - Print helpful error messages

5. **Update this README:**
   - Add usage examples
   - Document all arguments
   - Explain when to use the script

---

## Support

For issues with scripts:

1. Check `.databrickscfg` is valid
2. Verify environment variables are set
3. Run `python scripts/setup/test_connection.py`
4. Check service principal permissions

For missing features or bugs, file an issue with:
- Script name and command used
- Error message and traceback
- Expected vs actual behavior
