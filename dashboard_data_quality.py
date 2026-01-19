"""
NYC Mobility & Weather Analytics - Data Completeness Dashboard

A monitoring dashboard for data engineers and analysts to verify:
- Data coverage by month and day
- Backfill status and gaps
- Data quality metrics (weather coverage, test results)
- Trip volume trends and anomalies

Run with: poetry run streamlit run dashboard_data_quality.py
"""

import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="NYC Mobility - Data Quality Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database connection
DB_PATH = Path(__file__).parent / "data" / "nyc_mobility.duckdb"


def get_connection():
    """Create a fresh read-only DuckDB connection."""
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_summary():
    """Load overall data summary statistics."""
    conn = get_connection()
    try:
        query = """
        SELECT
            MIN(CAST(pickup_datetime AS DATE)) as earliest_date,
            MAX(CAST(pickup_datetime AS DATE)) as latest_date,
            COUNT(*) as total_trips,
            COUNT(DISTINCT CAST(pickup_datetime AS DATE)) as days_with_data,
            COUNT(DISTINCT DATE_TRUNC('month', pickup_datetime)) as months_with_data,
            COUNT(DISTINCT trip_type) as trip_types,
            SUM(CASE WHEN temp_category IS NOT NULL THEN 1 ELSE 0 END) as trips_with_weather,
            ROUND(100.0 * SUM(CASE WHEN temp_category IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 4) as weather_coverage_pct
        FROM core_core.fct_trips
        """
        return conn.execute(query).fetchdf()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_monthly_summary():
    """Load trip counts by month and trip type."""
    conn = get_connection()
    try:
        query = """
        SELECT
            DATE_TRUNC('month', pickup_datetime) as month,
            trip_type,
            COUNT(*) as trip_count,
            COUNT(DISTINCT CAST(pickup_datetime AS DATE)) as days_in_month,
            SUM(CASE WHEN temp_category IS NOT NULL THEN 1 ELSE 0 END) as trips_with_weather,
            ROUND(100.0 * SUM(CASE WHEN temp_category IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as weather_coverage_pct,
            MIN(pickup_datetime) as first_trip,
            MAX(pickup_datetime) as last_trip
        FROM core_core.fct_trips
        GROUP BY DATE_TRUNC('month', pickup_datetime), trip_type
        ORDER BY month, trip_type
        """
        return conn.execute(query).fetchdf()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_daily_summary():
    """Load trip counts by day for heatmap."""
    conn = get_connection()
    try:
        query = """
        SELECT
            CAST(pickup_datetime AS DATE) as date,
            COUNT(*) as trip_count,
            SUM(CASE WHEN trip_type = 'yellow_taxi' THEN 1 ELSE 0 END) as yellow_taxi_trips,
            SUM(CASE WHEN trip_type = 'fhv' THEN 1 ELSE 0 END) as fhv_trips,
            SUM(CASE WHEN trip_type = 'citibike' THEN 1 ELSE 0 END) as citibike_trips,
            SUM(CASE WHEN temp_category IS NOT NULL THEN 1 ELSE 0 END) as trips_with_weather
        FROM core_core.fct_trips
        GROUP BY CAST(pickup_datetime AS DATE)
        ORDER BY date
        """
        return conn.execute(query).fetchdf()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_hourly_coverage():
    """Load trip counts by hour to detect gaps."""
    conn = get_connection()
    try:
        query = """
        SELECT
            DATE_TRUNC('hour', pickup_datetime) as hour,
            COUNT(*) as trip_count,
            COUNT(DISTINCT trip_type) as trip_types_present
        FROM core_core.fct_trips
        GROUP BY DATE_TRUNC('hour', pickup_datetime)
        ORDER BY hour
        """
        return conn.execute(query).fetchdf()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def detect_date_gaps():
    """Detect gaps in date coverage."""
    conn = get_connection()
    try:
        query = """
        WITH date_range AS (
            SELECT
                MIN(CAST(pickup_datetime AS DATE)) as min_date,
                MAX(CAST(pickup_datetime AS DATE)) as max_date
            FROM core_core.fct_trips
        ),
        expected_dates AS (
            SELECT unnest(
                generate_series(
                    (SELECT min_date FROM date_range),
                    (SELECT max_date FROM date_range),
                    INTERVAL '1 day'
                )
            )::date as expected_date
        ),
        actual_dates AS (
            SELECT DISTINCT CAST(pickup_datetime AS DATE) as actual_date
            FROM core_core.fct_trips
        ),
        missing_dates AS (
            SELECT
                e.expected_date,
                CASE WHEN a.actual_date IS NULL THEN 1 ELSE 0 END as is_missing
            FROM expected_dates e
            LEFT JOIN actual_dates a ON e.expected_date = a.actual_date
        )
        SELECT
            expected_date,
            is_missing
        FROM missing_dates
        WHERE is_missing = 1
        ORDER BY expected_date
        """
        return conn.execute(query).fetchdf()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_data_quality_metrics():
    """Load data quality test results if available."""
    conn = get_connection()
    try:
        # Try to get test results from dbt
        query = """
        SELECT
            'Weather Coverage' as metric,
            weather_coverage_pct as value,
            CASE
                WHEN weather_coverage_pct >= 99.99 THEN 'Excellent'
                WHEN weather_coverage_pct >= 99.0 THEN 'Good'
                WHEN weather_coverage_pct >= 95.0 THEN 'Fair'
                ELSE 'Poor'
            END as status
        FROM (
            SELECT ROUND(100.0 * SUM(CASE WHEN temp_category IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 4) as weather_coverage_pct
            FROM core_core.fct_trips
        )
        """
        return conn.execute(query).fetchdf()
    except Exception:
        # If test results table doesn't exist, return empty
        return pd.DataFrame(columns=['metric', 'value', 'status'])
    finally:
        conn.close()


