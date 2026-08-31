# AI Prompts — Bronze Layer

## Session 1 — Ingestion scripts
**Tool / mode:** Cursor, Agent mode
**Prompt:** Fully-specced prompt for all 3 ingestion scripts + orchestrator,
referencing spec.md section 2. Included explicit DDL schema strings for
each source (no inferSchema, to avoid the ambiguity risk flagged before
generation), exact Unity Catalog Volume paths, exact write pattern
(`format("delta").mode("overwrite").saveAsTable(...)`), and a built-in
tripwire (NULL count on `signup_date`/`order_date`, which should always be
zero) to catch silent date-parsing failures without needing a rerun to
discover them.

**Result:** Accepted, no code-logic fixes needed. Cursor correctly:
- Used `importlib` to load the numeric-prefixed `01_`/`02_`/`03_` files as
  modules from `ingest_all.py` (correct Python workaround, not something
  the prompt specified — a good judgment call).
- Followed the exact DDL schema, write pattern, and "no extra columns"
  rule with no deviation.
- Exposed each script as an `ingest_<entity>(spark)` function with a
  docstring and a standalone `__main__` entry point, per `.cursorrules`.

## Debugging — running the scripts (not a code bug)
Two environment/tooling issues surfaced when actually running the
generated code, neither caused by Cursor's code:

1. **`%run` failed** — `%run` is a Databricks-notebook-specific magic
   command; it only works on notebooks, not plain `.py` files. Since the
   scripts were correctly written as standalone Python (per spec), `%run`
   was the wrong invocation method. **Root cause:** a gap in *my*
   environment knowledge, not a prompt or code issue. **Fix:** used
   `runpy.run_path(...)` with `init_globals={"spark": spark}` instead,
   which executes a plain script file while sharing the notebook's
   existing Spark session.

2. **Empty file content on first run** — after fixing the `%run` issue,
   `ingest_all.py` executed but produced zero output, with no error.
   Root cause: the Databricks Git folder had not fully synced the latest
   commit despite showing the correct branch/commit reference in the UI —
   an explicit manual "Pull" was required before the file content matched
   what was actually on GitHub. **Lesson:** don't trust a Git folder's
   apparent sync state after creation; explicitly pull and spot-check
   file content before running, especially right after linking a new
   Git folder.

## Validation
Ran `ingest_all.py` via `runpy` in a Databricks notebook (serverless
compute). Output:
- `workspace.default.bronze_customers`: 10,000 rows, signup_date NULL
  count = 0
- `workspace.default.bronze_orders`: 100,000 rows, order_date NULL
  count = 0
- `workspace.default.bronze_products`: 500 rows, N/A (no date column)

All row counts match the source CSVs exactly (10,000 / 100,000 / 500),
confirming Bronze ingested every row with no silent drops, and the
date-null tripwire confirms no schema/parsing mismatch.

## Status: ACCEPTED (1 code session, 2 environment/tooling fixes, 0 code fixes)