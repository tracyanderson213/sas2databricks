# Naming Conventions & DAB Presets

**Standardized naming across all resources using DAB preset variables.**

---

## Overview

All resources now follow a **consistent `sas_dbx_` prefix** and use **DAB preset variables** to eliminate manual configuration.

### Key Benefits

✅ **No `--var developer_id` needed** — auto-detects your username  
✅ **Consistent naming** — all resources use `sas_dbx_` prefix  
✅ **Standardized tags** — same tags across all resources  
✅ **Simpler commands** — fewer flags to remember  

---

## DAB Preset Variables

These are **automatically available** in every DAB deployment:

| Variable | Example Value | Description |
|----------|--------------|-------------|
| `${bundle.name}` | `sas_dbx_migration` | Bundle name from databricks.yml |
| `${bundle.target}` | `dev`, `prod` | Current deployment target |
| `${workspace.current_user.shortName}` | `tanderson` | Your username (no domain) |
| `${workspace.current_user.userName}` | `tanderson@3cloudsolutions.com` | Your full email |

**No configuration needed!** These work out-of-the-box.

---

## Resource Naming Patterns

### Schemas

**Pattern:** `sas_dbx_{developer_id}_{layer}`

**Examples:**
- `sas_dbx_tanderson_bronze`
- `sas_dbx_tanderson_silver`
- `sas_dbx_tanderson_gold`

**Configuration:**
```yaml
schemas:
  sas_dbx_bronze:
    name: "sas_dbx_${var.developer_id}_bronze"
    # ${var.developer_id} defaults to ${workspace.current_user.shortName}
```

**Result:**
- Your username is automatically detected
- No `--var developer_id` flag needed
- Can override if needed: `--var developer_id=custom`

---

### Job (Code Translator)

**Pattern:** `sas_dbx_code_translator_{developer_id}`

**Examples:**
- `sas_dbx_code_translator_tanderson`
- `sas_dbx_code_translator_jsmith`

**Configuration:**
```yaml
jobs:
  sas_dbx_code_translator:
    name: "sas_dbx_code_translator_${var.developer_id}"
```

**Before:**
```bash
databricks bundle run sas_code_translator_tanderson -t dev
```

**After:**
```bash
databricks bundle run -t dev sas_dbx_code_translator
# Auto-detects: sas_dbx_code_translator_tanderson
```

---

### Pipelines

**Pattern:** `sas_dbx_{pipeline_name}_{developer_id}`

**Examples:**
- `sas_dbx_template_tanderson`
- `sas_dbx_claims_adjudication_tanderson`
- `sas_dbx_customer_analysis_jsmith`

**Configuration:**
```yaml
pipelines:
  sas_dbx_template_pipeline:
    name: "sas_dbx_template_${var.developer_id}"
```

**Why no `_pipeline` suffix?**
- Databricks UI already shows these under "Pipelines" section
- Shorter names = easier to read in UI
- Consistent with Databricks conventions

---

## Standardized Tags

**All resources get consistent tags:**

```yaml
tags:
  project: "sas_dbx_migration"
  developer_id: ${var.developer_id}
  bundle_target: ${bundle.target}
  <resource_specific>: <value>
```

**Resource-specific tags:**
- **Schemas:** `layer: bronze/silver/gold`
- **Job:** `job_type: code_translator`
- **Pipelines:** `pipeline_type: template`

**Benefits:**
- Easy filtering in Databricks UI
- Clear ownership and purpose
- Consistent across all resources

---

## Simplified Workflow

### Before (Manual developer_id)

```bash
# Every command needed --var developer_id
databricks bundle deploy -t dev --var developer_id=tanderson
databricks bundle run sas_code_translator_tanderson -t dev
databricks bundle destroy -t dev --var developer_id=tanderson
```

**3 commands, 3 flags, 2 name variations**

---

### After (Auto-detected)

```bash
# No --var needed (uses your username)
databricks bundle deploy -t dev
databricks bundle run -t dev sas_dbx_code_translator
databricks bundle destroy -t dev
```

**3 commands, 0 flags, 1 consistent name**

---

### Override Username (Optional)

```bash
# Only if you need a custom name
databricks bundle deploy -t dev --var developer_id=custom
```

---

## Migration Guide

### For Existing Deployments

**Old schema names:**
- `sas_tanderson_bronze` → `sas_dbx_tanderson_bronze`
- `sas_tanderson_silver` → `sas_dbx_tanderson_silver`
- `sas_tanderson_gold` → `sas_dbx_tanderson_gold`

