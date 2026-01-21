import marimo as mo

__generated__ = "0.1.0"

_tex = mo.md(
    r"""
    # NYC Mobility & Weather Analytics - Exploration

    This reactive notebook explores the relationships between weather conditions and mobility patterns in NYC.
    """
)
app = mo.App(title="NYC Mobility & Weather Analytics")

@app.cell
def __():
    import duckdb
    import pandas as pd
    import plotly.express as px
    import os
    
    # Configure Connection
    MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")
    if MOTHERDUCK_TOKEN:
        con = duckdb.connect("md:nyc_mobility?motherduck_token=" + MOTHERDUCK_TOKEN)
    else:
        con = duckdb.connect("data/nyc_mobility.duckdb")
        
    return duckdb, pd, px, os, con, MOTHERDUCK_TOKEN


@app.cell
def __(con):
    # Query Data
    df = con.sql("SELECT * FROM core_core.fct_trips LIMIT 1000").df()
    return df


@app.cell
def __(df, mo, px):
    # Visualization
    fig = px.scatter(df, x="trip_distance", y="trip_duration_minutes", color="trip_type", title="Trip Distance vs Duration")
    mo.ui.plotly(fig)
    return fig


if __name__ == "__main__":
    app.run()
