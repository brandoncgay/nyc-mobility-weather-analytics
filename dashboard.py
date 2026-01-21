"""
NYC Mobility & Weather Analytics Dashboard

Interactive Streamlit dashboard for exploring 14M+ trips across NYC taxi, FHV, and CitiBike
with weather correlations.

Run with: poetry run streamlit run dashboard.py
"""

import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="NYC Mobility & Weather Analytics",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
DB_PATH = Path(__file__).parent / "data" / "nyc_mobility.duckdb"


@st.cache_resource
def get_connection():
    """Create a read-only DuckDB connection."""
    import os
    token = os.getenv("MOTHERDUCK_TOKEN")
    if token:
        return duckdb.connect("md:nyc_mobility", read_only=True)
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=600)
def load_data(query: str):
    """Execute query and return DataFrame."""
    conn = get_connection()
    return conn.execute(query).df()


def format_large_number(num):
    """Format large numbers with K/M suffixes."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return f"{num:.0f}"


# Header
st.title("🚕 NYC Mobility & Weather Analytics")
st.markdown("**Exploring 14M+ trips** across Yellow Taxi, FHV, and CitiBike with weather correlations")

# Sidebar filters
st.sidebar.header("📊 Filters")

# Get date range from data
date_range_query = """
    SELECT
        MIN(CAST(pickup_datetime AS DATE)) as min_date,
        MAX(CAST(pickup_datetime AS DATE)) as max_date
    FROM core_core.fct_trips
"""
date_info = load_data(date_range_query)
min_date = pd.to_datetime(date_info['min_date'].iloc[0]).date()
max_date = pd.to_datetime(date_info['max_date'].iloc[0]).date()

# Date range selector
date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

# Transportation mode filter
mode_options = {
    "All Modes": "all",
    "Yellow Taxi": "yellow_taxi",
    "FHV (Uber/Lyft)": "fhv",
    "CitiBike": "citibike"
}
selected_mode = st.sidebar.selectbox(
    "Transportation Mode",
    options=list(mode_options.keys())
)
mode_filter = mode_options[selected_mode]

# Build WHERE clause based on filters
where_clauses = [
    f"CAST(pickup_datetime AS DATE) BETWEEN '{start_date}' AND '{end_date}'"
]

if mode_filter != "all":
    where_clauses.append(f"trip_type = '{mode_filter}'")

where_clause = " AND ".join(where_clauses)

# ==========================
# KEY METRICS
# ==========================
st.header("📈 Key Metrics")

metrics_query = f"""
    SELECT
        COUNT(*) as total_trips,
        AVG(trip_distance) as avg_distance,
        SUM(revenue) as total_revenue,
        AVG(trip_duration_minutes) as avg_duration,
        COUNT(DISTINCT trip_type) as num_modes
    FROM core_core.fct_trips
    WHERE {where_clause}
"""

metrics = load_data(metrics_query)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Total Trips",
        format_large_number(metrics['total_trips'].iloc[0])
    )

with col2:
    st.metric(
        "Avg Distance",
        f"{metrics['avg_distance'].iloc[0]:.2f} mi"
    )

with col3:
    total_rev = metrics['total_revenue'].iloc[0]
    if pd.notna(total_rev):
        st.metric("Total Revenue", f"${format_large_number(total_rev)}")
    else:
        st.metric("Total Revenue", "N/A")

with col4:
    st.metric(
        "Avg Duration",
        f"{metrics['avg_duration'].iloc[0]:.1f} min"
    )

with col5:
    st.metric(
        "Transport Modes",
        f"{metrics['num_modes'].iloc[0]}"
    )

# ==========================
# DAILY TRENDS
# ==========================
st.header("📅 Daily Trends")

daily_query = f"""
    SELECT
        CAST(pickup_datetime AS DATE) as date,
        trip_type,
        COUNT(*) as trips,
        AVG(trip_distance) as avg_distance
    FROM core_core.fct_trips
    WHERE {where_clause}
    GROUP BY 1, 2
    ORDER BY 1, 2
"""

daily_data = load_data(daily_query)

if len(daily_data) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Daily Trip Volume by Mode")
        fig = px.line(
            daily_data,
            x='date',
            y='trips',
            color='trip_type',
            title='Daily Trips by Transportation Mode',
            labels={'trips': 'Number of Trips', 'date': 'Date', 'trip_type': 'Mode'}
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Average Trip Distance by Mode")
        fig = px.line(
            daily_data,
            x='date',
            y='avg_distance',
            color='trip_type',
            title='Daily Average Distance by Mode',
            labels={'avg_distance': 'Avg Distance (mi)', 'date': 'Date', 'trip_type': 'Mode'}
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data available for the selected filters")

# ==========================
# HOURLY PATTERNS
# ==========================
st.header("🕐 Hourly Patterns")

hourly_query = f"""
    SELECT
        pickup_hour,
        trip_type,
        COUNT(*) as trips,
        AVG(trip_duration_minutes) as avg_duration
    FROM core_core.fct_trips
    WHERE {where_clause}
    GROUP BY 1, 2
    ORDER BY 1, 2
"""

hourly_data = load_data(hourly_query)

if len(hourly_data) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Trips by Hour of Day")
        fig = px.bar(
            hourly_data,
            x='pickup_hour',
            y='trips',
            color='trip_type',
            title='Trip Volume by Hour',
            labels={'pickup_hour': 'Hour of Day', 'trips': 'Number of Trips', 'trip_type': 'Mode'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Average Duration by Hour")
        fig = px.line(
            hourly_data,
            x='pickup_hour',
            y='avg_duration',
            color='trip_type',
            title='Average Trip Duration by Hour',
            labels={'pickup_hour': 'Hour of Day', 'avg_duration': 'Avg Duration (min)', 'trip_type': 'Mode'}
        )
        st.plotly_chart(fig, use_container_width=True)

# ==========================
# WEATHER IMPACT
# ==========================
st.header("🌦️ Weather Impact")

# Check if we have weather data
weather_check_query = f"""
    SELECT COUNT(*) as count
    FROM core_core.fct_trips
    WHERE {where_clause}
    AND temperature_fahrenheit IS NOT NULL