# ============================================
# Main Dashboard Layout
# ============================================

st.title("📊 Data Completeness & Quality Dashboard")
st.markdown("**Monitor data coverage, backfill status, and quality metrics**")

# Refresh button
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
with col2:
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

st.divider()

# ============================================
# Section 1: Overview Metrics
# ============================================

st.header("📈 Overview Metrics")

try:
    summary_df = load_data_summary()

    if summary_df.empty:
        st.error("❌ No data found in fct_trips. Please run data ingestion first.")
        st.stop()

    summary = summary_df.iloc[0]

    # Key metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            label="Total Trips",
            value=f"{summary['total_trips']:,.0f}",
            help="Total number of trips across all modes"
        )

    with col2:
        date_range_days = (summary['latest_date'] - summary['earliest_date']).days + 1
        st.metric(
            label="Date Range",
            value=f"{date_range_days} days",
            delta=f"{summary['earliest_date'].strftime('%b %d')} - {summary['latest_date'].strftime('%b %d, %Y')}",
            help="Span from earliest to latest trip date"
        )

    with col3:
        coverage_pct = (summary['days_with_data'] / date_range_days) * 100
        st.metric(
            label="Day Coverage",
            value=f"{summary['days_with_data']} days",
            delta=f"{coverage_pct:.1f}% of range",
            delta_color="normal" if coverage_pct >= 95 else "off",
            help="Number of days with at least 1 trip"
        )

    with col4:
        st.metric(
            label="Weather Coverage",
            value=f"{summary['weather_coverage_pct']:.4f}%",
            delta="Excellent" if summary['weather_coverage_pct'] >= 99.99 else "Check data",
            delta_color="normal" if summary['weather_coverage_pct'] >= 99.99 else "off",
            help="Percentage of trips with weather data"
        )

    with col5:
        st.metric(
            label="Months Loaded",
            value=f"{summary['months_with_data']:.0f}",
            help="Number of distinct months with data"
        )

    # Warning if weather coverage is low
    if summary['weather_coverage_pct'] < 99.99:
        st.warning(
            f"⚠️ Weather coverage is {summary['weather_coverage_pct']:.2f}% (target: 99.99%). "
            f"Missing weather for {summary['total_trips'] - summary['trips_with_weather']:,.0f} trips. "
            "Run full refresh if this is due to a backfill."
        )

except Exception as e:
    st.error(f"❌ Error loading data summary: {e}")
    st.stop()

st.divider()

# ============================================
# Section 2: Monthly Breakdown
# ============================================

st.header("📅 Monthly Data Completeness")

