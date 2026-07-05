# CampaignForge AI Overview

## Summary

`CampaignForge AI` is a focused campaign planning and content-generation workflow for small marketing teams, freelancers, and agencies. The clearest product story is simple: take a brief, generate campaign strategy and copy, review the outputs, and export a handoff bundle.

## What A Buyer Gets

- A Python workflow that turns campaign briefs into structured strategy, copy, prompts, and export bundles
- Workflow controls for regeneration, image approvals, campaign history, and exports
- A FastAPI service and Streamlit dashboard for demos and operator use
- Enough engineering support material to back up delivery, technical review, and later productisation

## Core Capabilities

- structured campaign brief input
- generated strategy, angles, copy, CTAs, and prompts
- optional image concept generation with mock-first local mode
- review and regeneration workflow
- exportable campaign bundle

## Commercial Positioning

This repository is best positioned as:

- a starter product for campaign planning and content generation
- a productised-service accelerator for agencies and freelancers
- a technically credible code asset that can later be narrowed into a hosted product

It is not positioned as a finished SaaS platform. Its value is in delivering a clear workflow while staying honest about current hosted limitations.

## Recommended Demo Story

1. Run the one-command demo with `make demo`.
2. Review `demo_outputs/latest/` to show the saved campaign pack outputs.
3. Explain the brief -> generate -> review -> export workflow.
4. Launch the dashboard with `make dashboard` and show campaign history, regeneration, and export.
5. Launch the API with `make api` and show the protected campaign endpoints.
6. Only then reference broader deployment assets as supporting credibility, not the main pitch.

## Suggested Buyer Talking Points

- the product solves a narrow, easy-to-understand problem
- the workflow is small enough to deliver manually or package as software
- security-conscious defaults and CI coverage reduce delivery risk
- the same code can support a code asset, service workflow, or later hosted cut

## Contents To Highlight In A Listing

- `README.md` for quick-start and architecture
- `docs/COMMERCIAL_MVP.md` for product scope
- `docs/PRODUCTISED_SERVICE_RUNBOOK.md` for service delivery
- `docs/HOSTED_MVP.md` for the hosted cut
- `Makefile` for demo commands
- `scoring/fastapi_app.py` for API delivery
- `streamlit_app.py` for dashboard UX
- Dockerfiles and deployment docs for packaging discussions
