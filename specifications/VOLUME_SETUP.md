# Volume Setup Specification

## Purpose

Create Unity Catalog volumes to support the **sas2dbx-migrate** system.

---

## Volume Structure

```
/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/
├── input/                    # SAS source files + config
├── staging/                  # Conversion output (pre-review)
├── approved/                 # Vetted code ready for deployment
├── metadata_registry/        # Global data dictionaries
└── archive/                  # Original SAS backup
```

---

## Setup Script

### Step 1: Create Volume

```sql
-- Run in Databricks SQL Editor or notebook

-- Create schema if needed
CREATE SCHEMA IF NOT EXISTS `na-dbxtraining`.sas2dbx_migrate
COMMENT 'SAS to Databricks migration workspace';

-- Create volume
CREATE VOLUME IF NOT EXISTS `na-dbxtraining`.sas2dbx_migrate.sas_migration
COMMENT 'Storage for SAS code conversion pipeline';
```

### Step 2: Create Subfolders

```python
# Databricks notebook
dbutils.fs.mkdirs("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input")
dbutils.fs.mkdirs("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging")
dbutils.fs.mkdirs("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/approved")
dbutils.fs.mkdirs("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/metadata_registry")
dbutils.fs.mkdirs("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/archive")

# Verify structure
display(dbutils.fs.ls("/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration"))
```

### Step 3: Create Sample Project Structure

```python
# Create example project folder
project_name = "claims_analytics"
base_path = f"/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input/{project_name}"

dbutils.fs.mkdirs(f"{base_path}/sas")
dbutils.fs.mkdirs(f"{base_path}/metadata")

# Create config template
config_template = """project_name: claims_analytics
description: Weekly claims analytics and spike detection
sas_version: 9.4
execution_order:
  - 01_load_claims.sas
  - 02_enrich_claims.sas
  - 03_weekly_summary.sas
target:
  pipeline_type: sdp
  medallion_layer: end_to_end
  schedule: "0 2 * * 1"
conversion:
  model: opus-4.8
  validate_output: true
  create_bundle: true
"""

dbutils.fs.put(f"{base_path}/config.yaml", config_template, overwrite=True)
```

### Step 4: Set Permissions

```sql
-- Grant read/write to relevant groups
GRANT READ, WRITE ON VOLUME `na-dbxtraining`.sas2dbx_migrate.sas_migration 
TO `data-engineering-team`;

GRANT READ ON VOLUME `na-dbxtraining`.sas2dbx_migrate.sas_migration 
TO `data-analyst-team`;
```

---

## Verification Checklist

- [ ] Volume created: `/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/`
- [ ] Subfolders exist: `input/`, `staging/`, `approved/`, `metadata_registry/`, `archive/`
- [ ] Permissions configured for data engineering team
- [ ] Sample project structure created in `input/claims_analytics/`
- [ ] Can write test file: `dbutils.fs.put(...)`

---

## Usage Example

```python
# Upload SAS file
sas_code = """
data work.test;
    set sashelp.class;
run;
"""
dbutils.fs.put(
    "/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input/claims_analytics/sas/test.sas",
    sas_code,
    overwrite=True
)

# Run conversion (next step after setup)
from sas2databricks import migrate_project
migrate_project(
    sas_project_dir="/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/input/claims_analytics",
    output_dir="/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/staging/claims_analytics",
    target="sdp",  # Modern Spark Declarative Pipelines
    model="opus-4.8"
)
```

---

**Next:** See `SAS_MIGRATION_GUIDE.md` for decomposition strategy.
