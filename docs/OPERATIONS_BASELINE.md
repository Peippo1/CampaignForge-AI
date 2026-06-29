# Operations baseline

This document defines the minimum supported runtime and observability baseline for CampaignForge AI in its current starter-product state.

## Supported Python runtimes

- Python 3.11
- Python 3.12

These are the only versions currently treated as supported for core app and test paths.

## Dependency boundary

Required dependencies for core app paths:

- FastAPI
- Pydantic
- Pandas
- Streamlit

Optional dependencies:

- `pymysql` for CRM-backed dashboard data access
- `gspread` for Google Sheets sync
- OpenTelemetry exporter packages for tracing

Optional integrations should not break unrelated app paths when they are not configured.

## Health and observability baseline

- `GET /health` must return `200`
- FastAPI sets no-store and basic hardening headers
- tracing stays opt-in through `OTEL_ENABLED`
- deployment docs must state the env vars needed for tracing and storage

## Failure-mode expectations

- LLM generation falls back to mock mode when live provider calls fail
- image generation falls back to mock mode when live provider calls fail
- missing optional integrations should degrade specific features, not the whole application
- generated campaign storage should use the managed storage root rather than assuming repo-local JSON files

## Validation

Use:

```bash
python3 -m utils.runtime_baseline
python3 -m pytest tests/test_runtime_baseline.py
```
