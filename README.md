# NYC Yellow Taxi Analytics Hub (DuckDB)

An end-to-end Data Reliability Engineering (DRE) & Analytics pipeline implementing Medallion Architecture (Bronze -> Silver -> Gold) using DuckDB, Python, and Parquet.

## 📌 Project Overview
This project processes NYC Yellow Taxi trip data from the Taxi & Limousine Commission (TLC) using DuckDB for vectorized, memory-efficient data processing. It sanitizes hardware & GPS telemetry anomalies (Silver Layer) and builds high-performance analytical Data Marts (Gold Layer) for executive reporting.

## 🛠️ Architecture & Tech Stack
- **Engine**: DuckDB (Vectorized SQL execution engine)
- **Format**: Apache Parquet
- **Language & Package Manager**: Python 3.12, `uv`
- **Visualization**: Plotly Express (Interactive charts)
- **Quality Gates**: pytest

## 🚀 Getting Started

### 1. Installation
Clone the repository and install dependencies using `uv`:
```bash
uv sync
```

### 2. Running the Pipeline
Execute the main orchestrator script:
```bash
uv run python scripts/main.py
```

### 3. Running Exploratory Analysis
Open the Jupyter notebook:
```bash
uv run jupyter lab notebooks/01_exploratory_analysis.ipynb
```

## 📊 Data Marts (Gold Layer)
The pipeline materializes the following analytics marts in `data/processed/`:
- `mart_daily_metrics.parquet`: Revenue, trip count, and ticket averages by date.
- `mart_hourly_traffic.parquet`: Traffic speed (MPH) and trip duration per pickup hour.
- `mart_cbd_impact.parquet`: Congestion fee breakdown & Manhattan CBD zone impact.
- `mart_vendor_stability.parquet`: Telemetry signal loss and market share by technology vendor.
- `mart_occupancy_elasticity.parquet`: Metrics grouped by passenger party size.
- `mart_revenue_audit.parquet`: Revenue share split between drivers, tolls, and government taxes.
- `mart_geo_hotspots.parquet`: Top 20 most popular and profitable origin-destination pairs.
