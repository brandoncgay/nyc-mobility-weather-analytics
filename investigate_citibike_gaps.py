#!/usr/bin/env python3
"""
CitiBike Data Gap Investigation Tool

Analyzes missing dates in CitiBike data and provides recommendations.
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "nyc_mobility.duckdb"

def investigate_citibike_gaps():
    """Investigate CitiBike data gaps and identify patterns."""

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    print('=' * 80)
    print('CITIBIKE DATA GAP INVESTIGATION')
    print('=' * 80)

    # Get monthly coverage
    query = '''
    SELECT
        DATE_TRUNC('month', started_at) as month,
        MIN(CAST(started_at AS DATE)) as first_date,
        MAX(CAST(started_at AS DATE)) as last_date,
        COUNT(DISTINCT CAST(started_at AS DATE)) as days_with_data,
        COUNT(*) as total_trips
    FROM raw_data.trips
    WHERE started_at >= '2025-05-01'
    GROUP BY DATE_TRUNC('month', started_at)
    ORDER BY month
    '''

    result = conn.execute(query).fetchdf()

    # 1. Monthly Summary
    print('\n1. MONTHLY SUMMARY')
    print('-' * 80)
    print(f'{"Month":<15} | {"Date Range":<20} | {"Days":<5} | {"Trips":>12}')
    print('-' * 80)

    for _, row in result.iterrows():
        month_str = row['month'].strftime('%B %Y')
        first = row['first_date'].strftime('%b %d')
        last = row['last_date'].strftime('%b %d')
        date_range = f'{first} to {last}'
        print(f'{month_str:<15} | {date_range:<20} | {row["days_with_data"]:>2d}    | {row["total_trips"]:>12,}')

    # 2. Missing Date Ranges
    print('\n2. MISSING DATE RANGES')
    print('-' * 80)

    gaps_found = []

    for _, row in result.iterrows():
        month_pd = row['month']
        month_start = pd.Timestamp(month_pd.year, month_pd.month, 1).date()

        # Calculate last day of month
        if month_pd.month == 12:
            next_month = pd.Timestamp(month_pd.year + 1, 1, 1)
        else:
            next_month = pd.Timestamp(month_pd.year, month_pd.month + 1, 1)
        month_end = (next_month - pd.Timedelta(days=1)).date()

        actual_first = pd.Timestamp(row['first_date']).date()
        actual_last = pd.Timestamp(row['last_date']).date()
        month_str = month_pd.strftime('%B %Y')

        # Check for gaps at start
        if actual_first > month_start:
            days_missing = (actual_first - month_start).days
            gap_end = actual_first - timedelta(days=1)
            print(f'{month_str:<15} | ❌ Missing START: {month_start} to {gap_end} ({days_missing} days)')
            gaps_found.append({
                'month': month_str,
                'type': 'start',
                'days': days_missing,
                'start_day': actual_first.day
            })

        # Check for gaps at end
        if actual_last < month_end:
            days_missing = (month_end - actual_last).days
            gap_start = actual_last + timedelta(days=1)
            print(f'{month_str:<15} | ❌ Missing END:   {gap_start} to {month_end} ({days_missing} days)')
            gaps_found.append({
                'month': month_str,
                'type': 'end',
                'days': days_missing,
                'end_day': actual_last.day
            })

        if actual_first == month_start and actual_last == month_end:
            print(f'{month_str:<15} | ✅ Complete month')

    # 3. Pattern Analysis
    print('\n3. PATTERN ANALYSIS')
    print('-' * 80)

    start_gaps = [g for g in gaps_found if g['type'] == 'start']
    end_gaps = [g for g in gaps_found if g['type'] == 'end']

    if start_gaps:
        print(f'\nMonths missing data from START: {len(start_gaps)}')
        start_days = [g['start_day'] for g in start_gaps]
        for gap in start_gaps:
            print(f'  • {gap["month"]}: Missing {gap["days"]} days (starts on day {gap["start_day"]})')

        if len(set(start_days)) == 1:
            print(f'\n  ⚠️  PATTERN: All incomplete months start on day {start_days[0]}')
        else:
            print(f'\n  📊 Various start days: {sorted(set(start_days))}')

    if end_gaps:
        print(f'\nMonths missing data from END: {len(end_gaps)}')
        for gap in end_gaps:
            print(f'  • {gap["month"]}: Missing {gap["days"]} days (ends on day {gap["end_day"]})')

    # 4. Source File Analysis
    print('\n4. SOURCE FILE HYPOTHESIS')
    print('-' * 80)

    if start_gaps:
        start_day = start_gaps[0]['start_day']
        if all(g['start_day'] == start_day for g in start_gaps):
            print(f'✅ Consistent pattern detected:')
            print(f'   All months with gaps start on day {start_day}')
            print(f'\n💡 HYPOTHESIS:')
            print(f'   CitiBike may be publishing preliminary data files mid-month')
            print(f'   Files named YYYYMM-citibike-tripdata.zip may only contain')
            print(f'   data from day {start_day} onwards when published early.')
            print(f'\n📋 RECOMMENDED ACTIONS:')
            print(f'   1. Check CitiBike S3 bucket for file metadata:')
            print(f'      aws s3 ls s3://tripdata/ --recursive | grep citibike-tripdata.zip')
            print(f'   2. Compare file sizes for complete vs incomplete months')
            print(f'   3. Check file Last-Modified dates')
            print(f'   4. Download sample file and inspect date range')
            print(f'   5. Contact CitiBike if files appear incomplete')

    # 5. Data Quality Impact
    print('\n5. DATA QUALITY IMPACT')
    print('-' * 80)

    total_trips = result['total_trips'].sum()

    # Convert to date for comparison
    result['first_day'] = pd.to_datetime(result['first_date']).dt.day
    complete_months = result[
        (result['first_day'] == 1) &
        (result['days_with_data'] >= 28)
    ]

    if len(complete_months) > 0:
        avg_complete_month = complete_months['total_trips'].mean()
        incomplete_months = len(result) - len(complete_months)
        estimated_missing = avg_complete_month * 0.43 * incomplete_months  # ~43% of month

        print(f'Complete months: {len(complete_months)}')
        print(f'Incomplete months: {incomplete_months}')
        print(f'Average trips/complete month: {avg_complete_month:,.0f}')
        print(f'Estimated missing trips: ~{estimated_missing:,.0f}')
        print(f'Current total trips: {total_trips:,.0f}')
        print(f'Potential total (if complete): ~{total_trips + estimated_missing:,.0f}')

    # 6. Check specific dates
    print('\n6. DETAILED DAY-BY-DAY CHECK (July 2025)')
    print('-' * 80)

    query_daily = '''
    SELECT
        CAST(started_at AS DATE) as date,
        COUNT(*) as trips
    FROM raw_data.trips
    WHERE started_at >= '2025-07-01' AND started_at < '2025-08-01'
    GROUP BY date
    ORDER BY date
    '''

    daily = conn.execute(query_daily).fetchdf()

    # Check for all dates in July
    july_dates = pd.date_range('2025-07-01', '2025-07-31', freq='D')
    july_dates_set = {d.date() for d in july_dates}
    daily_dates_set = {pd.Timestamp(d).date() for d in daily['date']}
    missing_dates = july_dates_set - daily_dates_set

    if missing_dates:
        print(f'Missing dates in July: {len(missing_dates)} days')
        for date in sorted(missing_dates)[:5]:
            print(f'  • {date}')
        if len(missing_dates) > 5:
            print(f'  ... and {len(missing_dates) - 5} more')
    else:
        print('✅ July has all dates')
        print('First 3 days:')
        print(daily.head(3).to_string(index=False))

    conn.close()

    print('\n' + '=' * 80)
    print('END OF INVESTIGATION')
    print('=' * 80)


if __name__ == '__main__':
    investigate_citibike_gaps()
