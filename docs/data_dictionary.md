# NYC Mobility & Weather Analytics - Data Dictionary

**Version:** 1.0
**Last Updated:** January 2026
**Data Period:** October-November 2025
**Total Records:** 12,475,274

---

## Table of Contents

- [Overview](#overview)
- [Yellow Taxi (`raw_data.yellow_taxi`)](#yellow-taxi-raw_datayellow_taxi)
- [For-Hire Vehicle (`raw_data.fhv_taxi`)](#for-hire-vehicle-raw_datafhv_taxi)
- [CitiBike Trips (`raw_data.trips`)](#citibike-trips-raw_datatrips)
- [Hourly Weather (`raw_data.hourly_weather`)](#hourly-weather-raw_datahourly_weather)
- [Data Quality Standards](#data-quality-standards)
- [Change Log](#change-log)

---

## Overview

This data dictionary documents all tables in the NYC Mobility & Weather Analytics platform. All tables are stored in DuckDB under the `raw_data` schema.

**Data Sources:**
- NYC TLC (Taxi & Limousine Commission) - Monthly Parquet files
- CitiBike System Data - Monthly CSV files (zipped)
- Open-Meteo Weather API - Hourly historical weather data

**Ingestion Method:** DLT (Data Load Tool) with automatic schema management

**Join Pattern:** All trip tables join to weather on hourly grain using:
```sql
DATE_TRUNC('hour', trip_timestamp) = DATE_TRUNC('hour', weather.timestamp)
```

---

## Yellow Taxi (`raw_data.yellow_taxi`)

**Description:** Trip records for NYC's iconic yellow taxi cabs that primarily serve Manhattan and airports.

**Grain:** One row per trip
**Primary Key:** Composite (`tpep_pickup_datetime`, `vendor_id`, `pu_location_id`)
**Row Count:** 8,610,143 trips
**Time Range:** October-November 2025
**Data Source:** NYC TLC Trip Record Data
**Update Frequency:** Monthly

### Schema

| Column Name | Data Type | Nullable | Description | Constraints | Sample Values |
|-------------|-----------|----------|-------------|-------------|---------------|
| `vendor_id` | BIGINT | No | Provider identifier (1=Creative Mobile, 2=VeriFone) | Valid values: 1, 2 | `1`, `2` |
| `tpep_pickup_datetime` | TIMESTAMP | No | Trip pickup date and time | PK component | `2025-10-01 08:15:23` |
| `tpep_dropoff_datetime` | TIMESTAMP | No | Trip dropoff date and time | Must be ≥ pickup_datetime | `2025-10-01 08:32:45` |
| `passenger_count` | BIGINT | Yes | Number of passengers (driver-entered) | 0-9 typical range | `1`, `2`, `5` |
| `trip_distance` | DOUBLE | No | Trip distance in miles (taximeter) | ≥ 0 | `2.5`, `10.3`, `0.8` |
| `ratecode_id` | BIGINT | Yes | Rate code (1=Standard, 2=JFK, 3=Newark, 4=Nassau/Westchester, 5=Negotiated, 6=Group) | 1-6 | `1`, `2` |
| `store_and_fwd_flag` | VARCHAR | Yes | Trip record stored in vehicle memory before sending (Y=Yes, N=No) | Y or N | `N`, `Y` |
| `pu_location_id` | BIGINT | Yes | TLC Taxi Zone where trip started | FK to TLC zones (1-265) | `161`, `237` |
| `do_location_id` | BIGINT | Yes | TLC Taxi Zone where trip ended | FK to TLC zones (1-265) | `234`, `48` |
| `payment_type` | BIGINT | Yes | Payment method (1=Credit, 2=Cash, 3=No charge, 4=Dispute, 5=Unknown, 6=Voided) | 1-6 | `1`, `2` |
| `fare_amount` | DOUBLE | No | Base fare calculated by taximeter | ≥ 0 | `12.50`, `45.00` |
| `extra` | DOUBLE | Yes | Miscellaneous extras (rush hour, overnight surcharge) | ≥ 0 | `0.50`, `1.00` |
| `mta_tax` | DOUBLE | Yes | MTA tax automatically triggered based on metered rate | $0.50 standard | `0.50` |
| `tip_amount` | DOUBLE | Yes | Tip amount (credit card tips only, cash tips not recorded) | ≥ 0 | `2.50`, `10.00` |
| `tolls_amount` | DOUBLE | Yes | Total tolls paid during trip | ≥ 0 | `0.00`, `5.76` |
| `improvement_surcharge` | DOUBLE | Yes | Improvement surcharge assessed on trips | $0.30 standard | `0.30` |
| `total_amount` | DOUBLE | No | Total amount charged to passenger (excludes cash tips) | ≥ 0 | `18.30`, `52.76` |
| `congestion_surcharge` | DOUBLE | Yes | Congestion surcharge for trips in Manhattan below 96th St | $2.50 or $2.75 | `2.50`, `0.00` |
| `airport_fee` | DOUBLE | Yes | Airport fee for JFK/LaGuardia pickups | $1.25 standard | `1.25`, `0.00` |
| `cbd_congestion_fee` | DOUBLE | Yes | Central Business District congestion fee | Variable | `1.50`, `0.00` |

### Business Rules

1. **Trip Duration**: `tpep_dropoff_datetime` must be after `tpep_pickup_datetime`
2. **Fare Logic**: `total_amount` should approximately equal: `fare_amount + extra + mta_tax + tip_amount + tolls_amount + improvement_surcharge + congestion_surcharge + airport_fee + cbd_congestion_fee`
3. **Tip Recording**: Cash tips are NOT included in `tip_amount` (credit card only)
4. **Location Zones**: Valid zone IDs range from 1-265 (NYC TLC Taxi Zones)
5. **Negative Fares**: Possible for refunds/disputes (indicated by `payment_type = 4`)

### Known Data Quality Issues

- ~2-5% of records have `passenger_count` = 0 (likely driver error)
- Some trips have `trip_distance` = 0 (short pickups/dropoffs)
- Outliers exist: trips >100 miles, fares >$500 (typically airport trips or data errors)
- Cash tips are not recorded in `tip_amount`

---

## For-Hire Vehicle (`raw_data.fhv_taxi`)

**Description:** Trip records for For-Hire Vehicles including Uber, Lyft, and other app-based ride services.

**Grain:** One row per trip
**Primary Key:** Composite (`pickup_datetime`, `dispatching_base_num`)
**Row Count:** 2,446,615 trips
**Time Range:** October 2025 only (November data not yet published by NYC TLC)
**Data Source:** NYC TLC For-Hire Vehicle Trip Record Data
**Update Frequency:** Monthly

### Schema

| Column Name | Data Type | Nullable | Description | Constraints | Sample Values |
|-------------|-----------|----------|-------------|-------------|---------------|
| `dispatching_base_num` | VARCHAR | No | TLC base license number of dispatching base | PK component, 6 chars | `B02764`, `B03404` |
| `pickup_datetime` | TIMESTAMP | No | Trip pickup date and time | PK component | `2025-10-15 14:23:11` |
| `drop_off_datetime` | TIMESTAMP | Yes | Trip dropoff date and time | Should be ≥ pickup_datetime | `2025-10-15 14:45:32` |
| `affiliated_base_number` | VARCHAR | Yes | TLC base license number of affiliated base | 6 chars | `B02764`, `B03404` |
| `p_ulocation_id` | BIGINT | Yes | TLC Taxi Zone where trip started | FK to TLC zones (1-265) | `79`, `132` |
| `d_olocation_id` | BIGINT | Yes | TLC Taxi Zone where trip ended | FK to TLC zones (1-265) | `234`, `161` |

### Business Rules

1. **Trip Duration**: `drop_off_datetime` should be after `pickup_datetime`
2. **Location Coverage**: FHV trips cover all 5 boroughs (broader geographic coverage than yellow taxis)
3. **Base Numbers**: Both `dispatching_base_num` and `affiliated_base_number` must be valid TLC-licensed bases
4. **Privacy**: FHV data does not include fare amounts, passenger counts, or payment information (privacy protection)

### Known Data Quality Issues

- ~15-20% of records have NULL `drop_off_datetime` (incomplete trip records)
- Some location IDs are NULL (trips outside NYC boundaries)
- November 2025 data not yet available (delayed publishing by NYC TLC)

---

## CitiBike Trips (`raw_data.trips`)

**Description:** Trip records from NYC's bike share system operated by CitiBike.

**Grain:** One row per bike trip
**Primary Key:** `ride_id` (unique identifier)
**Row Count:** 1,417,052 trips
**Time Range:** October-November 2025
**Data Source:** CitiBike System Data (via S3)
**Update Frequency:** Monthly

### Schema

| Column Name | Data Type | Nullable | Description | Constraints | Sample Values |
|-------------|-----------|----------|-------------|-------------|---------------|
| `ride_id` | VARCHAR | No | Unique identifier for each trip | PK, 16 chars | `A1B2C3D4E5F6G7H8` |
| `rideable_type` | VARCHAR | Yes | Type of bike used | 'classic_bike', 'electric_bike', 'docked_bike' | `electric_bike`, `classic_bike` |
| `started_at` | TIMESTAMP | No | Trip start date and time | Must be before `ended_at` | `2025-10-12 09:15:44` |
| `ended_at` | TIMESTAMP | No | Trip end date and time | Must be after `started_at` | `2025-10-12 09:32:18` |
| `start_station_name` | VARCHAR | Yes | Name of station where trip started | | `Broadway & W 39 St`, `1 Ave & E 68 St` |
| `start_station_id` | VARCHAR | Yes | Unique ID of start station | FK to stations | `7531.10`, `6338.05` |
| `end_station_name` | VARCHAR | Yes | Name of station where trip ended | | `8 Ave & W 31 St`, `Broadway & W 53 St` |
| `end_station_id` | VARCHAR | Yes | Unique ID of end station | FK to stations | `7643.08`, `6811.08` |
| `start_lat` | DOUBLE | Yes | Latitude of trip start location | -90 to 90 | `40.7536`, `40.7677` |
| `start_lng` | DOUBLE | Yes | Longitude of trip start location | -180 to 180 | `-73.9912`, `-73.9642` |
| `end_lat` | DOUBLE | Yes | Latitude of trip end location | -90 to 90 | `40.7504`, `40.7632` |
| `end_lng` | DOUBLE | Yes | Longitude of trip end location | -180 to 180 | `-73.9946`, `-73.9789` |
| `member_casual` | VARCHAR | Yes | User type: member (annual) or casual (single/day pass) | 'member' or 'casual' | `member`, `casual` |

### Business Rules

1. **Trip Duration**: `ended_at` must be after `started_at`
2. **Geographic Bounds**:
   - Latitude: 40.61°N to 40.89°N (covers Manhattan, Brooklyn, Queens, Bronx)
   - Longitude: -74.04°W to -73.85°W
3. **Station IDs**: Station IDs are formatted as `XXXX.YY` where XXXX is the base ID and YY is the sub-location
4. **Bike Types**: Classic bikes are pedal-only; electric bikes have pedal-assist
5. **Member Types**:
   - `member` = Annual or monthly subscribers
   - `casual` = Single ride or day pass users

### Known Data Quality Issues

- ~1-2% of trips have NULL station names (likely dockless returns or system issues)
- Some trips have identical start/end locations (very short rides or false starts)
- Electric bike adoption has increased significantly (now ~60% of trips)
- Station coordinates occasionally updated (stations can be relocated)

### Trip Duration Guidelines

- **Typical Range**: 5-45 minutes
- **Short Trips**: <5 minutes may indicate false starts or station issues
- **Long Trips**: >60 minutes incur overage fees (>45 min for casual, >60 min for members)
- **Outliers**: Trips >3 hours may indicate lost/stolen bikes

---

## Hourly Weather (`raw_data.hourly_weather`)

**Description:** Hourly historical weather observations for New York City from Open-Meteo Weather API.

**Grain:** One row per hour
**Primary Key:** `timestamp`
**Row Count:** 1,464 hours (61 days × 24 hours)
**Time Range:** October-November 2025
**Data Source:** Open-Meteo Historical Weather API
**Update Frequency:** Historical data (static for time period)
**Geographic Location:** 40.7128°N, 74.0060°W (Lower Manhattan)

### Schema

| Column Name | Data Type | Nullable | Description | Constraints | Sample Values | Unit |
|-------------|-----------|----------|-------------|-------------|---------------|------|
| `timestamp` | TIMESTAMP | No | Hour of observation (timezone-aware) | PK, hourly intervals | `2025-10-01 00:00:00` | - |
| `temp` | DOUBLE | Yes | Temperature at 2m above ground | Celsius | `15.2`, `8.7`, `22.1` | °C |
| `feels_like` | DOUBLE | Yes | Apparent temperature (wind chill/heat index) | Celsius | `13.5`, `7.2`, `23.4` | °C |
| `humidity` | BIGINT | Yes | Relative humidity | 0-100 | `65`, `82`, `45` | % |
| `dew_point` | DOUBLE | Yes | Dew point temperature | Celsius | `10.5`, `6.8`, `14.2` | °C |
| `precipitation` | DOUBLE | Yes | Total precipitation (rain + snow water equivalent) | mm, ≥ 0 | `0.0`, `2.5`, `8.1` | mm |
| `rain` | DOUBLE | Yes | Rainfall amount | mm, ≥ 0 | `0.0`, `2.5`, `5.3` | mm |
| `snowfall` | DOUBLE | Yes | Snowfall amount (water equivalent) | mm, ≥ 0 | `0.0`, `1.2` | mm |
| `cloud_cover` | BIGINT | Yes | Cloud coverage percentage | 0-100 | `25`, `90`, `0` | % |
| `pressure` | DOUBLE | Yes | Mean sea level atmospheric pressure | hPa | `1013.2`, `1020.5` | hPa |
| `wind_speed` | DOUBLE | Yes | Wind speed at 10m height | m/s, ≥ 0 | `3.5`, `8.2`, `0.5` | m/s |
| `wind_direction` | BIGINT | Yes | Wind direction (meteorological convention) | 0-360 degrees | `180`, `270`, `45` | ° |

### Business Rules

1. **Temporal Coverage**: Continuous hourly coverage with no gaps for Oct-Nov 2025
2. **Timezone**: All timestamps in America/New_York timezone (EST/EDT)
3. **Precipitation Components**: `precipitation` = `rain` + `snowfall` (water equivalent)
4. **Temperature Scale**: All temperatures in Celsius (convert to Fahrenheit: F = C × 9/5 + 32)
5. **Wind Direction**:
   - 0° = North
   - 90° = East
   - 180° = South
   - 270° = West
6. **Missing Values**: NULL indicates data not available from source (rare for Open-Meteo)

### Weather Variable Definitions

| Variable | Description | Typical Range (NYC Fall) | Extreme Values |
|----------|-------------|-------------------------|----------------|
| **Temperature** | Air temperature at 2m | 5-20°C (41-68°F) | -5 to 30°C |
| **Feels Like** | Perceived temperature with wind/humidity | 3-22°C (37-72°F) | -10 to 35°C |
| **Humidity** | Moisture saturation of air | 40-80% | 15-100% |
| **Precipitation** | Water falling from sky | 0-5mm/hr typical | 0-50mm/hr |
| **Wind Speed** | Speed at 10m height | 2-6 m/s (4-13 mph) | 0-25 m/s |
| **Pressure** | Atmospheric pressure | 1010-1025 hPa | 980-1040 hPa |
| **Cloud Cover** | Sky coverage by clouds | 20-70% | 0-100% |

### Spatial Accuracy Note

⚠️ **Single Weather Station Limitation**: Data represents conditions at Lower Manhattan (40.7128°N, 74.0060°W). Accuracy decreases with distance from this point.

**Accuracy by Distance:**
- **0-3 miles** (Central Manhattan): Excellent accuracy, <1°F variance
- **3-8 miles** (Core CitiBike area): Good accuracy, 1-3°F variance
- **8-15 miles** (Outer boroughs): Moderate accuracy, 3-5°F variance
- **15-20 miles** (Far edges): Lower accuracy, 5-10°F variance

**Suitable for:** City-wide trends, seasonal patterns, general weather-mobility correlations
**Limited for:** Neighborhood-level analysis, localized precipitation events

See [docs/data_model.md](data_model.md#weather-data-spatial-accuracy) for detailed spatial accuracy assessment.

---

## Data Quality Standards

### Completeness
- **Yellow Taxi**: 100% complete for Oct-Nov 2025
- **FHV**: 100% complete for Oct 2025; Nov 2025 not yet published
- **CitiBike**: 100% complete for Oct-Nov 2025
- **Weather**: 100% complete hourly coverage for Oct-Nov 2025

### Join Coverage
All trip tables achieve **100% join coverage** with weather data on hourly grain.

### Temporal Consistency
- All timestamps are timezone-aware (America/New_York)
- No temporal gaps or duplicate hours
- Hourly boundaries align perfectly for joins

### Data Validation Rules

| Check Type | Rule | Enforcement |
|------------|------|-------------|
| **Temporal** | Trip end time ≥ start time | Soft warning |
| **Numeric** | Fares, distances, counts ≥ 0 | Soft warning |
| **Referential** | Location IDs in range 1-265 | Soft warning |
| **Uniqueness** | Primary keys are unique | Hard constraint |
| **Nullability** | PK columns NOT NULL | Hard constraint |

### Known Limitations

1. **December 2025 Data**: Not available (month incomplete at time of ingestion)
2. **FHV November 2025**: Not published by NYC TLC yet
3. **TLC Zone Lookup**: Not yet loaded (needed for geographic analysis)
4. **CitiBike Station Metadata**: Embedded in trip records (no separate dimension)
5. **Weather Spatial Coverage**: Single station for entire NYC area

---

## Change Log

### Version 1.0 (January 2026)
- Initial data dictionary creation
- Documented all 4 tables in raw_data schema
- Added comprehensive column descriptions and business rules
- Included data quality notes and known limitations
- Total records: 12,475,274 (Oct-Nov 2025 data)

### Future Enhancements
- Add TLC Zone lookup table documentation (MVP 2)
- Add CitiBike station dimension table (MVP 2)
- Document Bronze/Silver/Gold layer tables (MVP 2+)
- Add dbt model lineage and transformations (MVP 2+)
- Include data quality test results and metrics (MVP 2+)

---

## Related Documentation

- [Data Model & ERD](data_model.md) - Entity relationships and join patterns
- [README](../README.md) - Project overview and setup
- [Jupyter Notebooks](../notebooks/) - Data exploration and analysis

---

**Maintained by:** NYC Mobility Analytics Team
**Questions?** See [docs/data_model.md](data_model.md) for detailed technical documentation.
