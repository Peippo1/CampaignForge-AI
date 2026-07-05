[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

# CampaignForge AI
Turn a campaign brief into a reviewed strategy, copy, and export pack from one modular Python codebase.

CampaignForge AI is a focused campaign planning and content-generation workflow for small marketing teams, freelancers, and agencies. The core commercial story is simple: brief, generate, review, export. The repository also includes supporting engineering assets for demos, custom delivery, and future hosted work, but it is not positioned as a broad campaign platform or a finished SaaS product.

## Product Workflow

CampaignForge AI is designed around one clear workflow:

1. Brief
   Capture a structured campaign brief with product, audience, channel, and tone inputs.
2. Generate
   Produce campaign strategy, audience suggestions, campaign angles, copy variants, CTAs, and image prompts.
3. Review
   Regenerate weak outputs, review image concepts, and keep only what is useful.
4. Export
   Download a ZIP bundle containing the brief, copy, prompts, image metadata, and selected assets.

## Core Outcome

The main value is turning a structured campaign brief into a reviewed campaign pack quickly. That pack can include:

- campaign summary and angle options
- audience suggestions
- headline, body copy, and CTA variants
- image prompts and optional concept images
- reviewed outputs in one export bundle

## Who It's For

- small marketing teams that need a faster planning workflow
- freelancers packaging campaign strategy and copy deliverables
- agencies that want a repeatable internal accelerator before building custom tooling
- buyers who want a credible starter product or delivery workflow they can adapt

## Core Features

- Source-first repository with generated outputs removed from version control
- GenAI brief copilot package with mock-first and API-key-gated live modes
- Durable campaign metadata storage with managed asset paths for saved images and export bundles
- Workflow controls for campaign history, regeneration, image review, and bundle export
- FastAPI service and Streamlit dashboard
- GitHub Actions workflows and automated tests
- Supporting sale/demo docs:
  - `PROJECT_OVERVIEW.md`
  - `PRODUCT.md`
  - `docs/COMMERCIAL_MVP.md`
  - `docs/PRODUCTISED_SERVICE_RUNBOOK.md`
  - `docs/HOSTED_MVP.md`
  - `docs/DEMO_SCRIPT.md`

## Optional Supporting Assets

These are useful for demos, custom delivery, or future expansion, but they are not the core product story:

- ETL and lead-scoring workflow
- CRM integration examples for Salesforce and HubSpot
- Google Sheets sync example
- Dockerfiles, Kubernetes manifests, and Airflow DAGs
- deployment, release, and listing support docs

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
- a `genai/` folder containing the latest saved campaign output bundle inputs
- saved image concept assets for the latest generated campaign
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
- Generate: review the generated campaign summary, angle options, copy, and prompts
- Review: approve or reject images, then regenerate where needed
- Export: download the campaign ZIP bundle for handoff

Useful companion docs:

- `PROJECT_OVERVIEW.md` for a buyer-facing summary
- `docs/DEMO_SCRIPT.md` for a guided walkthrough
- `docs/SCREENSHOT_CHECKLIST.md` for listing or portfolio prep
- `docs/SAMPLE_OUTPUTS.md` for reusable output snippets
- `docs/LISTING_COPY.md` for repo description and marketplace copy
- `docs/ASSET_PREP.md` for screenshots, GIFs, and listing asset planning
- `docs/COMMERCIAL_MVP.md` for the narrow product scope
- `docs/PRODUCTISED_SERVICE_RUNBOOK.md` for the done-for-you operator workflow
- `docs/HOSTED_MVP.md` for the smallest hosted product cut
- `docs/GENAI_ROADMAP.md` for the staged GenAI plan
- `docs/DURABLE_STORAGE.md` for campaign record and asset storage decisions
- `docs/OPERATIONS_BASELINE.md` for supported runtimes, dependency boundaries, and observability expectations
- `docs/HOSTED_AUTH.md` for the current workspace/auth model and hosted-vs-demo posture
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

- Gives a buyer one clear outcome instead of an open-ended platform pitch
- Supports a code asset, productised service, or later hosted MVP path
- Keeps the main workflow small enough to ship and validate demand
- Still includes enough engineering depth to support custom work and technical review

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
- Use `CAMPAIGNFORGE_AUTH_MODE=workspace_api_key` for hosted API protection and `disabled` for local demo/code-asset mode.
- Use `CAMPAIGNFORGE_DASHBOARD_AUTH_MODE=password` to protect the Streamlit dashboard in hosted mode.
- The current commercial MVP is the brief-to-export workflow, not the full repository surface area.
- The public GitHub repository description should match the CampaignForge AI positioning for consistency.
- Sales assets can be organized under `docs/assets/` without changing the source layout.