try:
    monthly_df = load_monthly_summary()

    # Create pivot table for visualization
    monthly_pivot = monthly_df.pivot_table(
        index='month',
        columns='trip_type',
        values='trip_count',
        fill_value=0
    ).reset_index()

    # Convert month to string for better display
    monthly_pivot['month_str'] = monthly_pivot['month'].dt.strftime('%Y-%m')

    # Total trips per month
    monthly_total = monthly_df.groupby('month')['trip_count'].sum().reset_index()
    monthly_total['month_str'] = monthly_total['month'].dt.strftime('%Y-%m')

    # Stacked bar chart
    fig_monthly = go.Figure()

    trip_types = ['yellow_taxi', 'fhv', 'citibike']
    colors = {'yellow_taxi': '#FFD700', 'fhv': '#4169E1', 'citibike': '#32CD32'}

    for trip_type in trip_types:
        if trip_type in monthly_pivot.columns:
            fig_monthly.add_trace(go.Bar(
                name=trip_type.replace('_', ' ').title(),
                x=monthly_pivot['month_str'],
                y=monthly_pivot[trip_type],
                marker_color=colors.get(trip_type, '#999999'),
                text=monthly_pivot[trip_type].apply(lambda x: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'),
                textposition='inside',
            ))

    fig_monthly.update_layout(
        title="Trip Volume by Month and Type",
        xaxis_title="Month",
        yaxis_title="Number of Trips",
        barmode='stack',
        height=400,
        hovermode='x unified',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig_monthly, use_container_width=True)

    # Detailed monthly table
    with st.expander("📋 View Detailed Monthly Statistics"):
        # Aggregate by month for summary
        monthly_summary = monthly_df.groupby('month').agg({
            'trip_count': 'sum',
            'days_in_month': 'first',
            'trips_with_weather': 'sum',
            'weather_coverage_pct': 'mean',
            'first_trip': 'min',
            'last_trip': 'max'
        }).reset_index()

        monthly_summary['month_str'] = monthly_summary['month'].dt.strftime('%Y-%m')
        monthly_summary['avg_trips_per_day'] = (monthly_summary['trip_count'] / monthly_summary['days_in_month']).astype(int)

        # Add status column
        def get_status(row):
            if row['trip_count'] < 100000:
                return "⚠️ Low Volume"
            elif row['weather_coverage_pct'] < 99:
                return "⚠️ Weather Issues"
            elif row['days_in_month'] < 28:
                return "ℹ️ Partial Month"
            else:
                return "✅ Complete"

        monthly_summary['status'] = monthly_summary.apply(get_status, axis=1)

        display_cols = ['month_str', 'trip_count', 'days_in_month', 'avg_trips_per_day',
                        'weather_coverage_pct', 'status']
        display_df = monthly_summary[display_cols].copy()
        display_df.columns = ['Month', 'Total Trips', 'Days', 'Avg Trips/Day', 'Weather %', 'Status']

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Total Trips": st.column_config.NumberColumn(format="%d"),
                "Avg Trips/Day": st.column_config.NumberColumn(format="%d"),
                "Weather %": st.column_config.NumberColumn(format="%.2f%%"),
            }
        )

        # Highlight any problematic months
        problematic = monthly_summary[monthly_summary['status'].str.contains('⚠️')]
        if not problematic.empty:
            st.warning(
                f"⚠️ {len(problematic)} month(s) need attention:\n\n" +
                "\n".join([f"- **{row['month_str']}**: {row['status']}" for _, row in problematic.iterrows()])
            )

except Exception as e:
    st.error(f"❌ Error loading monthly data: {e}")

st.divider()

# ============================================
# Section 3: Daily Coverage Heatmap
# ============================================

st.header("📊 Daily Coverage Heatmap")

try:
    daily_df = load_daily_summary()

    # Create calendar heatmap data
    daily_df['date'] = pd.to_datetime(daily_df['date'])
    daily_df['year'] = daily_df['date'].dt.year
    daily_df['month'] = daily_df['date'].dt.month
    daily_df['day'] = daily_df['date'].dt.day
    daily_df['weekday'] = daily_df['date'].dt.dayofweek
    daily_df['week'] = daily_df['date'].dt.isocalendar().week

    # Select metric to display
    metric_choice = st.radio(
        "Select metric to display:",
        options=['trip_count', 'yellow_taxi_trips', 'fhv_trips', 'citibike_trips', 'trips_with_weather'],
        format_func=lambda x: x.replace('_', ' ').title(),
        horizontal=True
    )

    # Create heatmap by month
    unique_months = daily_df[['year', 'month']].drop_duplicates().sort_values(['year', 'month'])

    for _, month_row in unique_months.iterrows():
        year, month = month_row['year'], month_row['month']
        month_data = daily_df[(daily_df['year'] == year) & (daily_df['month'] == month)].copy()

        if month_data.empty:
            continue

        # Create calendar grid
        month_name = pd.Timestamp(year=year, month=month, day=1).strftime('%B %Y')

        # Pivot for heatmap (day of week x week of month)
        month_data['week_of_month'] = ((month_data['day'] - 1) // 7) + 1

        heatmap_data = month_data.pivot_table(
            index='weekday',
            columns='week_of_month',
            values=metric_choice,
            fill_value=0
        )

        # Create heatmap
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=[f'Week {i}' for i in heatmap_data.columns],
            y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            colorscale='Blues',
            text=heatmap_data.values,
            texttemplate='%{text:,.0f}',
            textfont={"size": 10},
            hovertemplate='%{y}, %{x}<br>Trips: %{z:,.0f}<extra></extra>',
            colorbar=dict(title="Trips")
        ))

        fig_heatmap.update_layout(
            title=f"{month_name}",
            xaxis_title="",
            yaxis_title="",
            height=300,
        )

        st.plotly_chart(fig_heatmap, use_container_width=True)

