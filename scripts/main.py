import duckdb
import logging
from pathlib import Path

# Basic logging setup to trace pipeline execution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Standardized path configurations for 2026-04
RAW_DATA_PATH = "data/raw/yellow_tripdata_2026-04.parquet"
STAGING_DIR = Path("data/staging")
PROCESSED_DIR = Path("data/processed")

STAGING_DATA_PATH = STAGING_DIR / "taxi_cleaned_2026_04.parquet"

def create_connection():
    """Creates a DuckDB connection (using in-memory mode for batch processing)"""
    return duckdb.connect(':memory:')

def clean_raw_data(con, raw_path, staging_path):
    """Reads raw data, applies quality rules (filters), and saves reliable intermediate data (Silver Layer)."""
    logging.info("Cleansing raw data...")
    query = f"""
        COPY (
            SELECT * FROM '{raw_path}'
            WHERE total_amount > 0 
              AND fare_amount > 0
              AND trip_distance > 0
              AND tpep_pickup_datetime >= '2026-04-01' 
              AND tpep_pickup_datetime < '2026-05-01'
        ) TO '{staging_path}' (FORMAT PARQUET)
    """
    con.execute(query)

def transform_daily_metrics(staging_path):
    """Calculates daily metrics: volume, average ticket, and tips."""
    logging.info("Transforming data: Daily Metrics...")
    query = f"""
        SELECT 
            tpep_pickup_datetime::DATE AS date,
            COUNT(*) AS total_trips,
            AVG(total_amount) AS avg_ticket,
            AVG(tip_amount / NULLIF(fare_amount, 0)) * 100 AS tip_percentage
        FROM '{staging_path}'
        GROUP BY 1
    """
    return query

def transform_hourly_mobility(staging_path):
    """Generates hourly mobility metrics including average speed."""
    logging.info("Transforming data: Hourly Mobility Metrics...")
    query = f"""
        SELECT 
            EXTRACT(HOUR FROM tpep_pickup_datetime) AS hour_of_day,
            COUNT(*) AS total_trips,
            AVG(epoch(tpep_dropoff_datetime - tpep_pickup_datetime) / 60.0) AS avg_duration_min,
            AVG(trip_distance) AS avg_distance,
            AVG(trip_distance / (NULLIF(epoch(tpep_dropoff_datetime - tpep_pickup_datetime), 0) / 3600.0)) AS avg_speed_mph
        FROM '{staging_path}'
        WHERE epoch(tpep_dropoff_datetime - tpep_pickup_datetime) BETWEEN 60 AND 10800
        GROUP BY 1
        ORDER BY 1
    """
    return query

def transform_airport_metrics(staging_path):
    """Calculates metrics for airport trips (JFK, Newark) vs standard trips."""
    logging.info("Transforming data: Airport Metrics...")
    query = f"""
        SELECT 
            CASE 
                WHEN RatecodeID = 2 THEN 'JFK'
                WHEN RatecodeID = 3 THEN 'Newark'
                ELSE 'Standard' 
            END AS trip_type,
            COUNT(*) AS total_trips,
            AVG(trip_distance) AS avg_distance_miles,
            AVG(total_amount) AS avg_ticket,
            AVG(tip_amount) AS avg_tip,
            AVG(tolls_amount) AS avg_tolls,
            AVG(Airport_fee) AS avg_airport_fee,
            AVG(total_amount / NULLIF(trip_distance, 0)) AS revenue_per_mile
        FROM '{staging_path}'
        GROUP BY 1
    """
    return query

def transform_payment_metrics(staging_path):
    """Calculates payment method distribution and tip rates."""
    logging.info("Transforming data: Payment Method Metrics...")
    query = f"""
        SELECT 
            CASE payment_type 
                WHEN 1 THEN 'Credit Card'
                WHEN 2 THEN 'Cash'
                WHEN 3 THEN 'No Charge'
                WHEN 4 THEN 'Dispute'
                ELSE 'Other' 
            END AS payment_method,
            COUNT(*) AS total_trips,
            AVG(fare_amount) AS avg_fare,
            AVG(tip_amount) AS avg_tip,
            AVG(tip_amount / NULLIF(fare_amount, 0)) * 100 AS avg_tip_percentage
        FROM '{staging_path}'
        GROUP BY payment_type
    """
    return query

def transform_speed_metrics(staging_path):
    """Calculates average trip speed grouped by hour of the day."""
    logging.info("Transforming data: Speed/Traffic Metrics...")
    query = f"""
        SELECT 
            hour(tpep_pickup_datetime) AS hour_of_day,
            COUNT(*) AS total_trips,
            AVG(trip_distance) AS avg_distance,
            AVG(trip_distance / (NULLIF(epoch(tpep_dropoff_datetime - tpep_pickup_datetime), 0) / 3600.0)) AS avg_speed_mph
        FROM '{staging_path}'
        WHERE epoch(tpep_dropoff_datetime - tpep_pickup_datetime) BETWEEN 60 AND 10800
        GROUP BY 1
        ORDER BY 1
    """
    return query

def transform_weekday_metrics(staging_path):
    """Calculates aggregated metrics by day of the week (volume and average tip)."""
    logging.info("Transforming data: Weekday Metrics...")
    query = f"""
        SELECT 
            dayname(tpep_pickup_datetime) AS weekday,
            dayofweek(tpep_pickup_datetime) AS weekday_order,
            COUNT(*) AS total_trips,
            COUNT(DISTINCT tpep_pickup_datetime::DATE) AS occurrences,
            COUNT(*) / COUNT(DISTINCT tpep_pickup_datetime::DATE) AS avg_daily_trips,
            AVG(tip_amount) AS avg_tip_amount,
            AVG(tip_amount / NULLIF(fare_amount, 0)) * 100 AS avg_tip_percentage
        FROM '{staging_path}'
        GROUP BY 1, 2
        ORDER BY weekday_order
    """
    return query

def load_to_parquet(con, query, output_filename):
    """Executes SQL query and exports the result set to a Parquet file."""
    output_path = PROCESSED_DIR / output_filename
    logging.info(f"Exporting results to: {output_path}")
    
    # Executes direct copy to Parquet
    con.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")

def main():
    # 1. Ensure output directory structure exists
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    con = create_connection()
    
    try:
        logging.info("Starting ETL Pipeline (Medallion Architecture)...")
        
        # Step 1: Cleansing (Generates Silver Layer)
        clean_raw_data(con, RAW_DATA_PATH, STAGING_DATA_PATH)
        
        # Step 2: Analytical Transformations (Generates Gold Layer)
        load_to_parquet(con, transform_daily_metrics(STAGING_DATA_PATH), "mart_daily_metrics_2026_04.parquet")
        load_to_parquet(con, transform_hourly_mobility(STAGING_DATA_PATH), "mart_hourly_mobility_2026_04.parquet")
        load_to_parquet(con, transform_airport_metrics(STAGING_DATA_PATH), "mart_airport_revenue_2026_04.parquet")
        load_to_parquet(con, transform_payment_metrics(STAGING_DATA_PATH), "mart_payment_taxes_2026_04.parquet")
        load_to_parquet(con, transform_speed_metrics(STAGING_DATA_PATH), "mart_speed_metrics_2026_04.parquet")
        load_to_parquet(con, transform_weekday_metrics(STAGING_DATA_PATH), "mart_weekday_metrics_2026_04.parquet")
        
        logging.info("ETL Pipeline completed successfully! All Data Marts were generated.")
    except Exception as e:
        logging.error(f"Error during ETL execution: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
