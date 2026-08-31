# Debugging Notes

Project-level synthesis of the debugging approach and key incidents. Each
layer's full prompt/response log lives in its own `ai-prompts/*.md` file —
linked below, not duplicated here.

## Methodology

Throughout this project, validation prioritized **known ground truth**
over "it ran without error":

- **Injected-issue counts and row counts** were the primary pass/fail
  criteria at every layer (e.g. exactly 50 `FAIL_NULL_EMAIL`, exactly
  10,000 Bronze customers).
- **Derived numbers were cross-checked mathematically** where possible —
  percentile splits (High-Value = exactly 20% of active customers),
  `SUM(customer_count)` invariants across Gold segmentation, chart
  magnitude vs. known per-day revenue — rather than trusting a single
  output value in isolation.
- **Generated code was read directly** after each Cursor session rather
  than trusting the tool's summary of what it produced.

## Environment / tooling incidents (not code bugs)

| Incident | Resolution | Full detail |
|---|---|---|
| `%run` failed on plain `.py` files | Use `runpy.run_path(..., init_globals={"spark": spark})` instead | [ai-prompts/bronze-layer.md](ai-prompts/bronze-layer.md) |
| Stale Databricks Git-folder sync (empty file content despite correct branch) | Manual Pull required before running | [ai-prompts/bronze-layer.md](ai-prompts/bronze-layer.md) |
| Line chart defaulted to MONTHLY date binning (~20× inflated revenue per point) | Switch X-axis Transform to WEEKLY; caught by cross-checking magnitude against known per-day revenue | [ai-prompts/dashboard.md](ai-prompts/dashboard.md) |

## Logic risks caught before running (pre-emptive hardening)

These were identified and patched into prompts **before** sending to
Cursor, not discovered via failed runs afterward:

| Risk | Layer | Full detail |
|---|---|---|
| NULL FK double-counted as orphan; join row-explosion from duplicate parent keys | Silver | [ai-prompts/silver-layer.md](ai-prompts/silver-layer.md) |
| LEFT JOIN silently becoming INNER JOIN via post-join WHERE; missing `COALESCE` on `SUM`; percentile diluted by zero-revenue customers | Gold | [ai-prompts/gold-layer.md](ai-prompts/gold-layer.md) |
| Gold-section DECIMAL precision guess could cause Delta schema-mismatch if written as executable DDL — made commented-out reference text instead | Documentation | [ai-prompts/documentation.md](ai-prompts/documentation.md) |
| Parameterized dashboard queries untestable via `spark.sql()`; missing `'All'` dropdown value | Dashboard | [ai-prompts/dashboard.md](ai-prompts/dashboard.md) |
| Test suite designed around regression invariants (NULL-vs-orphan mutual exclusivity, Gold segmentation sum), not just re-confirming known numbers | Tests | [ai-prompts/debugging.md](ai-prompts/debugging.md) |

## Reflection

The dominant debugging pattern in this project was **precision in the
prompt before code generation**, not iteration on broken output afterward.
Silver, Gold, Dashboard, Documentation, and the test suite each passed in
a single Cursor session with zero logic fix-iterations because known
failure modes (join semantics, NULL handling, schema precision, platform
behavior uncertainty) were anticipated and written into the prompt as
hard rules upfront. Given the Cursor budget constraint, investing review
time in prompt hardening proved more effective than relying on a
generate-then-fix loop — the few real issues that did surface (MONTHLY vs.
WEEKLY chart binning, Git-folder sync) were environment or platform
defaults, not logic bugs in the generated pipeline code.