except Exception as e:
    st.error(f"❌ Error loading daily coverage: {e}")

st.divider()

# ============================================
# Section 4: Gap Detection
# ============================================

st.header("🔍 Data Gap Detection")

try:
    gaps_df = detect_date_gaps()

    if gaps_df.empty:
        st.success("✅ No date gaps detected! All days in the date range have data.")
    else:
        st.warning(f"⚠️ Found {len(gaps_df)} day(s) with no data:")

        # Group consecutive gaps
        gaps_df['date_diff'] = gaps_df['expected_date'].diff().dt.days
        gaps_df['gap_group'] = (gaps_df['date_diff'] > 1).cumsum()

        gap_ranges = gaps_df.groupby('gap_group').agg({
            'expected_date': ['min', 'max', 'count']
        }).reset_index(drop=True)
        gap_ranges.columns = ['start_date', 'end_date', 'days_missing']

        # Display gap ranges
        for _, gap in gap_ranges.iterrows():
            if gap['days_missing'] == 1:
                st.markdown(f"- **{gap['start_date'].strftime('%Y-%m-%d')}**: 1 day missing")
            else:
                st.markdown(
                    f"- **{gap['start_date'].strftime('%Y-%m-%d')} to {gap['end_date'].strftime('%Y-%m-%d')}**: "
                    f"{gap['days_missing']} consecutive days missing"
                )

        # Suggest action
        if gap_ranges['days_missing'].max() > 3:
            st.error(
                "🚨 Large gap detected (>3 days). This likely indicates a backfill issue. "
                "Run the backfill job for the missing date range."
            )

            # Show backfill command suggestion
            missing_month = gaps_df['expected_date'].iloc[0]
            st.code(
                f"poetry run dagster job launch backfill_monthly_data \\\n"
                f"  --config '{{\"ops\": {{\"monthly_dlt_ingestion\": {{\"config\": "
                f"{{\"year\": {missing_month.year}, \"month\": {missing_month.month}}}}}}}}}'",
                language="bash"
            )

except Exception as e:
    st.error(f"❌ Error detecting gaps: {e}")

st.divider()

# ============================================
# Section 5: Data Quality Metrics
# ============================================

