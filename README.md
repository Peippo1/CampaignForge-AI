[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# CampaignForge AI
Turn campaign briefs and customer data into reusable strategy, copy, API responses, and dashboard-ready outputs from one modular codebase.

CampaignForge AI is a production-style Python workflow for buyers who want a credible campaign intelligence demo or starter product. It packages ETL, lead-scoring style modeling, a GenAI brief copilot, API delivery, dashboard presentation, and deployment assets into one reviewable repository. It is not positioned as a hosted SaaS product or a finished image-generation platform.

## Product Workflow

CampaignForge AI is designed around a simple workflow:

1. Brief
   Capture a structured campaign brief with product, audience, channel, and tone inputs.
2. Strategy
   Generate a campaign summary, personas, channel recommendations, and campaign angles.
3. Copy
   Produce headline variants, body copy variants, CTA options, and prompt-ready messaging.
4. Image Concepts
   Turn saved prompts into mock-first concept images or live-provider outputs when configured.
5. Review
   Revisit saved campaigns, regenerate copy or prompts, and approve or reject generated images.
6. Export
   Download a ZIP bundle containing the brief, copy, prompts, manifests, and saved images.

## What It Does

- Processes raw campaign and customer data into cleaned, analysis-ready datasets
- Trains and evaluates a scikit-learn classification model for lead-scoring and campaign analytics style use cases
- Generates campaign summaries, audience suggestions, copy variants, CTA variants, and image prompts from a structured brief
- Generates optional concept images from saved campaign prompts with mock mode by default and live provider mode when configured
- Tracks approval state for generated images, supports regeneration, and exports full campaign bundles as ZIP files
- Exposes lightweight customer endpoints through FastAPI
- Presents customer data, GenAI brief outputs, and CRM handoff workflows through Streamlit
- Includes Airflow, Docker, and Kubernetes assets to support operational and deployment discussions

## Who It's For

- Developers packaging AI-adjacent marketing workflow products
- Agencies or freelancers who need a credible starter codebase for campaign analytics tooling
- Teams wanting a presentable example of ETL, modeling, API delivery, and dashboard UX in one repository
- Buyers who value engineering breadth, deployment readiness, and documented demo workflows

## Features

- Source-first repository with generated outputs removed from version control
- ETL scripts, model training, and model evaluation workflow
- GenAI brief copilot package with mock-first and API-key-gated live modes
- Durable campaign metadata storage with managed asset paths for saved images and export bundles
- Workflow controls for campaign history, regeneration, image review, and bundle export
- FastAPI service and Streamlit dashboard
- CRM integration examples for Salesforce and HubSpot
- Google Sheets sync example
- GitHub Actions workflows and automated tests
- Dockerfiles, Kubernetes manifests, and Airflow DAGs
- Supporting sale/demo docs:
  - `PROJECT_OVERVIEW.md`
  - `docs/DEMO_SCRIPT.md`
  - `docs/SCREENSHOT_CHECKLIST.md`
  - `docs/SAMPLE_OUTPUTS.md`

## What’s Included

- Full Python source code for ETL, model training, evaluation, API delivery, and dashboard presentation
- GenAI brief-to-copy workflow with campaign records stored in SQLite-backed metadata
- Structured image generation folders under `CAMPAIGNFORGE_STORAGE_ROOT/assets/images/<campaign_id>/`
- Exported campaign ZIP bundles under `CAMPAIGNFORGE_STORAGE_ROOT/assets/exports/`
- Demo data, predictable demo outputs, and Makefile shortcuts
- FastAPI and Streamlit interfaces for technical and non-technical walkthroughs
- Docker, Kubernetes, and Airflow assets for packaging and operations discussions
- Buyer-facing overview, deployment, release, and listing support docs

## Quickstart

The fastest local setup path is:

```bash
make demo
```

What those commands do:

- `make demo`: bootstraps the local environment if needed, then runs ETL, model training, evaluation, and the GenAI brief copilot end-to-end using the included sample inputs
- when dependencies are installed, `make demo` also generates saved concept images in mock mode for the latest campaign brief
- `make demo` also writes an exportable ZIP bundle for the latest generated campaign

The bundled demo inputs are included under `data/raw/` and `data/demo/`.

After `make demo`, the most useful outputs are gathered in:

```text
demo_outputs/latest/
```

That folder contains:

- the latest trained model artifact
- the training metrics JSON
- the evaluation metrics JSON
- a `genai/` folder containing the latest saved campaign brief manifest and copy output
- saved image concept assets and metadata for the latest generated campaign
- an exported campaign ZIP ready for download or handoff
- a small readme for quick inspection

If you want to continue the full interactive walkthrough after the demo run:

```bash
make api
make dashboard
```

If you prefer to prepare the environment explicitly first, you can still run:

```bash
make setup
make demo
```

If you prefer manual setup:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-airflow.txt
pip install -r requirements-streamlit.txt
```

## Demo

Recommended buyer demo flow:

1. Run `make demo`
2. Open `demo_outputs/latest/` and review the generated outputs
3. Review the generated campaign brief outputs under `demo_outputs/latest/genai/`
4. Review the saved concept images under `demo_outputs/latest/genai/images/`
5. Download or inspect the exported campaign ZIP in `demo_outputs/latest/genai/`
6. Launch the API with `make api`
7. Launch the dashboard with `make dashboard`

Recommended public sale narrative:

- Brief: enter a campaign concept and target market
- Strategy: review the generated campaign summary and angle options
- Copy: inspect headlines, body copy, CTAs, and saved prompts
- Image Concepts: generate concept visuals from a selected angle
- Review: approve or reject images, then regenerate where needed
- Export: download the campaign ZIP bundle for handoff

Useful companion docs:

- `PROJECT_OVERVIEW.md` for a buyer-facing summary
- `docs/DEMO_SCRIPT.md` for a guided walkthrough
- `docs/SCREENSHOT_CHECKLIST.md` for listing or portfolio prep
- `docs/SAMPLE_OUTPUTS.md` for reusable output snippets
- `docs/LISTING_COPY.md` for repo description and marketplace copy
- `docs/ASSET_PREP.md` for screenshots, GIFs, and listing asset planning
- `docs/GENAI_ROADMAP.md` for the staged GenAI plan
- `docs/DURABLE_STORAGE.md` for campaign record and asset storage decisions
- `docs/OPERATIONS_BASELINE.md` for supported runtimes, dependency boundaries, and observability expectations
- `QA_CHECKLIST.md` for launch verification
- `RELEASE_NOTES.md` for the v1 sale-ready summary

## Project Structure

```text
project-root/
├── airflow/                  # Airflow DAGs, scripts, and container setup
├── data/raw/                 # Sample raw dataset and supporting assets
├── docs/                     # Demo, screenshot, and sales-support material
├── etl/                      # ETL pipeline scripts
├── genai/                    # Brief copilot, prompt building, and output storage
├── k8s/                      # Kubernetes deployment manifests
├── models/                   # Training, evaluation, and artifact-related code
├── pipelines/                # Pipeline helper modules
├── scoring/                  # FastAPI application
├── tests/                    # Automated tests
├── utils/                    # CRM and Google Sheets helpers
├── streamlit_app.py          # Canonical Streamlit dashboard entrypoint
├── Makefile                  # Common developer/demo commands
├── setup.sh                  # Local setup helper
└── README.md
```

## Tech Stack

| Area | Tools |
| --- | --- |
| Language | Python 3.11 |
| Data processing | Pandas |
| ML | scikit-learn |
| GenAI | Mock-first brief copilot with optional OpenAI-compatible mode |
| API | FastAPI |
| Dashboard | Streamlit |
| Scheduling | Apache Airflow |
| Packaging | Docker |
| Deployment assets | Kubernetes manifests |
| Observability | OpenTelemetry hooks for FastAPI |
| Integrations | Salesforce, HubSpot, Google Sheets |

## Why This Is Useful

- Shows an end-to-end campaign intelligence workflow in one reviewable repository
- Gives buyers a realistic starting point rather than isolated notebooks or toy scripts
- Demonstrates breadth across ETL, model training, API delivery, dashboard UX, and orchestration
- Provides a stronger portfolio or resale asset than a single-purpose machine learning script
- Includes deployment and CI assets that help the project feel operationally credible

## Comparison

| Capability | Included |
| --- | --- |
| Source code | Yes |
| Local run path | Yes |
| One-command demo | Yes |
| Campaign export ZIP | Yes |
| Docker support | Yes |
| Dashboard | Yes |
| API | Yes |
| Tests | Yes |
| Airflow orchestration | Yes |
| Kubernetes manifests | Yes |

## Notes

- The repository currently targets Python `3.11.11` via `.python-version`.
- Generated outputs such as model artifacts, processed data, and local runtime files are intentionally gitignored.
- Demo outputs are collected under `demo_outputs/latest/` for predictable review.
- Generated GenAI artifacts use a SQLite-backed metadata store plus managed asset storage under `CAMPAIGNFORGE_STORAGE_ROOT` and are copied into the demo output bundle.
- Streamlit now includes saved campaign history plus workflow controls for regeneration, image review, and export.
- `streamlit_app.py` is the single supported dashboard entrypoint for demos and local runs.
- Local secrets should be supplied through `.env` and `.streamlit/secrets.toml`; start from `.env.example` where applicable.
- Set `CAMPAIGNFORGE_LLM_PROVIDER=openai` and `OPENAI_API_KEY` only when you want live LLM output; the local default is mock mode.
- Set `CAMPAIGNFORGE_IMAGE_PROVIDER=openai` together with `OPENAI_API_KEY` only when you want live image output; the local default is mock SVG concepts.
- Set `CAMPAIGNFORGE_STORAGE_ROOT` to a persistent volume or equivalent durable mount for hosted deployments.
- Set `CAMPAIGNFORGE_RETENTION_DAYS` to control campaign asset cleanup windows.
- Supported Python runtimes are currently `3.11` and `3.12`.
- Run `make compat-check` to validate the baseline runtime assumptions.
- The public GitHub repository description should match the CampaignForge AI positioning for consistency.
- Sales assets can be organized under `docs/assets/` without changing the source layout.
