# Commercial MVP scope

CampaignForge AI should be sold and developed around one clear workflow:

```text
brief -> generate -> review -> export
```

That is the smallest product story that is easy to explain, demonstrate, and charge for.

## Core workflow

1. Brief
   Capture the product, audience, channels, goals, tone, constraints, and any compliance notes.
2. Generate
   Produce campaign strategy, audience suggestions, campaign angles, copy variants, CTAs, and image prompts.
3. Review
   Let an operator or marketer regenerate copy or prompts, review image concepts, and approve useful outputs.
4. Export
   Package the campaign brief, generated copy, prompts, image metadata, selected assets, and manifest into a ZIP bundle.

## Core for the commercial MVP

- structured campaign brief input
- mock-first generation for demos and safe local use
- optional live LLM/image provider mode when configured
- saved campaign history
- regeneration for copy and prompts
- image review state
- campaign export bundle
- local API and dashboard surfaces for demos and operator use

## Optional supporting features

- ETL and lead-scoring workflow
- CRM examples
- Google Sheets sync
- Airflow orchestration examples
- Kubernetes manifests

These are useful for credibility and custom work, but they should not lead the product story.

## Explicitly out of scope for the first commercial cut

- enterprise campaign platform positioning
- multi-brand collaboration suites
- media buying or ad network activation
- full DAM/CMS functionality
- automated publishing to social platforms
- complex approval hierarchies
- claiming hosted SaaS production readiness before managed database and object storage work is complete

## Decision rule

New work should improve the brief-to-export flow, make the demo easier to trust, or reduce delivery risk. If it does not do one of those things, it should be treated as optional until demand proves otherwise.
