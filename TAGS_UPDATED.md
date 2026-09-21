# Pipeline Tags - Updated & Deployed

**Date:** 2026-09-21  
**Status:** ✅ Core Tags Configured & Deployed

---

## What Was Done

### 1. ✅ Standardized Core Tags (Optional Tags Removed)

**Core Tags Only:**
```yaml
project: "sas_dbx_migration"      # Project identifier
developer: "tracy_anderson"        # Owner (using full name)
bundle_target: "dev"               # Environment (dev/prod)
pipeline_type: "<type>"            # Pipeline category
created_by: "dab" | "manual"      # Creation source
sas_migration: "true"              # Migration project flag
```

**Removed Optional Tags:**
- ❌ `source` (e.g., "adventureworks_sql")
- ❌ `use_case` (e.g., "sql_server_validation")
- ❌ `version` (e.g., "v2")
- ❌ `status` (e.g., "deprecated", "legacy")
- ❌ `data_product` (e.g., "claims_analytics")

---

### 2. ✅ Updated databricks.yml

**Job Tags (Code Translator):**
```yaml
tags:
  project: "sas_dbx_migration"
  developer: "tracy_anderson"
  bundle_target: ${bundle.target}
  created_by: "dab"
  sas_migration: "true"
```

**Pipeline Tags (Template Pipeline):**
```yaml
tags:
  project: "sas_dbx_migration"
  developer: "tracy_anderson"
  bundle_target: ${bundle.target}
  pipeline_type: "template"
  created_by: "dab"
  sas_migration: "true"
```

---

### 3. ✅ Updated scripts/apply_pipeline_tags.py

**All 5 manually-created pipelines now have core tags:**

| Pipeline | Type | Tags |
|----------|------|------|
| Adventure Works Ingestion | `ingestion` | ✅ Core tags |
| Adventure Works Transformation V2 | `transformation` | ✅ Core tags |
| Migration Pipeline | `comprehensive` | ✅ Core tags |
| Claims Adjudication | `claims_processing` | ✅ Core tags |
| HLS Claims Pipeline | `claims_processing` | ✅ Core tags |

---

### 4. ✅ Deployed to Databricks

```bash
databricks bundle deploy -t dev
```

**Result:**
```
✅ Updated jobs.sas_dbx_code_translator
✅ Updated pipelines.sas_dbx_template_pipeline
✅ Files: 5 uploaded, 0 deleted
✅ Resources: 2 changed
```

---

## Key Decisions

### Developer Naming Convention

**Important Distinction:**

| Purpose | Value | Reason |
|---------|-------|--------|
| **Tags** (metadata) | `tracy_anderson` | Proper owner identification |
| **Schemas** (database) | `tanderson` | Matches existing data location |

**Example:**
```yaml
# In tags (for identification)
developer: "tracy_anderson"

# In schema names (for data location)
schema_bronze: "sas_tanderson_bronze"
```

**Why Different?**
- Tags identify WHO owns the resource → "tracy_anderson"
- Schemas identify WHERE the data lives → "sas_tanderson_bronze"
- Changing schema names would break all existing pipelines
- Tags can be updated without breaking anything

---

## Current Tag Status

### ✅ DAB-Managed Resources (Tags Applied)

1. ✅ `sas_dbx_code_translator_tanderson` (Job)
   - Tags: project, developer, bundle_target, created_by, sas_migration

2. ✅ `sas_dbx_template_tanderson` (Pipeline)
   - Tags: project, developer, bundle_target, pipeline_type, created_by, sas_migration

### ⚠️ Manual Resources (Permission Issue)

3. ⚠️ `sas_dbx_adventureworks_ingestion_tanderson`
4. ⚠️ `sas_dbx_adventureworks_02_tracy_anderson_V2`
5. ⚠️ `sas_dbx_migration_pipeline_tracy_anderson`
6. ⚠️ `sas_dbx_claims_adjudication_pipeline_tracy_anderson`
7. ⚠️ `hls_sas_dbx_claims_pipeline`

