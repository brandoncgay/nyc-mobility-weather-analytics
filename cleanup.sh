#!/bin/bash
# cleanup.sh - Repository cleanup script
# Run from project root: ./cleanup.sh

set -e

echo "========================================="
echo "NYC Mobility Analytics - Cleanup Script"
echo "========================================="
echo ""

# Function to get directory size
get_size() {
    du -sh "$1" 2>/dev/null | awk '{print $1}'
}

# Track total space reclaimed
total_space=0

echo "🧹 Starting cleanup..."
echo ""

# 1. Python cache
echo "1. Cleaning Python __pycache__ directories..."
pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$pycache_count" -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "   ✓ Removed $pycache_count __pycache__ directories"
else
    echo "   ✓ No __pycache__ directories found"
fi
echo ""

# 2. dbt artifacts
echo "2. Cleaning dbt build artifacts..."
if [ -d "dbt/target" ]; then
    target_size=$(get_size dbt/target)
    rm -rf dbt/target/
    echo "   ✓ Removed dbt/target/ ($target_size)"
else
    echo "   ✓ dbt/target/ already clean"
fi

if [ -d "dbt/logs" ]; then
    logs_size=$(get_size dbt/logs)
    rm -rf dbt/logs/
    echo "   ✓ Removed dbt/logs/ ($logs_size)"
else
    echo "   ✓ dbt/logs/ already clean"
fi
echo ""

# 3. Dagster temp storage
echo "3. Cleaning Dagster temporary storage..."
if [ -d "tmpvxdhpv0z" ]; then
    tmp_size=$(get_size tmpvxdhpv0z)
    rm -rf tmpvxdhpv0z/
    echo "   ✓ Removed tmpvxdhpv0z/ ($tmp_size)"
else
    echo "   ✓ No Dagster temp storage found"
fi
echo ""

# 4. Great Expectations uncommitted
echo "4. Cleaning Great Expectations cache..."
if [ -d "great_expectations/uncommitted" ]; then
    ge_size=$(get_size great_expectations/uncommitted)
    rm -rf great_expectations/uncommitted/*
    echo "   ✓ Cleaned great_expectations/uncommitted/ ($ge_size)"
else
    echo "   ✓ Great Expectations cache already clean"
fi
echo ""

# 5. Empty directories
echo "5. Cleaning empty/unused directories..."
for dir in data/bronze data/silver data/gold data/raw; do
    if [ -d "$dir" ]; then
        rmdir "$dir" 2>/dev/null || true
        echo "   ✓ Removed $dir/"
    fi
done
echo ""

# 6. Jupyter checkpoints
echo "6. Cleaning Jupyter notebook checkpoints..."
if [ -d "notebooks/.ipynb_checkpoints" ]; then
    rm -rf notebooks/.ipynb_checkpoints/
    echo "   ✓ Removed notebooks/.ipynb_checkpoints/"
else
    echo "   ✓ No Jupyter checkpoints found"
fi
echo ""

# 7. Optional: Old scripts
echo "7. Optional: Remove old/superseded scripts?"
if [ -f "scripts/run_pipeline.sh" ]; then
    read -p "   Remove scripts/run_pipeline.sh (superseded by Dagster)? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm scripts/run_pipeline.sh
        echo "   ✓ Removed scripts/run_pipeline.sh"
    else
        echo "   ⊘ Kept scripts/run_pipeline.sh"
    fi
else
    echo "   ✓ scripts/run_pipeline.sh not found"
fi
echo ""

# 8. Optional: Duplicate notebooks
echo "8. Optional: Remove original notebooks (keeping executed versions)?"
read -p "   This will remove .ipynb files if *_executed.ipynb exists [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    removed_count=0
    for nb in notebooks/*_executed.ipynb; do
        if [ -f "$nb" ]; then
            original="${nb/_executed/}"
            if [ -f "$original" ]; then
                rm "$original"
                echo "   ✓ Removed $(basename "$original")"
                removed_count=$((removed_count + 1))
            fi
        fi
    done
    if [ $removed_count -eq 0 ]; then
        echo "   ✓ No duplicate notebooks found"
    else
        echo "   ✓ Removed $removed_count original notebook(s)"
    fi
else
    echo "   ⊘ Kept all notebooks"
fi
echo ""

# Summary
echo "========================================="
echo "✓ Cleanup Complete!"
echo "========================================="
echo ""
echo "Recommended next steps:"
echo "  1. Run 'git status' to see changes"
echo "  2. Add cleanup artifacts to .gitignore"
echo "  3. Rebuild dbt artifacts: cd dbt && poetry run dbt deps"
echo ""
echo "Note: All cleaned artifacts will be regenerated automatically when needed"
echo ""
