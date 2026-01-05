# Jupyter Notebooks

Interactive notebooks for running, testing, and exploring the NYC Mobility & Weather Analytics pipeline.

## Available Notebooks

### 01_pipeline_operations.ipynb

**Purpose:** Run and validate each step of the data pipeline

**What it does:**
- ✅ Run DLT data ingestion (Bronze layer)
- ✅ Run dbt transformations (Silver layer)
- ✅ Run Great Expectations validation (Gold layer)
- ✅ Validate data quality at each step
- ✅ Monitor pipeline performance
- ✅ Troubleshoot issues

**Use this notebook to:**
- Execute the complete pipeline step-by-step
- Validate that each stage completes successfully
- Debug pipeline issues
- Monitor execution time and resource usage
- Understand what each pipeline stage does

**Typical workflow:**
1. Verify environment setup
2. Run DLT ingestion → validate raw data
3. Run dbt transformations → validate staging/marts
4. Run Great Expectations → review data quality
5. Check overall pipeline health

### 02_data_exploration_and_metrics.ipynb

**Purpose:** Explore transformed data and analyze metrics

**What it does:**
- 📊 Explore 12.5M trip records
- 📈 Analyze temporal patterns (hourly, daily, weekly)
- 🌤️ Study weather impact on mobility
- 🗺️ Identify top pickup/dropoff locations
- 🚗 Compare transportation modes
- 📉 Query semantic layer metrics
- 💾 Export analysis results

**Use this notebook to:**
- Answer business questions with data
- Create visualizations and charts
- Understand mobility patterns
- Generate reports and insights
- Export data for external tools

**Example analyses included:**
- How does rain affect trip volume?
- What are peak hours for each transportation mode?
- Which neighborhoods have the most pickups?
- How do weekends differ from weekdays?
- What's the mode share in different weather conditions?

---

## Getting Started

### 1. Install Jupyter

```bash
poetry add --group dev jupyter ipykernel matplotlib seaborn
```

Or if already in pyproject.toml:

```bash
poetry install
```

### 2. Start Jupyter

```bash
# From project root
poetry run jupyter notebook

# Or use Jupyter Lab (recommended)
poetry run jupyter lab
```

### 3. Open a Notebook

Navigate to the `notebooks/` directory and open either:
- `01_pipeline_operations.ipynb` - for running the pipeline
- `02_data_exploration_and_metrics.ipynb` - for data analysis

### 4. Run Cells

Execute cells in order using:
- `Shift + Enter` - Run cell and move to next
- `Ctrl + Enter` - Run cell and stay on current
- `Cell → Run All` - Run entire notebook

---

## Prerequisites

**Before running the notebooks:**

1. **Environment Setup**
   ```bash
   poetry install
   ```

2. **For Pipeline Operations Notebook:**
   - Nothing required - it will run ingestion for you
   - First run will take ~5-10 minutes for data ingestion

3. **For Data Exploration Notebook:**
   - Data must exist in database (run pipeline first)
   - Or use notebook #1 to populate data

---

## Notebook Outputs

### Pipeline Operations

**Generated outputs:**
- Validation results in stdout
- dbt run results (`dbt/target/run_results.json`)
- Great Expectations reports (`great_expectations/uncommitted/data_docs/`)
- Pipeline performance metrics

### Data Exploration

**Generated outputs:**
- Visualizations (charts, graphs, plots)
- Statistical summaries
- CSV exports in `outputs/` directory:
  - `mode_statistics.csv`
  - `hourly_patterns.csv`
  - `weather_impact.csv`
  - `top_pickup_locations.csv`

---

## Tips & Tricks

### Performance

**For faster execution:**
- Close DuckDB connections when done: `conn.close()`
- Limit query results with `LIMIT` for exploratory analysis
- Use `read_only=True` when connecting to DuckDB for analysis

**Example:**
```python
conn = duckdb.connect(str(DB_PATH), read_only=True)
```

### Customization

**Modify queries:**
All SQL queries are in code cells - edit them to:
- Change date ranges
- Filter by specific modes
- Aggregate differently
- Add new metrics

**Example:**
```python
# Original: all trips
df = conn.execute("SELECT * FROM fct_trips").fetchdf()

# Modified: only September yellow taxis
df = conn.execute("""
    SELECT * FROM fct_trips
    WHERE trip_type = 'yellow_taxi'
      AND pickup_datetime >= '2024-09-01'
      AND pickup_datetime < '2024-10-01'
""").fetchdf()
```

