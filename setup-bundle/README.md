# Setup Bundle - Deploy Notebooks to Workspace

This bundle deploys the 3 setup notebooks to your Databricks workspace.

## Quick Deploy

```bash
cd setup-bundle
databricks bundle validate -t dev
databricks bundle deploy -t dev
```

## What Gets Deployed

Notebooks are synced to:
```
/Workspace/Users/{your_email}/.sas2dbx_setup/files/notebooks/
├── 01_setup_volumes.py
├── 02_upload_sample_sas.py
└── 03_test_conversion.py
```

## After Deployment

1. Open Databricks Workspace
2. Navigate to: Users → {your_email} → .sas2dbx_setup → files → notebooks
3. Run notebooks in order (01, 02, 03)

See `../DEPLOY_NOTEBOOKS.md` for detailed instructions.
