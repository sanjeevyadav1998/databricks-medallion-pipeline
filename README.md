# Databricks Medallion Pipeline — E-Commerce Sales

End-to-end e-commerce sales analytics pipeline on Databricks: **Bronze →
Silver → Gold → Dashboard**, with intentional data-quality defects in the
seed data to exercise validation at the Silver layer.

## Architecture

```
  CSV seed data
       │
       ▼
  ┌─────────┐   Raw ingest, no cleaning — every row preserved
  │ BRONZE  │   bronze_customers / bronze_orders / bronze_products
  └────┬────┘
       ▼
  ┌─────────┐   Quality checks — rows flagged, never deleted
  │ SILVER  │   + quality_check_result column on all 3 tables
  └────┬────┘
       ▼
  ┌─────────┐   Aggregations from PASSED + Completed orders only
  │  GOLD   │   4 business-metric tables
  └────┬────┘
       ▼
  ┌───────────┐   Read-only SQL queries — 4 chart tiles, 2 filters
  │ DASHBOARD │
  └───────────┘
```

## Prerequisites

- **Databricks Free Edition** account with Unity Catalog (`workspace.default`
  catalog and schema already exist)
- **SQL Warehouse** (e.g. Serverless Starter Warehouse) for the Dashboard
- **Python 3.10+** locally, for running `generate_sample_data.py`

## Setup

For the full data-layer setup (seed generation, Volume upload, Bronze →
Silver → Gold pipeline), follow
[database/setup-notes.md](database/setup-notes.md).

Two additional steps not covered there:

1. **Build the Dashboard** — use
   [src/dashboard/dashboard_queries.sql](src/dashboard/dashboard_queries.sql)
   and the wiring guide in
   [src/dashboard/DASHBOARD_GUIDE.md](src/dashboard/DASHBOARD_GUIDE.md).
2. **Verify the pipeline** — run
   [tests/run_all_tests.py](tests/run_all_tests.py) in a Databricks notebook
   (note: the integration test tier re-runs Bronze/Silver/Gold and
   overwrites live tables).

## Repository structure

| Folder | Contents |
|---|---|
| `src/` | Pipeline code — `data_generation/`, `bronze/`, `silver/`, `gold/`, `dashboard/` |
| `data/` | Generated seed CSVs (customers, orders, products) |
| `database/` | Schema reference (`schema.sql`), seed mapping, setup instructions |
| `tests/` | Data-quality assertions and end-to-end integration tests |
| `ai-prompts/` | Per-activity prompt/response logs (one file per pipeline stage) |
| `tool-specific/` | Cursor workflow specs, task breakdown, project context |

## Key documentation

| Document | Purpose |
|---|---|
| [requirements-analysis.md](requirements-analysis.md) | Source requirements analysis |
| [design-notes.md](design-notes.md) | Architecture and design decisions |
| [data-model.md](data-model.md) | Conceptual entity model across layers |
| [data-quality-strategy.md](data-quality-strategy.md) | Silver validation framework and verified results |
| [debugging-notes.md](debugging-notes.md) | Debugging methodology and incident summary |
| [tool-workflow.md](tool-workflow.md) | AI-assisted development workflow |

## Status

All **10 core tasks** (sample data generation through database schema) are
**complete and verified**, per
[tool-specific/cursor-workflow/task-breakdown.md](tool-specific/cursor-workflow/task-breakdown.md).
