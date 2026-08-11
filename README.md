# ⚡ GridPulse Intelligence

### Modern Energy Data Engineering Platform

GridPulse Intelligence is an end-to-end data engineering project built around U.S. electricity, renewable generation, weather, and EV charging infrastructure data.

The goal is to build the project the same way I would approach a modern data platform: start with reliable ingestion, move into streaming and distributed processing, organize data through lakehouse layers, add quality and observability, and expose trusted datasets for analytics, forecasting, APIs, and interactive visualization.

The project is being developed locally first and will later be deployed to Microsoft Azure.

---

## Project Status

**Current phase: Platform Foundation**

Completed:

- [x] Apple Silicon development environment
- [x] Python 3.12 with `uv`
- [x] Reproducible project environment
- [x] Production-style repository structure
- [x] Ruff linting and formatting
- [x] mypy static type checking
- [x] pytest unit testing
- [x] Docker development environment
- [x] Terraform CLI
- [x] Azure CLI

Coming next:

- [ ] EIA electricity ingestion
- [ ] NOAA weather ingestion
- [ ] EV infrastructure ingestion
- [ ] Apache Kafka event streaming
- [ ] Spark Structured Streaming
- [ ] Bronze / Silver / Gold lakehouse
- [ ] Apache Iceberg tables
- [ ] dbt transformations
- [ ] Dagster orchestration
- [ ] Data contracts
- [ ] Data quality framework
- [ ] OpenLineage integration
- [ ] Prometheus metrics
- [ ] Grafana observability
- [ ] MLflow experiment tracking
- [ ] Energy demand forecasting
- [ ] FastAPI serving layer
- [ ] Next.js command center
- [ ] Three.js platform visualization
- [ ] Terraform Azure deployment
- [ ] GitHub Actions CI/CD

---

## Why GridPulse?

Electricity systems are becoming more data-intensive.

Power demand, renewable generation, storage, EV infrastructure, weather, and large computing workloads increasingly interact with the same grid.

This makes energy a useful domain for demonstrating modern data engineering problems such as:

- continuously changing source data
- event-driven ingestion
- late-arriving records
- schema evolution
- distributed processing
- time-series analytics
- data freshness
- data quality
- pipeline observability
- lineage
- infrastructure automation
- forecasting

Instead of building another static analytics dashboard, GridPulse is being designed as a small but complete **data platform**.

---

## Architecture

```text
                         GRIDPULSE INTELLIGENCE

                     ┌─────────────────────┐
                     │    DATA SOURCES     │
                     │                     │
                     │ EIA · NOAA · AFDC   │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │      INGESTION      │
                     │                     │
                     │ Python · REST APIs  │
                     │ Kafka · Event Hubs  │
                     └──────────┬──────────┘
                                │
                                ▼
                  ┌───────────────────────────┐
                  │    STREAM PROCESSING      │
                  │                           │
                  │ Apache Spark              │
                  │ Structured Streaming      │
                  └─────────────┬─────────────┘
                                │
                                ▼
                  ┌───────────────────────────┐
                  │        LAKEHOUSE          │
                  │                           │
                  │        BRONZE             │
                  │           ↓               │
                  │        SILVER             │
                  │           ↓               │
                  │         GOLD              │
                  │                           │
                  │ Iceberg · Delta · ADLS    │
                  └─────────────┬─────────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
                   ▼                         ▼
          ┌─────────────────┐       ┌─────────────────┐
          │    ANALYTICS    │       │   FORECASTING   │
          │                 │       │                 │
          │ dbt             │       │ MLflow          │
          │ SQL             │       │ XGBoost         │
          │ DuckDB          │       │ Features        │
          └────────┬────────┘       └────────┬────────┘
                   │                         │
                   └────────────┬────────────┘
                                │
                                ▼
                      ┌───────────────────┐
                      │   SERVING LAYER   │
                      │                   │
                      │ FastAPI           │
                      │ Next.js           │
                      │ Three.js          │
                      └───────────────────┘
