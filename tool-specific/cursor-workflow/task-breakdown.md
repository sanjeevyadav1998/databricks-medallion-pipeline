# Task Breakdown (as defined to Cursor)

Each task below is sent to Cursor as exactly one session, with
`project-context.md` + `.cursorrules` already loaded. Status is updated as
we go; the linked `ai-prompts/*.md` file holds the full prompt/response/
accept-reject log for that task.

| # | Task | Target file(s) | Depends on | Ai-prompts log | Status |
|---|---|---|---|---|---|
| 1 | Generate sample data with intentional quality issues | `src/data_generation/generate_sample_data.py` | — | `ai-prompts/data-generation.md` | Not started |
| 2 | Bronze ingestion — customers | `src/bronze/01_ingest_customers.py` | #1 | `ai-prompts/bronze-layer.md` | Not started |
| 3 | Bronze ingestion — orders | `src/bronze/02_ingest_orders.py` | #1 | `ai-prompts/bronze-layer.md` | Not started |
| 4 | Bronze ingestion — products | `src/bronze/03_ingest_products.py` | #1 | `ai-prompts/bronze-layer.md` | Not started |
| 5 | Bronze orchestrator | `src/bronze/ingest_all.py` | #2–4 | `ai-prompts/bronze-layer.md` | Not started |
| 6 | Silver quality checks (all 4) + merge | `src/silver/01–05_*.py`, `create_silver_tables.py` | #5 | `ai-prompts/silver-layer.md` | Not started |
| 7 | Gold aggregations (3) | `src/gold/*.sql`, `create_gold_tables.py` | #6 | `ai-prompts/gold-layer.md` | Not started |
| 8 | Dashboard queries + guide | `src/dashboard/*` | #7 | `ai-prompts/dashboard.md` | Not started |
| 9 | Test suite (data quality + integration) | TBD (e.g. `tests/`) | #6, #7 | `ai-prompts/debugging.md` | Not started |
| 10 | Database schema / setup script | `database/schema.sql`, `setup-notes.md` | #6, #7 | `ai-prompts/documentation.md` | Not started |

## Rule for every task
1. I (Claude) write the full prompt for the task, referencing `spec.md` and
   `project-context.md` sections rather than restating them.
2. You run it once in Cursor.
3. You test the output locally against that task's acceptance criteria.
4. You report back pass/fail + specifics.
5. If it passed: we log it as accepted in the `ai-prompts` file and move on.
6. If it failed: I write one targeted fix-prompt (not a full re-explain) —
   this still counts as the same Cursor session/task, just an iteration.
