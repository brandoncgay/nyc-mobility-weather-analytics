# Jupyter Notebooks

Interactive notebooks for running, testing, and exploring the NYC Mobility & Weather Analytics pipeline.

---

## Available Notebooks

### 01_pipeline_operations.ipynb

**Purpose:** Run and validate the complete data pipeline

**What it does:**
- ✅ Environment verification (directory/database checks)
- ✅ DLT data ingestion execution (Bronze layer)
- ✅ dbt transformation execution (Silver layer)
- ✅ Great Expectations validation (Gold layer)
- ✅ Pipeline health checks and validation
- ✅ Performance metrics and monitoring
- ✅ Troubleshooting guide

**Use this notebook to:**
- Execute the complete pipeline step-by-step
- Validate that each stage completes successfully
- Debug pipeline issues
- Monitor execution time and resource usage

### 02_data_exploration_and_metrics.ipynb

**Purpose:** Comprehensive data exploration and analysis

**What it does:**
- 📊 Temporal Patterns - Hourly, daily, and weekly trends
- 🌤️ Weather Impact - Temperature and precipitation analysis
- 🚕 Mode Share - Transportation mode comparison
- 📍 Geographic Patterns - Top pickup/dropoff locations
- 📈 Comparative Analysis - Weekend vs. weekday, rush hour patterns
- 💡 Key Findings - Summary insights and statistics

**Use this notebook to:**
- Explore 12.4M+ trip records
- Analyze weather impact on mobility
- Compare transportation modes
- Identify temporal and geographic patterns
- Generate visualizations and insights

**Analysis Sections:**
1. Temporal Patterns (hourly, daily, day of week)
2. Weather Impact (temperature, precipitation, correlation)
3. Mode Share Analysis (taxi, FHV, CitiBike comparison)
4. Geographic Patterns (top zones, borough analysis)
5. Comparative Analysis (weekend/weekday, rush hour)
6. Key Findings & Insights (summary statistics)

### 03_semantic_models_and_metrics.ipynb

**Purpose:** Understand and explore the dbt semantic layer

**What it does:**
- 📚 Explains the semantic layer concept and benefits
- 🎯 Documents 2 semantic models (trips, hourly_mobility)
- 📊 Catalogs 50 metrics across 4 categories
- 🔍 Shows how to query metrics with SQL
- 📈 Provides working example analyses with visualizations

**Use this notebook to:**
- Learn what semantic models are and why they matter
- Understand the 50 available metrics
- See how metrics map to SQL queries
- Discover dimensions for slicing data
- Find the right metric for your analysis

**Metric Categories:**
- Core Trip Metrics (12): trips, duration, distance, speed, revenue
- Weather Impact Metrics (13): precipitation, temperature effects
- Mode Share Metrics (13): transportation mode breakdowns
- Time Pattern Metrics (12): rush hour, weekday/weekend, day parts

---

## Getting Started

### 1. Install Jupyter

```bash
poetry install  # Includes jupyter and visualization dependencies
```

### 2. Start Jupyter

```bash
# From project root
poetry run jupyter notebook

# Or use Jupyter Lab (recommended)
poetry run jupyter lab
```

### 3. Navigate to Notebooks

Open the `notebooks/` directory and select:
- `01_pipeline_operations.ipynb` - for running the pipeline
- `02_data_exploration_and_metrics.ipynb` - for data analysis
- `03_semantic_models_and_metrics.ipynb` - for understanding metrics

### 4. Run Cells

Execute cells in order:
- `Shift + Enter` - Run cell and move to next
- `Ctrl + Enter` - Run cell and stay
- `Cell → Run All` - Run entire notebook

---

## Prerequisites

**Before running the notebooks:**

1. **Environment Setup**
   ```bash
   poetry install
   ```

2. **For Pipeline Operations:**
   - First run takes ~5-10 minutes (data ingestion)
   - Subsequent runs are faster

3. **For Data Exploration:**
   - Data must exist in database
   - Run pipeline first or use notebook #1