st.header("✅ Data Quality Metrics")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Weather Coverage by Month")

    try:
        monthly_df = load_monthly_summary()
        weather_by_month = monthly_df.groupby('month').agg({
            'trips_with_weather': 'sum',
            'trip_count': 'sum'
        }).reset_index()
        weather_by_month['coverage_pct'] = (
            100.0 * weather_by_month['trips_with_weather'] / weather_by_month['trip_count']
        )
        weather_by_month['month_str'] = weather_by_month['month'].dt.strftime('%Y-%m')

        fig_weather = go.Figure()
        fig_weather.add_trace(go.Bar(
            x=weather_by_month['month_str'],
            y=weather_by_month['coverage_pct'],
            marker_color=['green' if x >= 99.99 else 'orange' if x >= 99 else 'red'
                         for x in weather_by_month['coverage_pct']],
            text=weather_by_month['coverage_pct'].apply(lambda x: f'{x:.2f}%'),
            textposition='outside',
        ))

        fig_weather.add_hline(
            y=99.99,
            line_dash="dash",
            line_color="green",
            annotation_text="Target: 99.99%",
            annotation_position="right"
        )

        fig_weather.update_layout(
            xaxis_title="Month",
            yaxis_title="Weather Coverage %",
            height=400,
            showlegend=False,
            yaxis=dict(range=[95, 100.5])
        )

        st.plotly_chart(fig_weather, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading weather coverage: {e}")

with col2:
    st.subheader("Trip Type Distribution")

    try:
        # Pie chart of trip types
        type_summary = monthly_df.groupby('trip_type')['trip_count'].sum().reset_index()

        fig_pie = go.Figure(data=[go.Pie(
            labels=type_summary['trip_type'].apply(lambda x: x.replace('_', ' ').title()),
            values=type_summary['trip_count'],
            marker=dict(colors=[colors.get(t, '#999999') for t in type_summary['trip_type']]),
            textinfo='label+percent',
            textposition='inside',
            hovertemplate='%{label}<br>%{value:,.0f} trips<br>%{percent}<extra></extra>'
        )])

        fig_pie.update_layout(
            height=400,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1)
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading trip type distribution: {e}")

# Additional quality checks
st.subheader("Quality Checks Summary")

col1, col2, col3 = st.columns(3)

with col1:
    # Check for low-volume days
    daily_df = load_daily_summary()
    low_volume_days = len(daily_df[daily_df['trip_count'] < 10000])

    if low_volume_days == 0:
        st.success("✅ No low-volume days")
    else:
        st.warning(f"⚠️ {low_volume_days} day(s) with <10k trips")

with col2:
    # Check for missing weather
    summary = load_data_summary().iloc[0]
    missing_weather = summary['total_trips'] - summary['trips_with_weather']

    if missing_weather < 10:
        st.success(f"✅ Weather coverage excellent ({missing_weather} trips missing)")
    else:
        st.warning(f"⚠️ {missing_weather:,.0f} trips missing weather")

with col3:
    # Check for date gaps
    gaps = detect_date_gaps()

    if gaps.empty:
        st.success("✅ No date gaps")
    else:
        st.warning(f"⚠️ {len(gaps)} day(s) with gaps")

st.divider()

# ============================================
# Section 6: Backfill Recommendations
# ============================================

st.header("💡 Backfill Recommendations")

# Analyze data and provide recommendations
recommendations = []

# Check for low-volume months
monthly_df = load_monthly_summary()
monthly_totals = monthly_df.groupby('month')['trip_count'].sum()
avg_monthly_volume = monthly_totals.mean()

for month, count in monthly_totals.items():
    if count < 100000:
        month_str = month.strftime('%B %Y')
        recommendations.append({
            'severity': 'high',
            'month': month,
            'message': f"**{month_str}** has only {count:,.0f} trips (expected >100k). Likely missing data.",
            'action': f"Run backfill for {month.year}-{month.month:02d}"
        })
    elif count < avg_monthly_volume * 0.3:
        month_str = month.strftime('%B %Y')
        recommendations.append({
            'severity': 'medium',
            'month': month,
            'message': f"**{month_str}** has {count:,.0f} trips (70% below average). Partial data?",
            'action': f"Verify data completeness for {month.year}-{month.month:02d}"
        })

# Check for weather coverage issues
for _, row in monthly_df.groupby('month').agg({'weather_coverage_pct': 'mean'}).reset_index().iterrows():
    if row['weather_coverage_pct'] < 99:
        month_str = row['month'].strftime('%B %Y')
        recommendations.append({
            'severity': 'medium',
            'month': row['month'],
            'message': f"**{month_str}** has {row['weather_coverage_pct']:.2f}% weather coverage (target: 99.99%).",
            'action': f"Run dbt full-refresh or check weather data ingestion"
        })

# Display recommendations
if recommendations:
    # Sort by severity and month
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    recommendations.sort(key=lambda x: (severity_order[x['severity']], x['month']))

    st.warning(f"⚠️ Found {len(recommendations)} issue(s) requiring attention:")

    for rec in recommendations:
        icon = "🚨" if rec['severity'] == 'high' else "⚠️" if rec['severity'] == 'medium' else "ℹ️"
        st.markdown(f"{icon} {rec['message']}")
        st.markdown(f"   *Action: {rec['action']}*")

        # Show backfill command
        if 'backfill' in rec['action'].lower():
            month = rec['month']
            with st.expander(f"Show backfill command for {month.strftime('%B %Y')}"):
                st.code(
                    f"poetry run dagster job launch backfill_monthly_data \\\n"
                    f"  --config '{{\"ops\": {{\"monthly_dlt_ingestion\": {{\"config\": "
                    f"{{\"year\": {month.year}, \"month\": {month.month}}}}}}}}}'",
                    language="bash"
                )
else:
    st.success("✅ No backfill issues detected. Data looks complete!")

st.divider()

# ============================================
# Footer
# ============================================

st.markdown("---")
st.markdown(
    """
    **Data Completeness Dashboard** |
    [Documentation](orchestration/README.md#backfilling-historical-data) |
    [GitHub](https://github.com/yourusername/nyc-mobility-weather-analytics)

    💡 **Tip**: Refresh this dashboard after running backfills to verify success.
    """
)
