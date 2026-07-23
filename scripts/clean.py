# scripts/clean.py
import logging

def handle_nulls(raw_path: str) -> str:
    """Handles null values by applying substitutions with corporate sentinel values."""
    logging.info("Cleansing: Handling null values and applying strategic imputations...")
    return f"""
        SELECT 
            VendorID,
            tpep_pickup_datetime,
            tpep_dropoff_datetime,
            -- Logical imputation: If sensor fails (NULL or 0), assume 1 passenger (statistical mode)
            CASE 
                WHEN passenger_count IS NULL OR passenger_count = 0 THEN 1 
                ELSE passenger_count 
            END AS passenger_count,
            trip_distance,
            COALESCE(RatecodeID, 99) AS RatecodeID,
            COALESCE(store_and_fwd_flag, 'N') AS store_and_fwd_flag,
            PULocationID,
            DOLocationID,
            payment_type,
            fare_amount,
            extra,
            mta_tax,
            tip_amount,
            tolls_amount,
            improvement_surcharge,
            total_amount,
            congestion_surcharge,
            Airport_fee,
            COALESCE(cbd_congestion_fee, 0.0) AS cbd_congestion_fee
        FROM '{raw_path}'
    """

def standardize_types(source_cte: str) -> str:
    """Ensures physical data type correctness for Parquet schema (immunizing against schema drift)."""
    logging.info("Cleansing: Standardizing column data types (SQL Casts)...")
    return f"""
        SELECT 
            VendorID::INTEGER AS VendorID,
            tpep_pickup_datetime::TIMESTAMP AS tpep_pickup_datetime,
            tpep_dropoff_datetime::TIMESTAMP AS tpep_dropoff_datetime,
            passenger_count::INTEGER AS passenger_count,
            trip_distance::DOUBLE AS trip_distance,
            RatecodeID::INTEGER AS RatecodeID,
            store_and_fwd_flag::VARCHAR AS store_and_fwd_flag,
            PULocationID::INTEGER AS PULocationID,
            DOLocationID::INTEGER AS DOLocationID,
            payment_type::INTEGER AS payment_type,
            fare_amount::DOUBLE AS fare_amount,
            extra::DOUBLE AS extra,
            mta_tax::DOUBLE AS mta_tax,
            tip_amount::DOUBLE AS tip_amount,
            tolls_amount::DOUBLE AS tolls_amount,
            improvement_surcharge::DOUBLE AS improvement_surcharge,
            total_amount::DOUBLE AS total_amount,
            congestion_surcharge::DOUBLE AS congestion_surcharge,
            Airport_fee::DOUBLE AS Airport_fee,
            cbd_congestion_fee::DOUBLE AS cbd_congestion_fee
        FROM ({source_cte}) AS src
    """

def validate_domains(source_cte: str) -> str:
    """Applies business compliance filters to reject invalid records and refunded transactions."""
    logging.info("Cleansing: Validating business domain rules (P&L and Occupancy filter)...")
    return f"""
        SELECT * 
        FROM ({source_cte}) AS src
        WHERE total_amount > 0 
          AND fare_amount > 0
          AND trip_distance > 0 -- Minimum spatial threshold (eliminates GPS hangs and shadowing)
          AND payment_type BETWEEN 0 AND 6
          AND (RatecodeID BETWEEN 1 AND 6 OR RatecodeID = 99)
          AND passenger_count BETWEEN 1 AND 6 -- Physical capacity boundary for TLC vehicles
    """

def remove_outliers(source_cte: str) -> str:
    """Filters extreme spatial and temporal outliers (Safety Margins)."""
    logging.info("Cleansing: Removing time and space outliers (150 miles and 3h limits)...")
    return f"""
        SELECT * 
        FROM ({source_cte}) AS src
        WHERE date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime) BETWEEN 1 AND 180
          AND trip_distance <= 150.0
    """

def clean_raw_data(con, raw_path: str, staging_path: str):
    """Orchestrator linking Data Cleansing steps via CTEs and materializing Silver Layer."""
    logging.info("=== STARTING DATA CLEANSING PIPELINE (SILVER) ===")
    
    step_1 = handle_nulls(raw_path)
    step_2 = standardize_types(step_1)
    step_3 = validate_domains(step_2)
    step_4 = remove_outliers(step_3)
    
    orchestration_query = f"COPY ({step_4}) TO '{staging_path}' (FORMAT PARQUET)"
    con.execute(orchestration_query)
    logging.info(f"=== SILVER LAYER CONSOLIDATED SUCCESSFULLY AT: {staging_path} ===")