#!/bin/bash
#
# Cleanup Old HLS Claims Demo Files
# Keeps only SAS Migration System files
#

set -e

PROJECT_DIR="/app/python/source_code/projects/3c8d1ae7-103b-4b34-8eed-a269543e43bb"
cd "$PROJECT_DIR"

echo "=========================================="
echo "SAS Migration System - Cleanup Old Files"
echo "=========================================="
echo ""
echo "This will remove old HLS claims demo files"
echo "and keep only SAS migration system files."
echo ""
echo "Files will be archived to: old_hls_demo_backup/"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Creating backup directory..."
mkdir -p old_hls_demo_backup

echo ""
echo "Archiving old folders..."
[ -d src/ ] && mv src/ old_hls_demo_backup/ && echo "  ✅ Archived: src/"
[ -d data_generation/ ] && mv data_generation/ old_hls_demo_backup/ && echo "  ✅ Archived: data_generation/"
[ -d pipeline/ ] && mv pipeline/ old_hls_demo_backup/ && echo "  ✅ Archived: pipeline/"
[ -d resources/ ] && mv resources/ old_hls_demo_backup/ && echo "  ✅ Archived: resources/"
[ -d context/ ] && mv context/ old_hls_demo_backup/ && echo "  ✅ Archived: context/"

echo ""
echo "Archiving old root files..."
[ -f architecture.md ] && mv architecture.md old_hls_demo_backup/ && echo "  ✅ Archived: architecture.md"
[ -f DEPLOY.md ] && mv DEPLOY.md old_hls_demo_backup/ && echo "  ✅ Archived: DEPLOY.md"
[ -f DAB_DEPLOYMENT.md ] && mv DAB_DEPLOYMENT.md old_hls_demo_backup/ && echo "  ✅ Archived: DAB_DEPLOYMENT.md"

echo ""
echo "Archiving old specification files..."
[ -f specifications/01-lakeflow.md ] && mv specifications/01-lakeflow.md old_hls_demo_backup/ && echo "  ✅ Archived: specifications/01-lakeflow.md"
[ -f specifications/04-ai-bi.md ] && mv specifications/04-ai-bi.md old_hls_demo_backup/ && echo "  ✅ Archived: specifications/04-ai-bi.md"
[ -f specifications/SCHEMAS.md ] && mv specifications/SCHEMAS.md old_hls_demo_backup/ && echo "  ✅ Archived: specifications/SCHEMAS.md"
[ -f specifications/SDP_MIGRATION.md ] && mv specifications/SDP_MIGRATION.md old_hls_demo_backup/ && echo "  ✅ Archived: specifications/SDP_MIGRATION.md"

echo ""
echo "=========================================="
echo "✅ CLEANUP COMPLETE!"
echo "=========================================="
echo ""
echo "Archived files: old_hls_demo_backup/"
echo ""
echo "Current structure:"
ls -1 | grep -v old_hls_demo_backup
echo ""
echo "📋 Next steps:"
echo "  1. Verify notebooks still work"
echo "  2. Review documentation"
echo "  3. Delete archive: rm -rf old_hls_demo_backup/"
echo ""
echo "=========================================="
