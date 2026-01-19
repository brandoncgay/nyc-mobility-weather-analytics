#!/usr/bin/env python3
"""
Check CitiBike source files to understand data availability.
"""

import requests
from datetime import datetime

# CitiBike S3 bucket base URL
BASE_URL = "https://s3.amazonaws.com/tripdata"

def check_file_metadata(year, month):
    """Check if a CitiBike data file exists and get metadata."""
    filename = f"{year}{month:02d}-citibike-tripdata.zip"
    url = f"{BASE_URL}/{filename}"

    try:
        # Send HEAD request to get file metadata without downloading
        response = requests.head(url, timeout=10)

        if response.status_code == 200:
            size_bytes = int(response.headers.get('Content-Length', 0))
            size_mb = size_bytes / (1024 * 1024)
            last_modified = response.headers.get('Last-Modified', 'Unknown')
            etag = response.headers.get('ETag', 'Unknown')

            return {
                'exists': True,
                'size_mb': size_mb,
                'last_modified': last_modified,
                'etag': etag,
                'url': url
            }
        elif response.status_code == 404:
            return {'exists': False, 'url': url}
        else:
            return {'exists': 'unknown', 'status': response.status_code, 'url': url}

    except Exception as e:
        return {'exists': 'error', 'error': str(e), 'url': url}


def main():
    print('=' * 80)
    print('CITIBIKE SOURCE FILE CHECK')
    print('=' * 80)
    print()
    print(f'Checking files at: {BASE_URL}')
    print()

    # Check months we have data for
    months_to_check = [
        (2025, 5, 'May 2025'),
        (2025, 6, 'June 2025'),
        (2025, 7, 'July 2025'),
        (2025, 8, 'August 2025'),
        (2025, 9, 'September 2025'),
        (2025, 10, 'October 2025'),
        (2025, 11, 'November 2025'),
        (2025, 12, 'December 2025'),
    ]

    print(f'{"Month":<15} | {"Status":<10} | {"Size (MB)":<12} | {"Last Modified"}')
    print('-' * 80)

    results = []
    for year, month, month_str in months_to_check:
        result = check_file_metadata(year, month)
        results.append((month_str, result))

        if result['exists'] == True:
            status = '✅ Found'
            size = f"{result['size_mb']:.1f}"
            modified = result['last_modified']
            print(f'{month_str:<15} | {status:<10} | {size:>12} | {modified}')
        elif result['exists'] == False:
            print(f'{month_str:<15} | ❌ Not Found | {"N/A":>12} | N/A')
        else:
            print(f'{month_str:<15} | ⚠️  Error    | {"N/A":>12} | {result.get("error", "Unknown")}')

    # Analyze file sizes
    print('\n' + '=' * 80)
    print('FILE SIZE ANALYSIS')
    print('=' * 80)

    complete_files = [(m, r) for m, r in results if r.get('exists') == True and r.get('size_mb', 0) > 0]

    if len(complete_files) >= 2:
        sizes = [r['size_mb'] for _, r in complete_files]
        avg_size = sum(sizes) / len(sizes)

        print(f'\nAverage file size: {avg_size:.1f} MB')
        print(f'Size range: {min(sizes):.1f} - {max(sizes):.1f} MB')
        print('\nComparison:')

        for month_str, result in complete_files:
            size = result['size_mb']
            pct_diff = ((size - avg_size) / avg_size) * 100

            if abs(pct_diff) > 30:
                flag = '⚠️'
            else:
                flag = '✅'

            print(f'  {flag} {month_str:<15}: {size:>7.1f} MB ({pct_diff:+.1f}% from avg)')

    # Recommendations
    print('\n' + '=' * 80)
    print('RECOMMENDATIONS')
    print('=' * 80)
    print()
    print('Based on the file check:')
    print()

    suspicious = [(m, r) for m, r in complete_files if r['size_mb'] < 50]
    if suspicious:
        print('⚠️  SUSPICIOUS FILES (unusually small):')
        for month_str, result in suspicious:
            print(f'   • {month_str}: {result["size_mb"]:.1f} MB')
            print(f'     May be incomplete or contain partial month data')
        print()

    print('📋 NEXT STEPS:')
    print('   1. Download a suspicious file and inspect the date range:')
    print('      wget https://s3.amazonaws.com/tripdata/202508-citibike-tripdata.zip')
    print('      unzip -l 202508-citibike-tripdata.zip')
    print()
    print('   2. Compare with a known complete month (Sept or Oct):')
    print('      wget https://s3.amazonaws.com/tripdata/202509-citibike-tripdata.zip')
    print()
    print('   3. Check CitiBike\'s data page for announcements:')
    print('      https://citibikenyc.com/system-data')
    print()
    print('   4. If files are incomplete, check back later or contact CitiBike')
    print()


if __name__ == '__main__':
    main()