**Old job name:**
- `sas_code_translator_tanderson` → `sas_dbx_code_translator_tanderson`

**Old pipeline name:**
- `sas_dbx_TEMPLATE_tanderson_pipeline` → `sas_dbx_template_tanderson`

### Steps to Migrate

```bash
# 1. Drop old schemas (optional — keep data if needed)
python cleanup_tables.py

# 2. Deploy with new naming
databricks bundle deploy -t dev

# 3. Verify new schemas created
databricks schemas list --catalog na-dbxtraining | grep sas_dbx_

# 4. Run converter
databricks bundle run -t dev sas_dbx_code_translator

# 5. Update pipelines
python update_pipeline_file.py template transformed_file.py
```

---

## Reference: Full Resource List

### Deployed Resources (dev target, user: tanderson)

**Schemas:**
- `na-dbxtraining.sas_dbx_tanderson_bronze`
- `na-dbxtraining.sas_dbx_tanderson_silver`
- `na-dbxtraining.sas_dbx_tanderson_gold`

**Job:**
- `sas_dbx_code_translator_tanderson`

**Pipeline:**
- `sas_dbx_template_tanderson`

**Workspace Paths:**
- `/Workspace/Users/57755c23-5f4c-45ac-b2a2-118523d0c1b5/.bundle/sas_dbx_migration/dev/`

**Volume (shared, not per-developer):**
- `/Volumes/na-dbxtraining/sas2dbx_migrate/sas_migration/`

---

## Developer Isolation

**Each developer gets isolated schemas:**

```bash
# User: tanderson
databricks bundle deploy -t dev
# Creates: sas_dbx_tanderson_bronze/silver/gold

# User: jsmith
databricks bundle deploy -t dev
# Creates: sas_dbx_jsmith_bronze/silver/gold

# Custom override
databricks bundle deploy -t dev --var developer_id=team_shared
# Creates: sas_dbx_team_shared_bronze/silver/gold
```

**No collisions, no overwrites!**

---

## Production Deployment

**Uses same pattern with `prod` target:**

```bash
# Deploy to production (auto-detects username)
databricks bundle deploy -t prod

# Or use dedicated prod identifier
databricks bundle deploy -t prod --var developer_id=prod
```

**Production schemas:**
- `na-dbxtraining.sas_dbx_prod_bronze`
- `na-dbxtraining.sas_dbx_prod_silver`
- `na-dbxtraining.sas_dbx_prod_gold`

---

## Troubleshooting

### "Cannot resolve ${workspace.current_user.shortName}"

**Cause:** Not authenticated to workspace

**Fix:**
```bash
# Test connection
python scripts/setup/test_connection.py

# Check auth
cat .databrickscfg.bundle
```

---

### "Resource already exists"

**Cause:** Schema/job/pipeline with old naming still exists

**Fix:**
```bash
# Option 1: Use different developer_id
databricks bundle deploy -t dev --var developer_id=tanderson_v2

# Option 2: Destroy old deployment first
# (if using old databricks.yml)
databricks bundle destroy -t dev --var developer_id=tanderson

# Then deploy with new naming
databricks bundle deploy -t dev
```

---

### "Job name doesn't match"

**Cause:** Running old command format

**Before:**
```bash
databricks bundle run sas_code_translator_tanderson -t dev  # ❌ Old
```

**After:**
```bash
databricks bundle run -t dev sas_dbx_code_translator  # ✅ New
```

---

## Summary

### Naming Standards

| Resource | Pattern | Example |
|----------|---------|---------|
| **Schemas** | `sas_dbx_{dev}_{layer}` | `sas_dbx_tanderson_bronze` |
| **Job** | `sas_dbx_code_translator_{dev}` | `sas_dbx_code_translator_tanderson` |
| **Pipelines** | `sas_dbx_{name}_{dev}` | `sas_dbx_template_tanderson` |

### Tags

| Tag | Value | Purpose |
|-----|-------|---------|
| `project` | `sas_dbx_migration` | Project identifier |
| `developer_id` | `${var.developer_id}` | Owner identifier |
| `bundle_target` | `${bundle.target}` | Environment (dev/prod) |

### Commands

**Deploy:**
```bash
databricks bundle deploy -t dev
```

**Run converter:**
```bash
databricks bundle run -t dev sas_dbx_code_translator
```

**Destroy:**
```bash
databricks bundle destroy -t dev
```

**Override username (optional):**
```bash
databricks bundle deploy -t dev --var developer_id=custom
```

---

**Result:** Clean, consistent, automatic! 🚀
