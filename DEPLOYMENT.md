# CampaignForge AI Deployment Guide

## Local Setup

Recommended path:

```bash
make setup
```

This creates a local Python environment and installs development dependencies.

If you prefer manual installation:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-airflow.txt
pip install -r requirements-streamlit.txt
```

## Fast Demo Path

For a quick under-5-minute demo:

```bash
make demo
```

This runs:

- local setup automatically if `.venv` is missing
- ETL
- model training
- model evaluation
- GenAI brief generation from the bundled sample brief
- optional concept image generation in mock mode for the saved sample campaign
- campaign export ZIP generation for the latest saved campaign

Demo outputs are collected under:

```text
demo_outputs/latest/
```

This bundle includes the latest model outputs plus the saved GenAI brief artifacts under `demo_outputs/latest/genai/`.
It also includes the latest exported campaign ZIP for download or handoff.

## Local App Runs

Run the API:

```bash
make api
```

Run the Streamlit dashboard:

```bash
make dashboard
```

## Docker

Build the Streamlit image:

```bash
docker build -t campaignforge-ai-dashboard .
```

Run the Streamlit container:

```bash
docker run -p 8501:8501 campaignforge-ai-dashboard
```

Build the FastAPI image:

```bash
docker build -t campaignforge-ai-api:latest -f Dockerfile.fastapi .
```

Run the FastAPI container:

```bash
docker run -p 8000:8000 campaignforge-ai-api:latest
```

## Airflow

Start the Airflow environment:

```bash
cd airflow
docker compose up --build
```

## Configuration Notes

- Local secrets should be provided through `.env`
- Streamlit secrets should be provided through `.streamlit/secrets.toml`
- Start from `.env.example` for environment variables where applicable
- CRM and Google Sheets integrations require valid credentials before live use
- GenAI runs in `mock` mode by default
- Set `CAMPAIGNFORGE_LLM_PROVIDER=openai` and `OPENAI_API_KEY` to enable live LLM generation
- Set `CAMPAIGNFORGE_IMAGE_PROVIDER=openai` and `OPENAI_API_KEY` to enable live image generation
- `OPENAI_BASE_URL` and `OPENAI_MODEL` are optional overrides for compatible providers
- `CAMPAIGNFORGE_STORAGE_ROOT` should point at persistent storage for hosted deployments
- `CAMPAIGNFORGE_RETENTION_DAYS` controls how long generated campaigns and assets are retained before cleanup

See `docs/DURABLE_STORAGE.md` for the storage boundary and retention design.
See `docs/OPERATIONS_BASELINE.md` for the current runtime and observability baseline.

## Intended Deployment Use

This repository includes deployment assets for:

- local demo and review
- Docker-based packaging
- Kubernetes discussion or extension
- Airflow-based orchestration examples

It is best treated as a starter codebase or downloadable asset, not as a production-managed deployment template without further project-specific hardening.
