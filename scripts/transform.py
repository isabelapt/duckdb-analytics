# scripts/transform.py
import logging

def build_gold_data_marts(con, staging_path: str, output_dir: str):
    """
    Executes Gold Layer aggregations (Data Marts) from the Silver Layer,
    applying defensive mathematical functions (such as NULLIF) and exporting results to Parquet.
    """
    logging.info("=== STARTING DATA MARTS CONSTRUCTION (GOLD LAYER) ===")

    # 1. Data Mart: Daily Revenue & Operational Metrics
    logging.info("Materializing: Daily Metrics Data Mart...")
    daily_metrics_query = f"""
        COPY (
            SELECT 
                tpep_pickup_datetime::DATE AS trip_date,
                COUNT(*) AS total_trips,
                ROUND(SUM(total_amount), 2) AS gross_revenue,
                ROUND(AVG(total_amount), 2) AS avg_ticket,
                ROUND(AVG(trip_distance), 2) AS avg_distance_miles,
                ROUND(AVG(total_amount / NULLIF(trip_distance, 0)), 2) AS revenue_per_mile
            FROM '{staging_path}'
            GROUP BY 1
            ORDER BY 1 DESC
        ) TO '{output_dir}/mart_daily_metrics.parquet' (FORMAT PARQUET);
    """
    con.execute(daily_metrics_query)

    # 2. Data Mart: Hourly Mobility & Traffic Flow (Flow Context)
    logging.info("Materializing: Hourly Speed & Urban Traffic Flow Data Mart...")
    traffic_query = f"""
        COPY (
            SELECT 
                EXTRACT(HOUR FROM tpep_pickup_datetime) AS pickup_hour,
                COUNT(*) AS total_trips,
                ROUND(AVG(trip_distance), 2) AS avg_distance,
                ROUND(AVG(date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime)), 2) AS avg_duration_minutes,
                ROUND(AVG(trip_distance / (NULLIF(date_diff('minute', tpep_pickup_datetime, tpep_dropoff_datetime), 0) / 60.0)), 2) AS avg_speed_mph
            FROM '{staging_path}'
            GROUP BY 1
            ORDER BY pickup_hour ASC
        ) TO '{output_dir}/mart_hourly_traffic.parquet' (FORMAT PARQUET);
    """
    con.execute(traffic_query)

    # 3. Data Mart: CBD Congestion Fee Impact Analysis
    logging.info("Materializing: CBD Congestion Fee Impact Data Mart...")
    cbd_query = f"""
        COPY (
            SELECT 
                tpep_pickup_datetime::DATE AS trip_date,
                COUNT(*) AS total_trips,
                SUM(CASE WHEN cbd_congestion_fee > 0 THEN 1 ELSE 0 END) AS trips_with_cbd,
                ROUND(AVG(cbd_congestion_fee), 2) AS avg_cbd_fee_paid,
                ROUND(AVG(cbd_congestion_fee / NULLIF(total_amount, 0)) * 100, 2) AS cbd_share_of_total_revenue
            FROM '{staging_path}'
            GROUP BY 1
            ORDER BY 1 DESC
        ) TO '{output_dir}/mart_cbd_impact.parquet' (FORMAT PARQUET);
    """
    con.execute(cbd_query)

    # 4. Data Mart: Telemetry Signal Stability by Vendor
    logging.info("Materializing: Vendor Telemetry Signal Stability Data Mart...")
    vendor_query = f"""
        COPY (
            SELECT 
                CASE VendorID
                    WHEN 1 THEN 'Creative Mobile Technologies'
                    WHEN 2 THEN 'VeriFone Inc.'
                    ELSE 'Other'
                END AS technology_provider,
                COUNT(*) AS total_trips,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS market_share_percentage,
                ROUND(SUM(CASE WHEN store_and_fwd_flag = 'Y' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 4) AS offline_trip_rate_percentage
            FROM '{staging_path}'
            GROUP BY 1
            ORDER BY total_trips DESC
        ) TO '{output_dir}/mart_vendor_stability.parquet' (FORMAT PARQUET);
    """
    con.execute(vendor_query)

    # 5. Data Mart: Occupancy Elasticity by Group Size
    logging.info("Materializing: Occupancy Elasticity Data Mart...")
    occupancy_query = f"""
        COPY (
            SELECT 
                passenger_count AS group_size,
                COUNT(*) AS total_trips,
                ROUND(AVG(trip_distance), 2) AS avg_distance_miles,
                ROUND(AVG(total_amount), 2) AS avg_ticket,
                ROUND(AVG(tip_amount / NULLIF(fare_amount, 0)) * 100, 2) AS avg_tip_percentage
            FROM '{staging_path}'
            GROUP BY 1
            ORDER BY group_size ASC
        ) TO '{output_dir}/mart_occupancy_elasticity.parquet' (FORMAT PARQUET);
    """
    con.execute(occupancy_query)

    # 6. Data Mart: Revenue Breakdown Audit (Driver vs Government)
    logging.info("Materializing: Revenue Share Audit Data Mart...")
    revenue_audit_query = f"""
        COPY (
            SELECT 
                ROUND(AVG(fare_amount / NULLIF(total_amount, 0)) * 100, 2) AS driver_base_fare_share_pct,
                ROUND(AVG(tip_amount / NULLIF(total_amount, 0)) * 100, 2) AS driver_tip_share_pct,
                ROUND(AVG((mta_tax + improvement_surcharge + congestion_surcharge + COALESCE(cbd_congestion_fee, 0)) / NULLIF(total_amount, 0)) * 100, 2) AS government_taxes_share_pct,
                ROUND(AVG(tolls_amount / NULLIF(total_amount, 0)) * 100, 2) AS highway_tolls_share_pct
            FROM '{staging_path}'
        ) TO '{output_dir}/mart_revenue_audit.parquet' (FORMAT PARQUET);
    """
    con.execute(revenue_audit_query)

    # 7. Data Mart: Geographic Hotspots Matrix (Top 20 Routes)
    logging.info("Materializing: Geographic Hotspots Data Mart...")
    hotspots_query = f"""
        COPY (
            SELECT 
                PULocationID,
                DOLocationID,
                COUNT(*) AS total_trips,
                ROUND(SUM(total_amount), 2) AS total_revenue,
                ROUND(AVG(total_amount), 2) AS avg_ticket,
                ROUND(AVG(total_amount / NULLIF(trip_distance, 0)), 2) AS revenue_per_mile
            FROM '{staging_path}'
            GROUP BY PULocationID, DOLocationID
            ORDER BY total_trips DESC
            LIMIT 20
        ) TO '{output_dir}/mart_geo_hotspots.parquet' (FORMAT PARQUET);
    """
    con.execute(hotspots_query)

    logging.info(f"=== GOLD LAYER CONSOLIDATED SUCCESSFULLY AT: {output_dir} ===")