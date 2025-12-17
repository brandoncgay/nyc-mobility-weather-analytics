# 🚦 NYC Mobility & Weather Analytics Platform

A modern data engineering project analyzing how weather affects NYC taxi and CitiBike usage, built using a fully free-tier modern data stack.

## 📘 Project Proposal

### Overview

This project builds an end-to-end modern data platform that analyzes how weather conditions influence transportation behavior across NYC taxis and CitiBike rides. Using publicly available datasets (NYC TLC Trip Records, CitiBike System Data, and OpenWeather API), the project integrates, cleans, models, and visualizes multimodal mobility patterns.

The platform delivers:

- A complete ELT pipeline (ingestion → orchestration → modeling → analytics)
- Dimensional models using dbt and medallion architecture
- A Hex dashboard with mobility + weather insights
- An AI-powered analytics assistant via FastAPI + embeddings

## 🧩 Problem Statement

Weather significantly impacts how people move around NYC, but mobility systems often respond reactively. Understanding these patterns requires integrating large, siloed datasets across transportation modalities and weather.

This project solves that by creating:

- A unified, analytics-ready dataset for taxi, bike, and weather data
- A modern data pipeline capable of repeatable ingestion and modeling
- A dashboard that clearly visualizes mobility changes under different conditions
- An AI interface that provides natural-language access to insights

This showcases practical, production-aligned data engineering skills while producing meaningful real-world mobility intelligence.

## 🎯 Project Objectives

- Build an ELT pipeline combining taxi, bike, and weather data
- Use dbt + medallion architecture to create clean, analytics-ready models
- Provide insights on how weather affects mobility behavior
- Produce rich visualizations in Hex
- Expose an AI assistant to answer natural-language mobility questions

## 📊 Data Sources

- **NYC TLC Trip Records (Taxi)** – Public monthly Parquet files
- **CitiBike System Data** – Public monthly CSV files
- **OpenWeather API** – Hourly historical weather data
- **DLTHub** – Metadata, data quality checks, lineage

## 🛠️ Technical Stack

- **Ingestion:** Airbyte, Python, DLTHub
- **Orchestration:** Dagster
- **Storage:** DuckDB (local), S3-compatible staging, Snowflake (free tier)
- **Transformations:** dbt (Bronze → Silver → Gold)
- **Analytics:** Hex dashboards
- **AI Layer:** FastAPI + Embeddings + RAG
- **Version Control:** Git + GitHub

## 📦 Deliverables

- Automated ingestion pipelines
- dbt transformation models and documentation
- Mobility + weather gold fact & dimension tables
- Interactive Hex dashboards
- AI Q&A service for mobility analytics
- Architecture diagrams & project documentation

## 🚀 MVP Roadmap

### MVP 1 — Raw Data Ingestion + Local Exploration

**Goal:** Validate data sources and feasibility.

**Includes:**
- Download taxi + bike data
- Pull sample weather data from API
- Store raw data in DuckDB / Parquet
- Perform early exploratory analysis

**Success:** All datasets ingested; basic joins & trends validated.

### MVP 2 — ELT Pipeline + Medallion Architecture in DuckDB

**Goal:** Create structured, modeled data.

**Includes:**
- dbt project setup
- Bronze → Silver → Gold modeling in DuckDB
- Dagster to orchestrate ELT

**Success:** End-to-end pipeline runs locally; gold tables ready.

### MVP 3 — Cloud Warehouse + Dashboard

**Goal:** Deploy analytics to the cloud.

**Includes:**
- Move dbt transformations to Snowflake
- Publish gold data models
- Build Hex dashboards for insights
- Visualize weather impact on taxis/bikes

**Success:** Dashboard demonstrates mobility–weather relationships.

### MVP 4 — AI Analytics Assistant

**Goal:** Enable conversational insights.

**Includes:**
- FastAPI service
- Embeddings for gold datasets
- RAG pipeline for answering analytics questions
- Example: "How does rainfall affect CitiBike demand?"

**Success:** API returns accurate insights for natural-language queries.

## 📅 High-Level Timeline

| MVP | Duration |
|-----|----------|
| MVP 1 | 1 week |
| MVP 2 | 1–2 weeks |
| MVP 3 | 2 weeks |
| MVP 4 | 1–2 weeks |

## 🔮 Optional Future Enhancements

- Demand forecasting using ML
- Real-time ingestion (Kafka simulation)
- CI/CD for dbt + Dagster
- Public web UI integrating dashboard + AI assistant
