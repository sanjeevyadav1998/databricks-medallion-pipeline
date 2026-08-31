# AI Prompts — Data Generation

## Session 1 — Initial generation
**Tool / mode:** Cursor, Agent mode
**Prompt (verbatim):**

Write the sample data generator for this project: `src/data_generation/generate_sample_data.py`.

Follow .cursorrules (layer boundaries, code style, naming) — this script has no layer restrictions itself (it runs before Bronze), but the code-style rules (docstrings, standalone runnable, logging, no hardcoded paths) still apply.

GOAL: Generate three CSVs with realistic e-commerce data and specific intentional data-quality issues, using Python (pandas + Faker, or pure Python/random if Faker isn't available — check and use whichever is installed, and note the choice in a comment).

OUTPUT FILES (write to a `data/` folder relative to the script, create it if missing):

1. customers.csv — 10,000 rows
   Columns: customer_id (INT, PK, 1..10000), customer_name (STRING), email (STRING), country (STRING), signup_date (DATE), customer_segment (STRING: one of Premium/Standard/Basic), lifetime_value (DECIMAL, positive, realistic e.g. 0-5000)

2. orders.csv — 100,000 rows
   Columns: order_id (INT, PK), customer_id (INT, FK), order_date (DATE), product_id (INT, FK), quantity (INT, 1-10), unit_price (DECIMAL), total_amount (DECIMAL, should equal quantity * unit_price for clean rows), order_status (STRING: Pending/Completed/Cancelled), payment_date (DATE, nullable — null for Pending orders, populated for Completed, may be null for Cancelled)

3. products.csv — 500 rows
   Columns: product_id (INT, PK, 1..500), product_name (STRING), category (STRING), price (DECIMAL), cost (DECIMAL, less than price), stock_quantity (INT), reorder_level (INT)

INTENTIONAL DATA QUALITY ISSUES — inject EXACTLY these counts, not approximately:

customers.csv:
- Exactly 50 rows with NULL email
- Exactly 10 rows with a duplicate customer_id (i.e. 10 rows reuse a customer_id that already exists elsewhere in the file)

orders.csv:
- Exactly 100 rows with NULL customer_id
- Exactly 200 rows with NULL product_id
- Exactly 50 rows where customer_id does NOT exist in the customers table (orphaned FK)
- Exactly 30 rows where product_id does NOT exist in the products table (orphaned FK)
- Exactly 20 rows with a duplicate order_id

These categories must not overlap within the same row unless unavoidable — keep the affected rows distinct where possible so each issue is independently countable and testable.

REQUIREMENTS:
- Use a fixed random seed so output is reproducible on every run.
- After generation, print a summary to stdout: total rows per file, and the actual count of each injected issue (so it's easy to verify against the spec above).
- Follow the naming/column conventions in tool-specific/cursor-workflow/project-context.md exactly — do not rename or reorder columns.
- Add a `# ASSUMPTION:` comment anywhere you have to make a judgment call not covered here (e.g. exact country list, exact category list, price ranges).
- Script must be runnable standalone: `python src/data_generation/generate_sample_data.py`

ALSO WRITE: `src/data_generation/DATA_GENERATION_NOTES.md` — briefly document how the data was generated and why each quality issue exists (one or two sentences per issue type, referencing that it's simulating a realistic upstream data problem).

Do not touch any other files.

**Result:** Accepted with one issue. All row counts and all 7 intentional
quality-issue counts matched the spec exactly on first generation:
- customers: 50 NULL email, 10 duplicate customer_id
- orders: 100 NULL customer_id, 200 NULL product_id, 50 orphan customer_id,
  30 orphan product_id, 20 duplicate order_id

**Issue found:** the phrase "relative to the script" in the prompt was
ambiguous and Cursor interpreted it literally — output landed in
`src/data_generation/data/` instead of the repo-root `data/` folder that
was already scaffolded in Stage 0 (with `.gitkeep`, matching the required
repo structure). This was a prompt-authoring gap, not a code logic bug —
the generation logic itself was correct on the first try.

## Session 2 — Path fix
**Tool / mode:** Cursor, Agent mode
**Prompt (verbatim):**

In src/data_generation/generate_sample_data.py, the output path is currently relative to the script's own location (src/data_generation/data/), which is wrong.

Fix it so CSVs are written to the repo-root data/ folder instead (the one that already exists with a .gitkeep file, two levels up from this script's location).

After fixing the path:
1. Delete the incorrect src/data_generation/data/ folder and the 3 CSVs inside it.
2. Re-run the script so the CSVs regenerate correctly in the repo-root data/ folder.
3. Print the same summary output as before so I can confirm the counts still match (they should be identical since the random seed is fixed).

Do not change anything else in the script — only the output path and the cleanup described above.

**Result:** Accepted. Output now correctly lands in the repo-root `data/`
folder. Summary counts identical to Session 1 (expected, since the random
seed is fixed) — confirms the fix touched only the path, not the
generation logic, as instructed.

## Root cause / lesson
"Relative to the script" is ambiguous phrasing whenever a script doesn't
live at the repo root — should specify the target path explicitly (e.g.
"two levels up from this script, at the repo root") in future prompts
involving nested `src/` scripts, rather than relying on "relative" being
interpreted the intended way.

## Status: ACCEPTED (2 sessions, 1 targeted fix)