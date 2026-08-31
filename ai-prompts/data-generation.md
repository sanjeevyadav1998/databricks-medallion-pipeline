# AI Prompts — Data Generation

## Session 1 — Initial generation
**Tool / mode:** Cursor, Agent mode
**Prompt:** Full spec-driven prompt for `src/data_generation/generate_sample_data.py`
— exact schemas for customers/orders/products, exact injected quality-issue
counts (50/10/100/200/50/30/20), fixed random seed, printed verification
summary, standalone-runnable, `data/` output folder "relative to the script."

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
**Prompt:** Targeted fix — correct the output path to the repo-root `data/`
folder, delete the misplaced folder, re-run, re-print the summary.

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