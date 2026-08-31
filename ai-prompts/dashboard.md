# AI Prompts — Dashboard

## Session 1 — Design decisions locked before drafting
**Tool / mode:** Claude (spec drafting), not yet sent to Cursor.
Locked three judgment calls the source requirements don't specify: (1) data
source — Dashboard reads ONLY from Gold tables, never Silver/Bronze, per
this repo's own spec.md rule "each layer reads only from the layer directly
below it"; (2) a 4th query/tile (daily/weekly trend line chart) added beyond
the 3 required (bar/histogram/pie), since gold_daily_weekly_trends already
existed as the Gold layer's 4th aggregation and would otherwise go unused;
(3) 2 interactive filter widgets — category dropdown on the bar chart,
date range on the trend line chart — with Histogram and Pie intentionally
left unfiltered (full-distribution and small-fixed-set requirements).

## Session 2 — Pre-emptive hardening (4 review passes before running)
Before sending the prompt to Cursor, reviewed it four separate times for
issues specific to Databricks SQL Dashboard mechanics:

1. Hedge on `:category` widget-binding syntax uncertainty (SQL parameter
   placeholder syntax varies by Databricks SQL Dashboard version).
2. Matching hedge added for `:date_range.min`/`.max` (legacy Redash-style
   Jinja templating `{{ date_range.start }}` / `{{ date_range.end }}` vs.
   native `:param` notation) — this one was originally missed on the first
   pass and added on a second pass for consistency.
3. Flagged that a plain `SELECT DISTINCT category` would never produce a
   literal `'All'` row for the dropdown's "show everything" option — added
   both a manual-static-value option and a `UNION ALL` query alternative.
4. Flagged that Query 4 returns daily-grain rows with `order_week` as a
   label column, not a pre-aggregated weekly rollup, and that getting a
   weekly *view* should default to the chart's own date-binning config
   rather than requiring a second query.
5. Flagged that Queries 1 and 4 (parameterized) can't be tested the same
   way Bronze/Silver/Gold were (`spark.sql()` won't resolve `:category`/
   `:date_range` placeholders) and added a throwaway-literal-value testing
   note instead.

