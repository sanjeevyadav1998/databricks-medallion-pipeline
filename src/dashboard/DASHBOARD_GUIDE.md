# Databricks SQL Dashboard — Wiring Guide

This guide walks through creating a Databricks SQL Dashboard from the four
read-only queries in `dashboard_queries.sql`. All tiles read **only** from
Gold-layer tables (`workspace.default.gold_*`); never query Silver or Bronze
directly from the dashboard.

**Prerequisites**

- Gold tables materialized via `src/gold/create_gold_tables.py`:
  - `workspace.default.gold_sales_by_product`
  - `workspace.default.gold_revenue_by_customer`
  - `workspace.default.gold_customer_segmentation`
  - `workspace.default.gold_daily_weekly_trends`
- Access to **Databricks SQL** (Free Edition) with Unity Catalog enabled.

---

## 1. Create the dashboard

1. In the Databricks workspace, open **SQL** → **Dashboards**.
2. Click **Create dashboard**, name it (e.g. `E-Commerce Sales Overview`), and save.
3. Open the dashboard editor. You will add **four datasets** (one per query) and
   **two filter widgets** (Category, Date Range).

---

## 2. Add datasets (one query per tile)

For each of the four queries in `dashboard_queries.sql`:

1. Click **Add** → **Query** (or **Add dataset**).
2. Copy the SQL block under the corresponding `-- QUERY N:` header (include only
   that query's `SELECT` — not the comment headers from other queries).
3. Set the **SQL warehouse** to your compute resource and run the query to confirm
   it returns rows (see [§7 Quick standalone test](#7-quick-standalone-test) for
   Queries 1 and 4, which need parameter placeholders resolved).
4. Save the dataset with a descriptive name matching the tile (e.g.
   `Top 10 Products by Revenue`).

Repeat for all four queries. Each tile will bind to its own saved dataset.

---

## 3. Tile configuration

### Tile 1 — Top 10 Products by Revenue (bar chart)

| Setting | Value |
|---|---|
| **Dataset** | Query 1 (`Top 10 Products by Revenue`) |
| **Visualization** | Bar chart |
| **X axis / Category** | `product_name` (or `product_id` if names are long) |
| **Y axis / Value** | `total_revenue` |
| **Optional series / color** | `category` |
| **Sort** | Already `ORDER BY total_revenue DESC LIMIT 10` in SQL — chart should show exactly **10 bars** when category = All |

**Filter widget:** Category dropdown (see [§4](#4-filter-widgets)).

---

### Tile 2 — Customer Revenue Distribution (histogram)

| Setting | Value |
|---|---|
| **Dataset** | Query 2 (`Customer Revenue Distribution`) |
| **Visualization** | Histogram |
| **Value column** | `total_revenue` |
| **Bin count** | 20–30 bins (adjust for readability; more bins show finer tail detail) |
| **No filter widget** | Intentionally omitted — see [§5](#5-queries-without-filter-widgets) |

The histogram must include customers with `total_revenue = 0` (zero-order
customers present in Gold). Do **not** add a `WHERE total_revenue > 0` clause;
that would truncate the left tail and misrepresent the distribution.

---

### Tile 3 — Customer Segmentation (pie chart)

| Setting | Value |
|---|---|
| **Dataset** | Query 3 (`Customer Segmentation`) |
| **Visualization** | Pie chart |
| **Slice labels / Category** | `segment_type` |
| **Slice values** | `customer_count` (primary) or `total_revenue` (alternate view) |
| **No filter widget** | Intentionally omitted — see [§5](#5-queries-without-filter-widgets) |

Gold returns exactly **four rows** (High-Value, Repeat, One-Time, Inactive).
All four slices should appear on the pie chart.

---

### Tile 4 — Daily/Weekly Revenue Trend (line chart)

| Setting | Value |
|---|---|
| **Dataset** | Query 4 (`Daily/Weekly Revenue Trend`) |
| **Visualization** | Line chart |
| **X axis** | `order_date` |
| **Y axis** | `total_revenue` (add a second line for `total_orders` if the UI supports dual series) |
| **Weekly view** | Prefer **date binning → Week** on the X axis in the visualization config (option **a**). The query returns daily grain; binning auto-aggregates `total_revenue` and `total_orders` by week using `order_date`. Only add a separate `GROUP BY order_week` query (option **b**) if your dashboard UI lacks date-binning. |
| **Sort** | Already `ORDER BY order_date` in SQL |

**Filter widget:** Date Range (see [§4](#4-filter-widgets)).

---

## 4. Filter widgets

Add two dashboard-level widgets and bind them to the query parameters in
Queries 1 and 4.

### Category dropdown (Query 1)

1. Click **Add filter** → choose **Dropdown** (or **Parameter** list).
2. **Parameter name:** `category` (must match `:category` in Query 1).
3. **Default value:** `All`.
4. **Value list source** — the Gold table does not contain a literal `'All'` row,
   so you must supply it explicitly. Use **one** of these approaches:

   **Option A — Static + dynamic (recommended):**
   - Manually add `All` as a static value in the widget configuration.
   - Populate remaining values from a helper query:

     ```sql
     SELECT DISTINCT category
     FROM workspace.default.gold_sales_by_product
     ORDER BY category
     ```

   **Option B — Single query including All:**

     ```sql
     SELECT 'All' AS category
     UNION ALL
     SELECT DISTINCT category
     FROM workspace.default.gold_sales_by_product
     ORDER BY category
     ```

5. Bind the widget to **Query 1's dataset** only. Query 1 SQL already handles
   the All case: `WHERE (:category = 'All' OR category = :category)`.

### Date Range (Query 4)

1. Click **Add filter** → choose **Date Range**.
2. **Parameter name:** `date_range` (must match `:date_range.min` and
   `:date_range.max` in Query 4).
3. Set sensible defaults (e.g. last 90 days or full range covered by sample data).
4. Bind the widget to **Query 4's dataset** only.

**Parameter syntax note:** This repo uses native placeholders
`:date_range.min` and `:date_range.max`. If your Databricks SQL Dashboard
version expects legacy Redash-style Jinja (`{{ date_range.start }}` /
`{{ date_range.end }}`), open the **Add filter** dialog, note the syntax it
shows, and update Query 4 accordingly before saving the dataset.

---

## 5. Queries without filter widgets

**Query 2 (histogram)** and **Query 3 (pie chart)** deliberately have **no**
filter widgets:

- **Query 2** must reflect the **full** customer revenue distribution, including
  zero-revenue customers. A revenue or segment filter would hide the inactive
  tail and distort the histogram shape.
- **Query 3** already aggregates to four segment buckets at Gold grain. Filters
  would either be redundant or collapse meaningful cross-segment comparison on
  a chart designed to show the whole customer base at a glance.

Only Query 1 (category slice for top products) and Query 4 (time window for
trends) benefit from interactive filtering.

---

## 6. Verification checklist

After wiring all tiles and widgets, confirm:

| Check | Expected result |
|---|---|
| Bar chart (Query 1) | Exactly **10 bars** when Category = All; fewer when a single category is selected |
| Category filter | Selecting **All** returns top 10 across all categories; selecting one category restricts to that category only |
| Histogram (Query 2) | Visible bar/bin count at **zero revenue** (left tail); total row count matches `gold_revenue_by_customer` |
| Pie chart (Query 3) | **4 slices**; sum of `customer_count` equals total PASSED customers in Gold segmentation |
| Line chart (Query 4) | Points plot in chronological order; date range widget narrows the X axis without errors |
| Layer boundary | No tile queries reference `silver_*` or `bronze_*` tables |
| Read-only | Dashboard does not `CREATE`, `INSERT`, or `ALTER` any table |

---

## 7. Quick standalone test

Queries **2** and **3** have no parameters — paste them into a SQL notebook
cell or the SQL editor and run as-is against your warehouse.

Queries **1** and **4** contain `:category` and `:date_range` placeholders
that only resolve inside a Databricks SQL Dashboard widget context. Running
`dashboard_queries.sql` wholesale via `spark.sql()` or the SQL editor **will
fail or behave unexpectedly** on those two queries.

To sanity-check base logic **before** wiring the dashboard:

1. Copy Query 1 or Query 4 into a throwaway SQL cell.
2. Replace placeholders with literals, e.g.:
   - Query 1: `WHERE category = 'Electronics'` (or remove the WHERE to see all)
   - Query 4: `WHERE order_date BETWEEN DATE '2024-01-01' AND DATE '2024-12-31'`
3. Run and inspect row counts / values.
4. **Do not commit** the literal-value version — it is for local testing only.

Restore parameter placeholders before saving the dataset in the dashboard UI.