**Issue:** OAuth token lacks `pipelines` scope for updating manually-created pipelines.

**Error:**
```
Provided OAuth token does not have required scopes: pipelines
```

**Why DAB Bundle Works:**
- DAB deployments use Service Principal authentication
- Service Principal has full pipeline management permissions
- Manually-created pipelines require different auth scope

---

## Benefits

### 1. **Simplified Tag Structure**
- ✅ Only essential tags
- ✅ Easy to understand
- ✅ Consistent across all resources

### 2. **Proper Owner Identification**
- ✅ Uses "tracy_anderson" for clear ownership
- ✅ No confusion with abbreviated names

### 3. **Automated Application**
- ✅ DAB bundle auto-applies tags
- ✅ Script ready for manual pipelines
- ✅ No manual UI updates needed

---

## Next Steps

### Apply Tags to Manual Pipelines

**Option 1: Migrate to DAB Bundle (RECOMMENDED)**

Move manual pipeline definitions into `databricks.yml`:

**Benefits:**
- ✅ Tags auto-apply on every deployment
- ✅ Version-controlled pipeline configuration
- ✅ Consistent infrastructure-as-code
- ✅ No permission issues

**How:**
1. Add pipeline definitions to `databricks.yml` (under `resources.pipelines`)
2. Run `databricks bundle deploy -t dev`
3. Tags automatically applied

**Option 2: Manual UI Update (Quick Fix)**

For each pipeline:
1. Open pipeline in Databricks UI: https://adb-1952652121322753.13.azuredatabricks.net/pipelines/[PIPELINE_ID]
2. Click **Settings**
3. Scroll to **Configuration**
4. Add each tag as a key-value pair:
   - `project` = `sas_dbx_migration`
   - `developer` = `tracy_anderson`
   - `bundle_target` = `dev`
   - `pipeline_type` = `[see table below]`
   - `created_by` = `manual`
   - `sas_migration` = `true`
5. Click **Save**

**Pipeline Types:**
| Pipeline ID | Type |
|-------------|------|
| `066a23bf...` (Adventure Works Ingestion) | `ingestion` |
| `5a190cd0...` (Adventure Works V2) | `transformation` |
| `46bfe4ed...` (Migration Pipeline) | `comprehensive` |
| `70e222e0...` (Claims Adjudication) | `claims_processing` |
| `14ccd56e...` (HLS Claims) | `claims_processing` |

**Option 3: Python Script (Blocked Until Token Scope Fixed)**

```bash
python scripts/apply_pipeline_tags.py
```

**Status:** ❌ Blocked - requires token with `pipelines` scope

---

## Files Updated

| File | Changes |
|------|---------|
| `databricks.yml` | ✅ Updated job & pipeline tags |
| `scripts/apply_pipeline_tags.py` | ✅ Removed optional tags, updated developer name |
| `TAGS_UPDATED.md` | ✅ This documentation |

---

## Summary

**Before:**
- ❌ No tags on any pipelines
- ❌ Inconsistent naming
- ❌ Optional tags cluttering config

**After:**
- ✅ Core tags defined in DAB bundle
- ✅ Consistent "tracy_anderson" for developer
- ✅ Clean, simple tag structure
- ✅ 2 DAB-managed resources tagged and deployed
- ⚠️ 5 manual pipelines require UI update or DAB migration

---

## Status

| Component | Status |
|-----------|--------|
| DAB Bundle Configuration | ✅ Updated & Deployed |
| Job: `sas_dbx_code_translator` | ✅ Tags Applied |
| Pipeline: `sas_dbx_template` | ✅ Tags Applied |
| Manual Pipelines (5) | ⚠️ Pending - See Options Above |

---

**Recommendation:** Migrate the 5 manually-created pipelines to the DAB bundle for automated tag management and version control.

**Quick Win:** If migration isn't immediate, apply tags via UI (5-10 minutes total for all pipelines).