"""
weather_check = load_data(weather_check_query)

if weather_check['count'].iloc[0] > 0:
    weather_query = f"""
        SELECT
            ROUND(temperature_fahrenheit / 10) * 10 as temp_bucket,
            trip_type,
            COUNT(*) as trips,
            AVG(trip_distance) as avg_distance
        FROM core_core.fct_trips
        WHERE {where_clause}
        AND temperature_fahrenheit IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2
    """

    weather_data = load_data(weather_query)

    if len(weather_data) > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Trips by Temperature")
            fig = px.bar(
                weather_data,
                x='temp_bucket',
                y='trips',
                color='trip_type',
                title='Trip Volume by Temperature',
                labels={'temp_bucket': 'Temperature (°F)', 'trips': 'Number of Trips', 'trip_type': 'Mode'},
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Distance vs Temperature")
            fig = px.scatter(
                weather_data,
                x='temp_bucket',
                y='avg_distance',
                color='trip_type',
                size='trips',
                title='Average Distance by Temperature',
                labels={'temp_bucket': 'Temperature (°F)', 'avg_distance': 'Avg Distance (mi)', 'trip_type': 'Mode'}
            )
            st.plotly_chart(fig, use_container_width=True)

    # Precipitation analysis
    precip_query = f"""
        SELECT
            CASE
                WHEN precipitation = 0 THEN 'No Rain'
                WHEN precipitation < 0.1 THEN 'Light'
                WHEN precipitation < 0.3 THEN 'Moderate'
                ELSE 'Heavy'
            END as rain_level,
            trip_type,
            COUNT(*) as trips
        FROM core_core.fct_trips
        WHERE {where_clause}
        AND precipitation IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2
    """

    precip_data = load_data(precip_query)

    if len(precip_data) > 0:
        st.subheader("Impact of Precipitation")
        fig = px.bar(
            precip_data,
            x='rain_level',
            y='trips',
            color='trip_type',
            title='Trips by Precipitation Level',
            labels={'rain_level': 'Precipitation Level', 'trips': 'Number of Trips', 'trip_type': 'Mode'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Weather data not available for the selected date range. Weather join coverage may be incomplete.")

# ==========================
# MODE COMPARISON
# ==========================
st.header("🚗 Mode Comparison")

mode_query = f"""
    SELECT
        trip_type,
        COUNT(*) as total_trips,
        AVG(trip_distance) as avg_distance,
        AVG(trip_duration_minutes) as avg_duration,
        SUM(revenue) as total_revenue,
        AVG(revenue) as avg_revenue
    FROM core_core.fct_trips
    WHERE {where_clause}
    GROUP BY 1
    ORDER BY 2 DESC
"""

mode_data = load_data(mode_query)

if len(mode_data) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Trip Distribution by Mode")
        fig = px.pie(
            mode_data,
            values='total_trips',
            names='trip_type',
            title='Percentage of Trips by Mode'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Comparison Table")
        display_df = mode_data.copy()
        display_df['total_trips'] = display_df['total_trips'].apply(lambda x: f"{x:,}")
        display_df['avg_distance'] = display_df['avg_distance'].apply(lambda x: f"{x:.2f}")
        display_df['avg_duration'] = display_df['avg_duration'].apply(lambda x: f"{x:.1f}")
        display_df['total_revenue'] = display_df['total_revenue'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
        display_df['avg_revenue'] = display_df['avg_revenue'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")

        st.dataframe(
            display_df.rename(columns={
                'trip_type': 'Mode',
                'total_trips': 'Total Trips',
                'avg_distance': 'Avg Distance (mi)',
                'avg_duration': 'Avg Duration (min)',
                'total_revenue': 'Total Revenue',
                'avg_revenue': 'Avg Revenue'
            }),
            use_container_width=True,
            hide_index=True
        )

# ==========================
# WEEKEND VS WEEKDAY
# ==========================
st.header("📆 Weekend vs Weekday")

weekend_query = f"""
    SELECT
        is_weekend,
        trip_type,
        COUNT(*) as trips,
        AVG(trip_distance) as avg_distance,
        AVG(trip_duration_minutes) as avg_duration
    FROM core_core.fct_trips
    WHERE {where_clause}
    GROUP BY 1, 2
    ORDER BY 1, 2
"""

weekend_data = load_data(weekend_query)

if len(weekend_data) > 0:
    weekend_data['day_category'] = weekend_data['is_weekend'].apply(lambda x: 'Weekend' if x else 'Weekday')

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Trip Volume: Weekend vs Weekday")
        fig = px.bar(
            weekend_data,
            x='day_category',
            y='trips',
            color='trip_type',
            title='Trips by Day Type',
            labels={'day_category': 'Day Type', 'trips': 'Number of Trips', 'trip_type': 'Mode'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Average Distance: Weekend vs Weekday")
        fig = px.bar(
            weekend_data,
            x='day_category',
            y='avg_distance',
            color='trip_type',
            title='Average Distance by Day Type',
            labels={'day_category': 'Day Type', 'avg_distance': 'Avg Distance (mi)', 'trip_type': 'Mode'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("**NYC Mobility & Weather Analytics** | Data powered by dbt + DuckDB + Dagster")
