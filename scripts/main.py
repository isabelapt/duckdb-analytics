import argparse
import duckdb
import logging
import sys
from pathlib import Path

# Add project root to sys.path to support execution from any directory
sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.clean import clean_raw_data
from scripts.transform import build_gold_data_marts

# Basic logging setup to trace pipeline execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Standardized path configurations for 2026-04
RAW_DATA_PATH = "data/raw/yellow_tripdata_2026-04.parquet"
STAGING_DIR = Path("data/staging")
PROCESSED_DIR = Path("data/processed")

STAGING_DATA_PATH = STAGING_DIR / "taxi_cleaned_2026_04.parquet"


def create_connection():
    """Creates a DuckDB connection (using in-memory mode for batch processing)."""
    return duckdb.connect(':memory:')


def main(period: str = "2026-04"):
    formatted_period = period.replace("-", "_")

    raw_data_path = f"data/raw/yellow_tripdata_{period}.parquet"
    staging_dir = Path("data/staging")
    processed_dir = Path("data/processed")
    staging_data_path = STAGING_DIR / f"taxi_cleaned_{formatted_period}.parquet"

    # Ensure output directory structure exists
    staging_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    con = create_connection()
    
    try:
        logging.info("Starting ETL Pipeline (Medallion Architecture)...")
        
        # Step 1: Cleansing (Generates Silver Layer)
        logging.info("Executing Silver Layer Data Cleansing...")
        clean_raw_data(con, RAW_DATA_PATH, str(STAGING_DATA_PATH))
        
        # Step 2: Analytical Transformations (Generates Gold Layer)
        logging.info("Executing Gold Layer Transformations...")
        build_gold_data_marts(con, str(STAGING_DATA_PATH), str(PROCESSED_DIR))
        
        logging.info("ETL Pipeline completed successfully! All Data Marts were generated.")

    except Exception as e:
        # Defensive rollback handling in case explicit transactions were active
        try:
            con.execute("ROLLBACK;")
        except duckdb.TransactionException:
            # Transaction already closed or auto-committed by DuckDB engine
            pass
            
        logging.error(f"Pipeline execution failed: {e}")
        raise e

    finally:
        con.close()
        logging.info("DuckDB connection closed gracefully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate DuckDB Medallion Pipeline")
    parser.add_argument(
        "--period",
        type=str,
        default="2026-04",
        help="Period to process in YYYY-MM format (default: 2026-04)"
    )
    args = parser.parse_args()

    main(period=args.period)