---

## Tips & Best Practices

### Performance

**For faster execution:**
```python
# Always use read-only mode for analysis
conn = duckdb.connect(str(DB_PATH), read_only=True)

# Close connections when done
conn.close()

# Use LIMIT for exploratory queries
SELECT * FROM fct_trips LIMIT 1000
```

### Customization

**Modify queries:**
```python
# Change date ranges
WHERE pickup_datetime >= '2025-10-01'
  AND pickup_datetime < '2025-11-01'

# Filter by mode
WHERE trip_type = 'yellow_taxi'

# Add new metrics
SELECT AVG(trip_distance) as avg_dist,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY trip_distance) as median_dist
```

### Visualization

**Customize charts:**
```python
# Change figure size
fig, ax = plt.subplots(figsize=(14, 6))

# Save figures
plt.savefig('outputs/chart.png', dpi=300, bbox_inches='tight')
```

### Export Data

**Export to different formats:**
```python
# CSV
df.to_csv('outputs/data.csv', index=False)

# Excel (requires openpyxl)
df.to_excel('outputs/data.xlsx', index=False)

# JSON
df.to_json('outputs/data.json', orient='records')
```

---

## Troubleshooting

### Database Not Found

**Error:** `FileNotFoundError: Database not found`

**Solution:**
```bash
# Run ingestion first
poetry run python src/ingestion/run_pipeline.py

# Or execute cells in notebook #1
```

### Database Locked

**Error:** `duckdb.IOException: database is locked`

**Solution:**
```python
# Close connections in notebooks
conn.close()

# Or kill all DuckDB processes
pkill -f duckdb
```

### Kernel Crashes

**Error:** Kernel dies on large queries

**Solution:**
- Add `LIMIT` to queries during exploration
- Use `read_only=True` mode
- Restart kernel: `Kernel → Restart`

### Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'matplotlib'`

**Solution:**
```bash
poetry install  # Should install all dependencies
```

---

## Example Workflows

### Daily Pipeline Check

1. Open `01_pipeline_operations.ipynb`
2. Run "Step 2: dbt Transformation"
3. Run "Step 3: Great Expectations"
4. Review validation results

### Weekly Analysis

1. Open `02_data_exploration_and_metrics.ipynb`
2. Modify date filters if needed
3. Run all analysis sections
4. Review key findings
5. Export results

### Ad-hoc Investigation

1. Open `02_data_exploration_and_metrics.ipynb`
2. Find relevant section (temporal, weather, mode, etc.)
3. Modify queries for your question
4. Run and visualize results

---

## Advanced Usage

### Convert to HTML Report

```bash
# Generate HTML report
poetry run jupyter nbconvert \
    --to html \
    notebooks/02_data_exploration_and_metrics.ipynb \
    --output-dir outputs/
```

### Run Programmatically

```bash
# Execute notebook from command line (for simple notebooks)
poetry run jupyter nbconvert \
    --to notebook \
    --execute \
    notebooks/03_semantic_models_and_metrics.ipynb
```

**Note:** Pipeline operations notebook should be run interactively (takes 10-15 min for first run).

---

## Project Structure

```
notebooks/
├── README.md                                    # This file
├── 01_pipeline_operations.ipynb                # Pipeline execution & validation
├── 02_data_exploration_and_metrics.ipynb       # Comprehensive data analysis
└── 03_semantic_models_and_metrics.ipynb        # Semantic layer documentation
```

**Simplified from 9 notebooks to 3 essential notebooks** - redundant content removed, exploration notebook expanded.

---

## Additional Resources

- **Main README**: [../README.md](../README.md)
- **Architecture**: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **Data Model**: [../docs/data_model.md](../docs/data_model.md)
- **dbt Documentation**: `cd dbt && poetry run dbt docs serve`

---

**Last Updated:** January 9, 2026
**Notebook Count:** 3 (simplified from 9)
**Total Size:** ~40KB (down from ~1.6GB with executed versions)
