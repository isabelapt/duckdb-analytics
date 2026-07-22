# DuckDB Analytics: NYC Yellow Taxi Hub Development Guide

This guide details the folder structure, analytical objectives, data cleansing rules, and implementation plan for the Data Quality & Analytics pipeline powered by DuckDB.

---

## 1. Repository Structure

The official repository directory tree follows the structure below:

```text
duckdb-analytics/
├── .github/
│   └── workflows/
│       └── data_pipeline_ci.yml
├── data/
│   ├── raw/                 # Bronze Layer (Git Ignored)
│   ├── staging/             # Silver Layer (Git Ignored)
│   └── processed/           # Gold Layer   (Git Ignored)
├── docs/
│   └── data_dictionary.md   # Official project data dictionary
├── notebooks/
│   └── 01_exploratory_analysis.ipynb
├── scripts/
│   ├── __init__.py
│   ├── clean.py             # Atomic data cleansing (Silver)
│   ├── transform.py         # Business logic & analytics KPIs (Gold)
│   └── main.py              # Central pipeline orchestrator
├── tests/
│   ├── __init__.py
│   └── test_quality_gates.py
├── .gitignore
├── Dockerfile
├── Makefile                 # Execution shortcuts (make run, make test)
├── pyproject.toml
└── README.md
```

---

## 2. Business Context & Market Pain Point

A major fleet operator and mobility consultancy in New York faces serious financial and operational inconsistencies in monthly reporting. Raw data collected directly from taximeters (provided by NYC TLC) arrives contaminated by hardware anomalies: GPS outages generate absurd telemetry recording thousands of miles on short local trips, network connectivity drops corrupt payment method logs, and canceled trips introduce zero or negative distance and fare entries into history. Making strategic driver allocation or pricing decisions on this raw data leads to financial losses and investor mistrust.

**Product Purpose & Objective:**
This product functions as a *Data Reliability Engineering* platform. The goal is to build an industrialized data pipeline that eliminates physical distortions via automated sanitization rules, centralizing clean data into an intermediate Staging layer (Silver) to reliably feed executive decision-making Data Marts (Gold Layer).

---

## 3. Modeling & Engineering Guidelines

* **Clean Architecture:** Strict separation between physical Parquet storage layer (Infrastructure) and SQL-structured analytical logic (Business Core).
* **SOLID (SRP):** Complete decoupling into independent modules: `clean.py` handles data integrity cleansing exclusively (Silver), `transform.py` focuses solely on mathematical consolidation of KPI Data Marts (Gold), and `main.py` acts as the single controller/orchestrator.
* **SOLID (DIP):** Dependency inversion for database connections: the in-memory DuckDB connection is centrally instantiated in the orchestrator and injected into functions via parameters.

---

## 4. Solution Requirements Scope

### Core Requirements (Must-Have / MVP Required)
* **DuckDB Ingestion:** Native vectorized processing consuming Parquet files directly from disk.
* **Cleansing Module:** Isolated functions for corporate null handling (`COALESCE` sentinel values), physical column casting (`TIMESTAMP`, `INTEGER`, `DOUBLE`), and strict domain rule enforcement to reject null, zero, or negative entries (`total_amount > 0` and `trip_distance > 0`).
* **Spatial and Temporal Outlier Filtering:** Rejection of records with trip distance over 150 miles and durations outside 1 to 180 minutes calculated via time-difference functions (`date_diff`).
* **Basic Data Mart Materialization:** Construction of aggregations serving four core business contexts (Daily Metrics, Hourly Speed/Traffic Flow, Airport Profitability, and Payment Method Behavior).

### Desirable Requirements (Portfolio Differentiators)
* **Diagnostic Lab:** Jupyter notebook featuring narrative storytelling and comparative audit using `SUMMARIZE` prior to production execution.
* **Interactive Visualization:** Dynamic line and bar charts using Plotly Express mapping trip volume and urban traffic patterns.
* **Automated Quality Testing:** `pytest` suites halting export routines if final Data Marts produce nulls on primary key columns.
* **Advanced Strategic Data Marts (Expanded Gold Layer):**
  1. *CBD Congestion Fee Impact:* Revenue and volume analysis within Manhattan Congestion Zone.
  2. *Vendor Connectivity Quality:* Tracking connection drops (`store_and_fwd_flag`) and market share by `VendorID`.
  3. *Occupancy Elasticity:* Distance and tip behavior grouped by party size (`passenger_count`).
  4. *Revenue Share Audit:* Breakdown of billed revenue between Driver (Base Fare + Tip) and Government Taxes / Tolls.
  5. *Geographic Hotspots Matrix:* Top performing routes grouped by `PULocationID` -> `DOLocationID` pairs.

---

## 5. KPI Matrix & Success Metrics

Transformations strictly follow mathematical formulas requested by business stakeholders:

### Operational & General Metrics:
1. **Daily Average Ticket ($)**:
   $$\text{avg\_ticket} = \frac{\sum(\text{total\_amount})}{\text{COUNT}(\text{trips})}$$
2. **Urban Traffic Average Speed (MPH)**:
   $$\text{avg\_speed\_mph} = \text{AVG}\left(\frac{\text{trip\_distance}}{\frac{\text{date\_diff('minute', pickup, dropoff)}}{60.0}}\right)$$
3. **Electronic Tip Penetration Rate (%)**:
   $$\text{avg\_tip\_percentage} = \text{AVG}\left(\frac{\text{tip\_amount}}{\text{NULLIF}(\text{fare\_amount}, 0)}\right) \times 100$$
4. **Revenue Per Useful Mile ($/Mile)**:
   $$\text{revenue\_per\_mile} = \text{AVG}\left(\frac{\text{total\_amount}}{\text{NULLIF}(\text{trip\_distance}, 0)}\right)$$

### Expanded Strategic Metrics:
5. **CBD Congestion Fee Share (%)**:
   $$\text{cbd\_impact\_\% } = \text{AVG}\left(\frac{\text{cbd\_congestion\_fee}}{\text{NULLIF}(\text{total\_amount}, 0)}\right) \times 100$$
6. **Offline Trip / Disconnection Rate (%)**:
   $$\text{offline\_rate} = \frac{\text{COUNT}(\text{CASE WHEN } store\_and\_fwd\_flag = 'Y' \text{ THEN 1 END})}{\text{COUNT}(*)} \times 100$$
7. **Driver Net Share (% Composition)**:
   $$\text{driver\_share\_\% } = \text{AVG}\left(\frac{\text{fare\_amount} + \text{tip\_amount}}{\text{total\_amount}}\right) \times 100$$
8. **Government Tax Share (% Composition)**:
   $$\text{tax\_share\_\% } = \text{AVG}\left(\frac{\text{mta\_tax} + \text{improvement\_surcharge} + \text{congestion\_surcharge} + \text{cbd\_fee}}{\text{total\_amount}}\right) \times 100$$
