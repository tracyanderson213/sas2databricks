"""
Apply Standardized Tags to SAS Migration Pipelines

This script updates pipeline tags for manually-created pipelines that aren't
managed by the DAB bundle.

Usage:
  databricks notebook run apply_pipeline_tags.py

Requirements:
  - Databricks SDK installed
  - Workspace access with pipeline update permissions
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import PipelineSpec
import sys

# Initialize Databricks client (uses env vars or .databrickscfg)
w = WorkspaceClient()

# Pipeline tag configurations (core tags only)
PIPELINE_TAGS = {
    # Adventure Works Ingestion
    "066a23bf-8841-4406-94ad-c61dc6a720d1": {
        "project": "sas_dbx_migration",
        "developer": "tracy_anderson",
        "bundle_target": "dev",
        "pipeline_type": "ingestion",
        "created_by": "manual",
        "sas_migration": "true"
    },

    # Adventure Works Transformation V2
    "5a190cd0-e289-4ee4-b3d0-63e9e8181787": {
        "project": "sas_dbx_migration",
        "developer": "tracy_anderson",
        "bundle_target": "dev",
        "pipeline_type": "transformation",
        "created_by": "manual",
        "sas_migration": "true"
    },

    # Migration Pipeline (Comprehensive)
    "46bfe4ed-6a53-40c6-821f-f461cf8b7e01": {
        "project": "sas_dbx_migration",
        "developer": "tracy_anderson",
        "bundle_target": "dev",
        "pipeline_type": "comprehensive",
        "created_by": "manual",
        "sas_migration": "true"
    },

    # Claims Adjudication (Production)
    "70e222e0-9c68-456a-ba29-71d63b7b387a": {
        "project": "sas_dbx_migration",
        "developer": "tracy_anderson",
        "bundle_target": "dev",
        "pipeline_type": "claims_processing",
        "created_by": "manual",
        "sas_migration": "true"
    },

    # HLS Claims Pipeline
    "14ccd56e-34aa-422e-b98e-3e547b8d6752": {
        "project": "sas_dbx_migration",
        "developer": "tracy_anderson",
        "bundle_target": "dev",
        "pipeline_type": "claims_processing",
        "created_by": "manual",
        "sas_migration": "true"
    }
}

def apply_tags_to_pipeline(pipeline_id: str, tags: dict):
    """
    Apply tags to a pipeline by updating its configuration.

    Args:
        pipeline_id: The pipeline ID
        tags: Dictionary of tag key-value pairs
    """
    try:
        # Get current pipeline configuration
        pipeline = w.pipelines.get(pipeline_id=pipeline_id)

        print(f"\n{'='*80}")
        print(f"Pipeline: {pipeline.name}")
        print(f"ID: {pipeline_id}")
        print(f"{'='*80}")

        # Merge new tags with existing configuration
        current_config = pipeline.spec.configuration or {}

        print(f"\n📋 Current tags:")
        if current_config:
            for key in ['project', 'developer', 'bundle_target', 'pipeline_type', 'created_by', 'sas_migration']:
                if key in current_config:
                    print(f"  {key}: {current_config[key]}")
        else:
            print("  None")

        # Update configuration with new tags
        updated_config = {**current_config, **tags}

        print(f"\n✨ New tags to apply:")
        for key, value in tags.items():
            print(f"  {key}: {value}")

        # Update pipeline with new configuration
        # Note: This updates the entire spec, so we need to preserve other settings
        w.pipelines.update(
            pipeline_id=pipeline_id,
            name=pipeline.name,
            catalog=pipeline.spec.catalog,
            target=pipeline.spec.target,
            libraries=pipeline.spec.libraries,
            configuration=updated_config,
            serverless=pipeline.spec.serverless,
            photon=pipeline.spec.photon,
            continuous=pipeline.spec.continuous,
            development=pipeline.spec.development
        )

        print(f"\n✅ Tags applied successfully!")

    except Exception as e:
        print(f"\n❌ Error applying tags to pipeline {pipeline_id}: {str(e)}")
        return False

    return True

def main():
    """Main execution function."""
    print("="*80)
    print("SAS Migration Pipeline Tag Application")
    print("="*80)
    print(f"\nPipelines to update: {len(PIPELINE_TAGS)}")

    success_count = 0
    failure_count = 0

    for pipeline_id, tags in PIPELINE_TAGS.items():
        if apply_tags_to_pipeline(pipeline_id, tags):
            success_count += 1
        else:
            failure_count += 1

    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed: {failure_count}")
    print(f"{'='*80}\n")

    if failure_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
