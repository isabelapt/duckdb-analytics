import duckdb
import logging
from pathlib import Path

# Configuração básica de log para vermos o que o script está fazendo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações de caminhos padronizadas para 2026-04
RAW_DATA_PATH = "data/raw/yellow_tripdata_2026-04.parquet"
STAGING_DIR = Path("data/staging")
PROCESSED_DIR = Path("data/processed")

STAGING_DATA_PATH = STAGING_DIR / "taxi_cleaned_2026_04.parquet"

def create_connection():
    """Cria conexão com o DuckDB (usando em memória para o processamento batch)"""
    return duckdb.connect(':memory:')

def clean_raw_data(con, raw_path, staging_path):
    """Lê o raw, aplica regras de qualidade (filtros) e salva o dado intermediário confiável (Camada Prata)."""
    logging.info("Limpando dados brutos...")
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

def 