Also verified an environment precondition before running anything: confirmed
via screenshot that a Databricks SQL Warehouse ("Serverless Starter
Warehouse") and Dashboards tab were actually available in the account,
rather than assuming Free Edition included Databricks SQL.

## Session 3 — Final prompt sent to Cursor
**Tool / mode:** Cursor, Agent mode.

**Prompt (verbatim):**

Write the BI dashboard queries and guide per tool-specific/cursor-workflow/spec.md section 5 and .cursorrules layer boundaries. Databricks SQL Dashboard (Free Edition, Unity Catalog three-level namespace: catalog.schema.table).

SOURCE TABLES (workspace.default — Dashboard reads ONLY from Gold, never from Silver or Bronze, per the architecture rule "each layer reads only from the layer directly below it"):
- workspace.default.gold_sales_by_product
- workspace.default.gold_revenue_by_customer
- workspace.default.gold_customer_segmentation
- workspace.default.gold_daily_weekly_trends

No target tables — this layer only produces queries for dashboard tiles, it does not write any Delta table.

FILES TO CREATE:

1. src/dashboard/dashboard_queries.sql — exactly 4 named queries, each preceded by a "-- QUERY N: <title> (<chart type>)" comment header so it's easy to paste each into a separate Databricks SQL Dashboard tile.

   QUERY 1: Top 10 Products by Revenue (bar chart)
   - SELECT product_id, product_name, category, total_orders, total_revenue, avg_order_value FROM workspace.default.gold_sales_by_product.
   - Add a category filter widget: WHERE (:category = 'All' OR category = :category)
   - ORDER BY total_revenue DESC LIMIT 10.
   - ASSUMPTION: :category widget default value is 'All'; exact widget-binding syntax may need minor adjustment once wired in the Databricks SQL Dashboard UI (the SQL parameter placeholder is standardized, but the dropdown's value list/default is configured in the UI, not in this file).

   QUERY 2: Customer Revenue Distribution (histogram)
   - SELECT customer_id, customer_name, customer_segment, total_revenue FROM workspace.default.gold_revenue_by_customer.
   - No filter widget on this query — histogram should reflect the full customer revenue distribution, including customers with total_revenue = 0 (zero-order customers, verified present in Gold), since excluding them would misrepresent the true distribution shape.

   QUERY 3: Customer Segmentation (pie chart)
   - SELECT segment_type, customer_count, avg_revenue, total_revenue FROM workspace.default.gold_customer_segmentation.
   - No filter needed — only 4 rows total, pie chart shows all segments.

   QUERY 4: Daily/Weekly Revenue Trend (line chart)
   - SELECT order_date, order_week, total_orders, total_revenue FROM workspace.default.gold_daily_weekly_trends.
   - Add a date range filter widget: WHERE order_date BETWEEN :date_range.min AND :date_range.max
   - ORDER BY order_date.
   - ASSUMPTION: this 4th query/tile is included because gold_daily_weekly_trends already exists as the project's 4th Gold aggregation; the source requirements only mandate 3 tiles (bar/histogram/pie), so this is an addition, not a replacement of any required tile.
   - ASSUMPTION: :date_range.min / :date_range.max is the native-parameter syntax; some Databricks SQL Dashboard versions use legacy Redash-style Jinja templating instead ({{ date_range.start }} / {{ date_range.end }}). Whichever syntax the actual dashboard UI expects, use that one instead — verify against the live "Add filter" widget dialog before finalizing.
   - This query returns DAILY grain rows (one per order_date), with order_week included as a label column, not a pre-aggregated weekly rollup. Getting a weekly view means either (a) setting the chart's X-axis date binning to "week" in the Databricks visualization config, which auto-aggregates the already-selected total_revenue/total_orders, or (b) writing a second query that does GROUP BY order_week instead of order_date. Default to (a) in DASHBOARD_GUIDE.md since it needs no second query; only add (b) if the chart's date-binning option isn't available in the actual dashboard UI.

2. src/dashboard/DASHBOARD_GUIDE.md — step-by-step guide for wiring these 4 queries into an actual Databricks SQL Dashboard:
   - How to create a new Databricks SQL Dashboard and add each query as a dataset.
   - For each of the 4 tiles: which chart type to select in the Databricks UI (bar, histogram, pie, line), which column maps to X/Y axis or category/value, and any chart-specific config (e.g. bin count for the histogram).
   - How to configure the two widgets: a "Category" dropdown widget bound to the :category parameter in Query 1. IMPORTANT: a plain SELECT DISTINCT category FROM workspace.default.gold_sales_by_product will never produce a row literally equal to 'All' — either add 'All' as a manually-entered static value in the widget's value list (in addition to the dynamic query-based values), or change the source list to SELECT 'All' AS category UNION ALL SELECT DISTINCT category FROM workspace.default.gold_sales_by_product, so the "show everything" option actually exists and is selectable. Also configure a "Date Range" widget bound to the :date_range parameter in Query 4.
   - Note that Query 2 and Query 3 intentionally have no filter widgets, and why.
   - A short "how to verify it renders correctly" checklist (e.g. bar chart shows exactly 10 bars, pie chart's 4 slices sum to the total PASSED customer count, histogram includes the zero-revenue tail).
   - A "quick standalone test" note: Queries 1 and 4 contain :category / :date_range placeholders that only resolve inside an actual Databricks SQL Dashboard widget context — running dashboard_queries.sql directly via spark.sql() (the same way Bronze/Silver/Gold were tested) will fail or behave unexpectedly on those two queries. To sanity-check the base query logic before wiring the real dashboard, temporarily replace the parameter placeholder with a literal value (e.g. WHERE category = 'Electronics', or a literal date range) and run that adjusted copy in a SQL cell — do not commit that literal-value version, it's a throwaway test only. Queries 2 and 3 have no parameters and can be run as-is.

HARD RULES:
- Every query reads ONLY from workspace.default.gold_* tables — never workspace.default.silver_* or bronze_* directly. Gold has already applied all PASSED/Completed filtering; do not re-filter by quality_check_result or order_status here, since those columns don't exist on Gold tables.
- Do not write, create, or alter any table from this layer — read-only queries.
- Do not add a filter widget to Query 2 or Query 3 — only Query 1 (category) and Query 4 (date range) get widgets, per the design above.
- Use "-- ASSUMPTION:" SQL comments only for judgment calls not covered by this prompt.

Do not touch any other files.

**Result:** Accepted on first generation, no fix-iteration needed. Code
review confirmed all 4 queries and both files matched the prompt exactly:
correct source tables, correct ASSUMPTION comments, correct filter
placement (only Queries 1 and 4).

## Debugging — validating the built dashboard against actual platform behavior
Three substantive findings surfaced only when actually building and
testing the dashboard, none of them SQL or prompt errors:

1. **Line chart defaulted to MONTHLY date binning** — the X-axis field's
   "Transform" setting defaulted to MONTHLY, producing per-point revenue
   sums of ~$3.2–3.8M (roughly 20x the actual ~$150K/day figure) that
   looked wrong until the Transform was manually switched to WEEKLY,
   producing the expected ~$700K–$1M per-point range (~7 days ×
   ~$150K/day). Confirmed correct after the switch, including a
   legitimately partial first week at the start of the data range. This
   was caught by cross-checking chart magnitude against the known
   per-day revenue figures already validated during the Gold layer step,
   not by assuming the default rendering was correct.
2. **The `'All'` dropdown concern turned out to be moot** — Databricks
   Lakeview's native "Filters → Fields" panel auto-detected the `category`
   column referenced in the SQL's `:category` parameter and built a value
   list that already included a literal "All" option alongside the real
   category values (Beauty, Electronics, Groceries, Toys, etc.), with no
   manual static-value addition or `UNION ALL` query needed. The
   hardening fix in the prompt (documenting both workarounds) turned out
   to be unnecessary in practice, though it was the right call to flag it
   proactively rather than assume the platform would handle it — the
   platform happened to handle it, but that wasn't guaranteed in advance.
3. **The `:date_range`/`:category` SQL parameter placeholders ended up
   unused in the live dashboard** — Databricks Lakeview's per-widget
   "Filters" panel (Fields → category / order_date) drives the actual
   interactive filtering directly at the platform level, independent of
   whatever literal WHERE clause is in the query text. The live dataset's
   WHERE clauses were commented out during testing and never needed to be
   restored — the checked-in repo file (dashboard_queries.sql) still
   contains the original parameterized version documenting the intended
   design, but the platform's native filter mechanism is what's actually
   driving the published dashboard's interactivity.

## Validation
Built and published the dashboard ("E-Commerce Sales Overview") using the
Serverless Starter Warehouse, confirmed via screenshots at each stage:

- **Tile 1 (bar):** exactly 10 bars, `product_name` / `total_revenue`.
- **Tile 2 (histogram):** full `total_revenue` distribution, 0–35K range,
  includes the zero-revenue tail.
- **Tile 3 (pie):** 4 segments in the legend (Repeat, High-Value, One-Time,
  Inactive); only 2 slices are visually distinguishable since One-Time
  (25) and Inactive (5) are each under 0.3% of the ~9,940 total — expected
  given the Gold-layer validation math done earlier, not a rendering bug.
- **Tile 4 (line, weekly binning):** ~$700K–$1M per week, consistent with
  ~7 × ~$150K/day; date range filter correctly narrows only this tile
  without affecting the other three.
- **Category filter:** native dropdown includes "All" plus real category
  values; confirmed scoped only to Tile 1.
- **Date range filter:** confirmed scoped only to Tile 4, tested by
  narrowing to "Last year" and observing the chart's window and revenue
  scale both update correctly while other tiles stayed unchanged.

## Root cause / lesson
The pre-emptive hardening passes correctly anticipated real risks (widget
syntax ambiguity, the missing 'All' value, daily-vs-weekly confusion,
untestable parameterized queries) even though the platform's native filter
mechanism ultimately resolved two of them automatically without needing
the documented workaround. Flagging uncertainty explicitly up front, rather
than guessing a single "definitely correct" answer for platform behavior
that can't be verified without the live product, avoided wasted Cursor
iterations — the SQL and guide were accepted in one pass, and the one real
correctness bug found (MONTHLY vs. WEEKLY binning) was caught by
cross-checking the rendered chart's magnitude against numbers already
validated in the Gold layer step, not by assuming the UI's default was right.

## Status: ACCEPTED (1 code session, 0 logic fix-iterations, dashboard built, wired, and published with all 4 tiles and 2 filters verified against expected data)
