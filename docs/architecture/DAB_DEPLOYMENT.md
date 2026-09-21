# DAB Deployment Guide

**Status:** DAB structure is ready, but authentication needs to be resolved.

---

## ✅ What's Ready

1. **DAB Structure Created:**
   ```
   databricks.yml           # Bundle configuration
   resources/               # Resource definitions
     └── claims_pipeline.yml  # Pipeline + jobs
   src/                     # Source code
     ├── claims_pipeline.py
     ├── claims_pipeline_sql.sql
     └── metric_views.sql
   ```

2. **Configuration:**
   - Dev and Prod targets configured
   - Pipeline with modern SDP syntax
   - Serverless enabled
   - Variables for catalog/schema

3. **Validation Passed (Syntax):**
   - Bundle structure is correct
   - Resource definitions are valid
   - Pipeline configuration is sound

---

## ❌ Current Blocker: Authentication

### Option 1: OAuth M2M Service Principal (Recommended for Production)
```
Client ID: 57755c23-5f4c-45ac-b2a2-118523d0c1b5
Status: ❌ "Client authentication failed"
```

**Issue:** The service principal client_secret appears to be expired or the SP needs reconfiguration in Azure AD.

**To Fix:**
1. Verify service principal exists in Azure AD
2. Check/regenerate the client secret in Azure Key Vault: `dbx-ss-kv-natraining-2/NADBXTrainingSPN-SlnBldr-Secret`
3. Ensure SP has these permissions:
   - Databricks workspace Contributor
   - Required OAuth scopes: workspace, sql, pipelines, unity-catalog

### Option 2: PAT Token (Current)
```
User: tracy.anderson@3cloudsolutions.com
Status: ⚠️ Works for validation, but missing 'workspace' scope for deployment
```

**Issue:** PAT lacks the `workspace` scope required for `databricks bundle deploy`.

**To Fix:**
1. Generate new PAT with all scopes (workspace, sql, clusters, pipelines, unity-catalog)
2. Or use browser-based `databricks auth login` flow

### Option 3: Azure CLI Authentication (Best for Interactive)
```
Status: Not configured (Azure CLI not installed)
```

**To Set Up:**
```bash
az login
az account set --subscription <subscription-id>
databricks auth login --host https://adb-1952652121322753.13.azuredatabricks.net
```

---

## 🚀 Deployment Options

### A. Fix Authentication, Then Deploy with DABs (Recommended)

Once authentication is resolved:

```bash
# Validate bundle
databricks bundle validate

# Deploy to dev
databricks bundle deploy -t dev

# Start the pipeline
databricks bundle run hls_sas_dbx_claims_pipeline -t dev

# Monitor
databricks pipelines get <pipeline-id>
```

**Benefits:**
- ✅ Version controlled
- ✅ Repeatable deployments
- ✅ CI/CD ready
- ✅ Multi-environment (dev/prod)
- ✅ Infrastructure as Code

---

### B. Hybrid Approach: Manual First, DABs for Updates

**Step 1: Manual UI Deployment (Now)**
Follow `DEPLOY_STEPS.txt` to:
1. Upload notebook via UI
2. Create pipeline manually
3. Get it working

**Step 2: Switch to DABs (Later)**
Once authentication is fixed:
```bash
# Import existing pipeline into DAB
databricks bundle deploy -t dev

# Future updates use DAB workflow
git commit -m "Update pipeline"
databricks bundle deploy -t dev
```

**Benefits:**
- ✅ Unblocked immediately
- ✅ Migrate to DABs incrementally
- ✅ Learn DABs on working system

---

### C. CLI-Only Deployment (Quick but Not IaC)

If you just need it deployed without DABs:

```bash
# Upload files
databricks workspace import-dir ./src /Workspace/Users/tracy.anderson@3cloudsolutions.com/hls_sas_dbx_claims --overwrite

# Create pipeline via JSON (see pipeline_config.json in DEPLOY.md)
databricks pipelines create --json @/tmp/pipeline_config.json

# Start pipeline
databricks pipelines start-update <pipeline-id>
```

---

## 📋 Recommendation

**For Right Now:**
→ **Use Option B (Hybrid):** Manual UI deployment following `DEPLOY_STEPS.txt`

**For Production:**
→ **Fix OAuth M2M Service Principal**, then use DABs for all deployments

---

## 🔧 Fixing the Service Principal (For IT/Admin)

The service principal `sp-solution-builder-natraining-dev` needs:

### 1. Azure AD Configuration
```bash
# Check if SP exists
az ad sp show --id 57755c23-5f4c-45ac-b2a2-118523d0c1b5

# Regenerate secret if needed
az ad sp credential reset --id 57755c23-5f4c-45ac-b2a2-118523d0c1b5

# Update Key Vault secret
az keyvault secret set \
  --vault-name dbx-ss-kv-natraining-2 \
  --name NADBXTrainingSPN-SlnBldr-Secret \
  --value "<new-secret>"
```

### 2. Databricks Workspace Permissions
1. Go to Workspace Settings → Identity and Access
2. Add service principal: `sp-solution-builder-natraining-dev`
3. Grant role: **Workspace Contributor** or **Account Admin**

### 3. OAuth Scopes
Ensure the service principal token includes:
- `workspace` - For bundle deployment
- `sql` - For SQL warehouses
- `pipelines` - For DLT pipelines
- `unity-catalog` - For catalog operations
- `clusters` - For compute management

---

## ✅ Once Fixed: DAB Deployment Commands

```bash
# Validate
databricks bundle validate -t dev

# Deploy
databricks bundle deploy -t dev
# Output: Pipeline ID and workspace URLs

# Run pipeline
databricks bundle run hls_sas_dbx_claims_pipeline -t dev

# Check status
databricks pipelines list-pipeline-events <pipeline-id> --max-results 10

# Deploy to production
databricks bundle deploy -t prod
```

---

## 📁 DAB Structure Reference

```
/app/python/source_code/projects/.../
├── databricks.yml                 # Main bundle config
├── resources/
│   └── claims_pipeline.yml        # Pipeline resource definition
├── src/
│   ├── claims_pipeline.py         # Modern SDP pipeline
│   ├── claims_pipeline_sql.sql    # SQL alternative
│   └── metric_views.sql           # Metric view definitions
├── .databrickscfg                 # Authentication config
└── .databricks/
    └── project.json               # Project metadata
```

---

## 🎯 Summary

| Approach | Auth Required | Time to Deploy | Best For |
|----------|---------------|----------------|----------|
| **DABs** (this setup) | ❌ OAuth M2M or full-scope PAT | 5 min (once auth fixed) | Production, CI/CD |
| **Manual UI** | ✅ Browser session | 10 min | Right now, learning |
| **CLI Direct** | ⚠️ Limited-scope PAT | 15 min | Quick iteration |

**Current Status:** DAB structure is production-ready. Deploy manually now, switch to DABs once SP authentication is fixed.

---

## Next Steps

1. **Immediate:** Follow `DEPLOY_STEPS.txt` for manual UI deployment
2. **Short-term:** Work with Azure/Databricks admin to fix service principal
3. **Long-term:** Use `databricks bundle deploy` for all updates

The DAB is ready to go — just waiting on auth! 🚀
