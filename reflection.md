# Reflection

## What I Built

A complete Databricks medallion pipeline (Bronze → Silver → Gold →
Dashboard) for e-commerce sales data, backed by reproducible seed CSVs
with intentional quality defects. The deliverable set includes:

- **Bronze:** three ingestion scripts plus `ingest_all.py` orchestrator
- **Silver:** five quality-check modules plus `create_silver_tables.py`
- **Gold:** four aggregation SQL files plus `create_gold_tables.py`
- **Dashboard:** four query tiles, two interactive filters, and a wiring
  guide (`dashboard_queries.sql`, `DASHBOARD_GUIDE.md`)
- **Tests:** a 2-tier suite (`test_data_quality.py` +
  `test_pipeline_integration.py`, orchestrated by `run_all_tests.py`)
- **Documentation:** schema reference, seed mapping, setup notes, and
  top-level narrative docs

All **10 core tasks** in
[tool-specific/cursor-workflow/task-breakdown.md](tool-specific/cursor-workflow/task-breakdown.md)
are complete and verified.

## How I Used AI (Across the Lifecycle)

I used a **two-tool split** throughout the project:

| Role | Tool | Used for |
|---|---|---|
| Design, specs, prompt authoring, documentation | Claude (chat) | Everything that is *not* code generation inside the repo |
| Code generation | Cursor (Agent mode) | Writing and filling `src/`, `tests/`, and `database/` artifacts only |

This split existed specifically because of a **$70/month org-wide Cursor
usage cap**. Claude iteration is effectively free for planning; Cursor
iteration is not. Every Cursor session therefore needed to land close to
correct on the first try — which meant investing heavily in specs,
`.cursorrules`, and fully written prompts *before* opening Cursor.

Stage 0 scaffolding (`.cursorrules`, `spec.md`, `project-context.md`,
`task-breakdown.md`) and Part A (`tool-workflow.md`) were all done with
Claude before any pipeline code was generated. See
[ai-prompts/documentation.md](ai-prompts/documentation.md) for that
planning-layer log.

## What AI Helped With Most

The highest-value AI contribution was **catching non-obvious PySpark/SQL
bugs before running code**, not after discovering them in a failed
Databricks run:

- **Gold:** a LEFT JOIN silently becoming an INNER JOIN when
  `quality_check_result` or `order_status` filters were placed in a
  post-join `WHERE` clause — would have dropped zero-activity
  products/customers entirely.
- **Silver:** NULL foreign keys being double-counted as orphans if
  referential-integrity checks did not exclude NULLs; join row-explosion
  if parent keys were not deduplicated before joining.
- **Gold segmentation:** `PERCENTILE_CONT(0.8)` diluted by zero-revenue
  Inactive customers, skewing the High-Value cutoff.
- **Database schema docs:** guessing Gold's computed `DECIMAL` precision
  as executable DDL could have caused a Delta schema-mismatch on the next
  `.saveAsTable(mode="overwrite")` write — caught and changed to
  commented-out reference text instead.

AI also helped write **complete, unambiguous Cursor prompts** — exact DDL
strings, exact injected-issue counts (50/10/100/200/50/30/20), exact file
boundaries ("do not touch any other files") — so most layers succeeded in
**one Cursor generation with zero logic fix-iterations**. Silver, Gold,
Dashboard, tests, and database schema all passed on first generation.

## What AI Got Wrong

Three concrete examples where AI output or AI-directed planning needed
correction:

1. **Silver prompt draft (never sent to Cursor):** the first draft
   targeted a local/pandas execution model (CSV paths, PySpark/pandas
   fallback) that did not match the Databricks Unity Catalog pattern
   already established in Bronze. Caught and rewritten before Cursor ever
   saw it — see [ai-prompts/silver-layer.md](ai-prompts/silver-layer.md).

2. **Sample data path (one fix-iteration):** the first generator run
   wrote CSVs to `src/data_generation/data/` because the prompt said
   output should be "relative to the script" — ambiguous phrasing, not
   wrong generation logic. Fixed in a targeted second session — see
   [ai-prompts/data-generation.md](ai-prompts/data-generation.md).

3. **Dashboard hardening (unnecessary in practice):** the prompt
   documented workarounds for a missing `'All'` dropdown value (`UNION
   ALL` alternative) and `:category`/`:date_range` SQL parameter
   placeholders. On the live Databricks Lakeview UI, the native Filters
   panel solved both problems without those workarounds. Being proactive
   about a risk that did not materialize is not the same as being wrong
   about underlying SQL logic, but it is a real case of solving for a
   problem the platform had already solved — see
   [ai-prompts/dashboard.md](ai-prompts/dashboard.md).

## How I Validated AI Output

I never treated **"it ran without error"** as sufficient. Every layer was
checked against **known ground truth** from the sample data's fixed random
seed:

- Injected-issue counts are exact, reproducible targets (50 NULL emails,
  10 duplicate `customer_id`, etc.) — not estimates.
- Row counts are exact (10,000 / 100,000 / 500 through Bronze and
  Silver; 9,940 PASSED customers in Silver; 500 Gold products).

Where possible, I **cross-checked derived numbers mathematically**:

- Gold customer segmentation: **1,987 High-Value** out of **9,935**
  customers with `total_orders > 0` → 1987/9935 = **0.2000** exactly,
  confirming the 80th-percentile logic worked as designed, not
  approximately.
- `SUM(customer_count)` across all 4 `gold_customer_segmentation` rows =
  **9,940**, matching Silver's PASSED customer count — structural proof
  the LEFT JOIN did not drop or duplicate customers.

After each Cursor session, I **read the actual generated code** directly
rather than trusting a chat summary of what was produced. Formalized
assertions live in [tests/test_data_quality.py](tests/test_data_quality.py).

## What I Would Improve Next

1. **Probe the Dashboard platform first.** Test how Databricks SQL
   Dashboard's native Filters mechanism actually behaves before writing
   SQL-parameter-based filter logic into a prompt. That would have
   avoided documenting `:category`/`:date_range` placeholders and `UNION
   ALL` dropdown workarounds for problems the UI solves natively.

2. **One fresh-clone acceptance pass.** Do a single literal
   follow-the-README-from-zero run on a clean environment as an explicit
   final acceptance step, rather than relying on each step having been
   individually verified in isolation across many separate sessions.

## Reusable Workflow

The core pattern from this project applies to any AI-assisted engineering
work under a per-generation cost constraint:

1. **Separate the thinking tool from the execution tool** — free iteration
   on design; paid iteration only for code.
2. **Write standing rules and specs before any code generation**
   (`.cursorrules`, `spec.md`, `project-context.md`) so every execution
   prompt can reference a section instead of re-explaining context.
3. **Review every prompt for domain-specific failure modes BEFORE
   sending it** — not after a wrong result forces a fix iteration.
4. **Validate against known ground truth** — fixed seeds, exact counts,
   mathematical cross-checks — rather than "did it run."

The specific tools (Claude + Cursor) matter less than this workflow shape.
