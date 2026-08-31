# Final AI Usage Summary

Compact at-a-glance reference for AI usage across the project. For
narrative reflection see [reflection.md](reflection.md). For Part A
workflow answers see [tool-workflow.md](tool-workflow.md).

## Two-tool workflow

**Claude** handled all design, spec-writing, prompt authoring, and
documentation; **Cursor (Agent mode)** was reserved strictly for code
generation inside the repo. This split was motivated by a **$70/month
org-wide Cursor usage cap** — Claude iteration is free, Cursor iteration
is not, so every Cursor session needed to land close to correct on the
first try.

> **# ASSUMPTION:** Exact dollar cost spent on Cursor is not tracked in
> this repository. Fill in the actual amount manually from the Cursor
> billing dashboard if required for submission — do not use a fabricated
> figure from this document.

## Prompt history

All **7** `ai-prompts/*.md` activity logs contain **verbatim prompt text**
(not paraphrased summaries), per the exercise brief's "Full prompt history
(CRITICAL)" requirement. Planning-layer work done with Claude (Stage 0
scaffolding, Part A) is logged separately at the top of
[ai-prompts/documentation.md](ai-prompts/documentation.md).

## Cursor sessions (10 tasks)

Fix-iteration counts pulled from each `ai-prompts/*.md` Status line.

| # | Task | Target file(s) | Ai-prompts log | Fix-iterations |
|---|---|---|---|---|
| 1 | Generate sample data with intentional quality issues | `src/data_generation/generate_sample_data.py`, `DATA_GENERATION_NOTES.md` | [ai-prompts/data-generation.md](ai-prompts/data-generation.md) | 1 (output path — prompt phrasing, not logic) |
| 2 | Bronze ingestion — customers | `src/bronze/01_ingest_customers.py` | [ai-prompts/bronze-layer.md](ai-prompts/bronze-layer.md) | 0 code fixes (batched with #3–5 in 1 session) |
| 3 | Bronze ingestion — orders | `src/bronze/02_ingest_orders.py` | [ai-prompts/bronze-layer.md](ai-prompts/bronze-layer.md) | 0 code fixes (batched with #2, #4–5) |
| 4 | Bronze ingestion — products | `src/bronze/03_ingest_products.py` | [ai-prompts/bronze-layer.md](ai-prompts/bronze-layer.md) | 0 code fixes (batched with #2–3, #5) |
| 5 | Bronze orchestrator | `src/bronze/ingest_all.py` | [ai-prompts/bronze-layer.md](ai-prompts/bronze-layer.md) | 0 code fixes (batched with #2–4) |
| 6 | Silver quality checks + merge | `src/silver/01–05_*.py`, `create_silver_tables.py` | [ai-prompts/silver-layer.md](ai-prompts/silver-layer.md) | 0 |
| 7 | Gold aggregations | `src/gold/*.sql`, `create_gold_tables.py` | [ai-prompts/gold-layer.md](ai-prompts/gold-layer.md) | 0 logic fixes (1 cosmetic indentation tweak) |
| 8 | Dashboard queries + guide | `src/dashboard/*` | [ai-prompts/dashboard.md](ai-prompts/dashboard.md) | 0 logic fixes |
| 9 | Test suite (data quality + integration) | `tests/test_data_quality.py`, `tests/test_pipeline_integration.py`, `tests/run_all_tests.py` | [ai-prompts/debugging.md](ai-prompts/debugging.md) | 0 |
| 10 | Database schema / setup docs | `database/schema.sql`, `database/seed-data-notes.md`, `database/setup-notes.md` | [ai-prompts/documentation.md](ai-prompts/documentation.md) | 0 |

## Totals

| Metric | Value |
|---|---|
| Cursor code sessions (distinct generations) | ~8 (Task 1 × 2; Bronze batched × 1; Tasks 6–10 × 1 each) |
| Logic fix-iterations across all tasks | **1** (sample-data output path only) |
| Layers passing on first generation with 0 logic fixes | Silver, Gold, Dashboard, Tests, Database schema |
| Pre-Cursor prompt rewrites (Claude only, never sent to Cursor) | 1 (Silver local/pandas draft) |

## Key verified numbers (ground truth)

| Check | Value |
|---|---|
| Silver customers passed | 9,940 / 10,000 (99.40%) |
| Silver orders passed | 99,600 / 100,000 (99.60%) |
| Silver products passed | 500 / 500 (100%) |
| Injected-issue counts caught | 50 / 10 / 100 / 200 / 50 / 30 / 20 (all exact) |
| High-Value segmentation | 1,987 / 9,935 active customers = 20.00% (80th percentile) |
| Total injected problematic rows | 460 (60 customers + 400 orders) |
