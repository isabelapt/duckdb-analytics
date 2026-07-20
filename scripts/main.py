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

def transform_daily_metrics(staging_path):
    """Calcula métricas diárias: volume, ticket médio e gorjetas."""
    logging.info("Transformando dados: Métricas Diárias...")
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
    """Gera métricas de mobilidade agrupadas por hora, incluindo velocidade média."""
    logging.info("Transformando dados: Métricas de Mobilidade por Hora...")
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
    """Calcula métricas para corridas de aeroporto (JFK, Newark) vs comuns."""
    logging.info("Transformando dados: Métricas de Aeroporto...")
    query = f"""
        SELECT 
            CASE 
                WHEN RatecodeID = 2 THEN 'JFK'
                WHEN RatecodeID = 3 THEN 'Newark'
                ELSE 'Comum' 
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
    """Calcula a distribuição de meios de pagamento e taxa de gorjetas."""
    logging.info("Transformando dados: Métricas por Meio de Pagamento...")
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
    """Calcula velocidade média das viagens agrupada por hora do dia."""
    logging.info("Transformando dados: Métricas de Velocidade/Trânsito...")
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
    """Calcula métricas agregadas por dia da semana (volume e gorjeta média)."""
    logging.info("Transformando dados: Métricas por Dia da Semana...")
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
    """Executa a query e salva o resultado em um arquivo Parquet."""
    output_path = PROCESSED_DIR / output_filename
    logging.info(f"Exportando resultados para: {output_path}")
    
    # Executa a cópia direta para Parquet
    con.execute(f"COPY ({query}) TO '{output_path}' (FORMAT PARQUET)")

def main():
    # 1. Garante que a estrutura de pastas existe
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    con = create_connection()
    
    try:
        logging.info("Iniciando Pipeline ETL (Arquitetura Medalhão)...")
        
        # Etapa 1: Limpeza (Gera a Camada Prata)
        clean_raw_data(con, RAW_DATA_PATH, STAGING_DATA_PATH)
        
        # Etapa 2: Transformações Analíticas (Gera a Camada Ouro)
        load_to_parquet(con, transform_daily_metrics(STAGING_DATA_PATH), "mart_daily_metrics_2026_04.parquet")
        load_to_parquet(con, transform_hourly_mobility(STAGING_DATA_PATH), "mart_hourly_mobility_2026_04.parquet")
        load_to_parquet(con, transform_airport_metrics(STAGING_DATA_PATH), "mart_airport_revenue_2026_04.parquet")
        load_to_parquet(con, transform_payment_metrics(STAGING_DATA_PATH), "mart_payment_taxes_2026_04.parquet")
        load_to_parquet(con, transform_speed_metrics(STAGING_DATA_PATH), "mart_speed_metrics_2026_04.parquet")
        load_to_parquet(con, transform_weekday_metrics(STAGING_DATA_PATH), "mart_weekday_metrics_2026_04.parquet")
        
        logging.info("Pipeline ETL concluída com sucesso! Todos os Data Marts foram gerados.")
    except Exception as e:
        logging.error(f"Erro durante a execução do ETL: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