### Visualization

**Customize charts:**
```python
# Change figure size
fig, ax = plt.subplots(figsize=(14, 6))  # width, height in inches

# Change colors
colors = ['#FF6B6B', '#4ECDC4', '#95E1D3']

# Save figure
plt.savefig('outputs/my_chart.png', dpi=300, bbox_inches='tight')
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

# Parquet
df.to_parquet('outputs/data.parquet')
```

---

## Troubleshooting

### Database Not Found

**Error:** `FileNotFoundError: Database not found`

**Solution:** Run ingestion first:
```bash
poetry run python src/ingestion/run_pipeline.py
```

Or execute the ingestion cell in notebook #1.

### Database Locked

**Error:** `duckdb.IOException: database is locked`

**Solution:** Close all DuckDB connections:
```python
conn.close()  # In notebook

# Or from terminal
pkill -f duckdb
```

### Kernel Crashes

**Error:** Kernel dies when running large queries

**Solution:**
- Restart kernel: `Kernel → Restart`
- Add `LIMIT` to queries
- Increase available memory
- Use read-only mode

### Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'matplotlib'`

**Solution:**
```bash
poetry add --group dev matplotlib seaborn
```

### MetricFlow Not Available

**Error:** `Could not list metrics`

**Solution:** This is OK! The notebooks work without MetricFlow. You can still query fact tables directly.

---

## Example Workflows

### Daily Pipeline Check

1. Open `01_pipeline_operations.ipynb`
2. Run "Step 2: dbt Transformation" (assumes data exists)
3. Run "Step 3: Great Expectations Validation"
4. Check "Step 4: Overall Pipeline Validation"
5. Review any failures

### Weekly Analysis

1. Open `02_data_exploration_and_metrics.ipynb`
2. Modify date filters in queries
3. Run all analysis cells
4. Export results to CSV
5. Share findings with team

### Ad-hoc Investigation

1. Open `02_data_exploration_and_metrics.ipynb`
2. Navigate to "Custom Analysis Examples"
3. Copy a template query
4. Modify for your specific question
5. Run and visualize results

---

## Best Practices

### 1. Always Close Connections
```python
conn = duckdb.connect(...)
# ... do work ...
conn.close()  # Important!
```

### 2. Use Read-Only for Analysis
```python
conn = duckdb.connect(str(DB_PATH), read_only=True)
```

### 3. Document Your Changes
Add markdown cells to explain custom analyses:
```markdown
## My Custom Analysis

Investigating the impact of temperature on CitiBike usage
```

### 4. Version Control
- Commit notebooks to git
- Use `.gitignore` for outputs: `outputs/*.csv`
- Clear outputs before committing: `Cell → All Output → Clear`

### 5. Share Results
- Export key findings to CSV/Excel
- Save visualizations as PNG/PDF
- Create summary markdown cells

---

## Advanced Usage

### Run Notebooks Programmatically

```bash
# Execute notebook from command line
poetry run jupyter nbconvert \
    --to notebook \
    --execute \
    --inplace \
    notebooks/01_pipeline_operations.ipynb
```

### Convert to HTML Report

```bash
# Generate HTML report
poetry run jupyter nbconvert \
    --to html \
    notebooks/02_data_exploration_and_metrics.ipynb \
    --output-dir outputs/
```

### Schedule Notebook Execution

Use `papermill` to run notebooks with parameters:

```bash
poetry add papermill

poetry run papermill \
    notebooks/02_data_exploration_and_metrics.ipynb \
    outputs/weekly_report.ipynb \
    -p analysis_date "2024-11-01"
```

---

## Additional Resources

- **Jupyter Documentation**: https://jupyter.org/documentation
- **DuckDB Python API**: https://duckdb.org/docs/api/python
- **Pandas Documentation**: https://pandas.pydata.org/docs/
- **Matplotlib Gallery**: https://matplotlib.org/stable/gallery/
- **Seaborn Tutorial**: https://seaborn.pydata.org/tutorial.html

---

## Questions?

Refer to:
- [Pipeline Operations Guide](../docs/PIPELINE_OPERATIONS_GUIDE.md)
- [MVP 2 Completion Summary](../docs/MVP2_COMPLETION_SUMMARY.md)
- [Main README](../README.md)
