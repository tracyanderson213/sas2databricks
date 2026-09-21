# Manual Tag Application Guide

**Quick Reference for UI-Based Tag Updates**

---

## Summary

✅ **2 of 6 pipelines** have tags applied (via DAB bundle)  
⚠️ **5 of 6 pipelines** need manual tag application (permission issue with API)

---

## Core Tags (Apply to All 5 Pipelines)

```yaml
project: "sas_dbx_migration"
developer: "tracy_anderson"
bundle_target: "dev"
pipeline_type: "<see table below>"
created_by: "manual"
sas_migration: "true"
```

---

## Pipeline-Specific Tags

### 1. Adventure Works Ingestion
- **Pipeline ID:** `066a23bf-8841-4406-94ad-c61dc6a720d1`
- **URL:** https://adb-1952652121322753.13.azuredatabricks.net/pipelines/066a23bf-8841-4406-94ad-c61dc6a720d1
- **pipeline_type:** `ingestion`

**Tags to add:**
```
project = sas_dbx_migration
developer = tracy_anderson
bundle_target = dev
pipeline_type = ingestion
created_by = manual
sas_migration = true
```

---

### 2. Adventure Works Transformation V2
- **Pipeline ID:** `5a190cd0-e289-4ee4-b3d0-63e9e8181787`
- **URL:** https://adb-1952652121322753.13.azuredatabricks.net/pipelines/5a190cd0-e289-4ee4-b3d0-63e9e8181787
- **pipeline_type:** `transformation`

**Tags to add:**
```
project = sas_dbx_migration
developer = tracy_anderson
bundle_target = dev
pipeline_type = transformation
created_by = manual
sas_migration = true
```

---

### 3. Migration Pipeline (Comprehensive)
- **Pipeline ID:** `46bfe4ed-6a53-40c6-821f-f461cf8b7e01`
- **URL:** https://adb-1952652121322753.13.azuredatabricks.net/pipelines/46bfe4ed-6a53-40c6-821f-f461cf8b7e01
- **pipeline_type:** `comprehensive`

**Tags to add:**
```
project = sas_dbx_migration
developer = tracy_anderson
bundle_target = dev
pipeline_type = comprehensive
created_by = manual
sas_migration = true
```

---

### 4. Claims Adjudication Pipeline
- **Pipeline ID:** `70e222e0-9c68-456a-ba29-71d63b7b387a`
- **URL:** https://adb-1952652121322753.13.azuredatabricks.net/pipelines/70e222e0-9c68-456a-ba29-71d63b7b387a
- **pipeline_type:** `claims_processing`

**Tags to add:**
```
project = sas_dbx_migration
developer = tracy_anderson
bundle_target = dev
pipeline_type = claims_processing
created_by = manual
sas_migration = true
```

---

### 5. HLS Claims Pipeline
- **Pipeline ID:** `14ccd56e-34aa-422e-b98e-3e547b8d6752`
- **URL:** https://adb-1952652121322753.13.azuredatabricks.net/pipelines/14ccd56e-34aa-422e-b98e-3e547b8d6752
- **pipeline_type:** `claims_processing`

**Tags to add:**
```
project = sas_dbx_migration
developer = tracy_anderson
bundle_target = dev
pipeline_type = claims_processing
created_by = manual
sas_migration = true
```

---

## UI Steps (Repeat for Each Pipeline)

### Step 1: Open Pipeline
Click the URL for the pipeline you want to update

### Step 2: Navigate to Settings
1. Click **Settings** in the left sidebar
2. Scroll down to **Configuration** section

### Step 3: Add Tags
For each tag (6 tags total):
1. Click **+ Add configuration**
2. Enter **Key** (e.g., `project`)
3. Enter **Value** (e.g., `sas_dbx_migration`)
4. Repeat for all 6 tags

### Step 4: Save
1. Click **Save** at the top right
2. Confirm the pipeline restarts (if running)

---

## Verification

After adding tags to all pipelines, verify by:

### Option 1: UI Check
Open each pipeline → Settings → Configuration → Verify 6 tags present

### Option 2: CLI Check
```bash
databricks pipelines get <PIPELINE_ID> --json | jq '.spec.configuration'
```

**Expected output:**
```json
{
  "project": "sas_dbx_migration",
  "developer": "tracy_anderson",
  "bundle_target": "dev",
  "pipeline_type": "ingestion",
  "created_by": "manual",
  "sas_migration": "true"
}
```

---

## Time Estimate

- **Per pipeline:** ~2 minutes (6 tags × 20 seconds each)
- **Total for 5 pipelines:** ~10 minutes

---

## Alternative: Migrate to DAB Bundle

**Long-term solution:** Move these pipelines into `databricks.yml`

**Benefits:**
- ✅ Tags auto-apply on every deployment
- ✅ Version-controlled configuration
- ✅ No manual UI updates needed
- ✅ Consistent with infrastructure-as-code best practices

**See:** `TAGS_UPDATED.md` for migration guidance

---

## Status Tracking

- [ ] Pipeline #1: Adventure Works Ingestion (`066a23bf...`)
- [ ] Pipeline #2: Adventure Works Transformation V2 (`5a190cd0...`)
- [ ] Pipeline #3: Migration Pipeline (`46bfe4ed...`)
- [ ] Pipeline #4: Claims Adjudication (`70e222e0...`)
- [ ] Pipeline #5: HLS Claims Pipeline (`14ccd56e...`)

---

**Quick Access:** All pipeline URLs are provided above for easy navigation!
