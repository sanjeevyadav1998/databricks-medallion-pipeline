# Project Context (paste-ready for Cursor)

Use this as the opening context for any new Cursor chat/session in this repo,
alongside the `.cursorrules` file (which Cursor should already pick up
automatically from the repo root).

---

**Project:** Databricks medallion architecture pipeline for an e-commerce
company's daily sales data (customer database, order system, product catalog).

**Goal:** Bronze (raw ingest) → Silver (data quality validation) → Gold
(business aggregations) → Dashboard (BI visualizations), built on Databricks
Community Edition using PySpark, Delta Lake, and SQL.

**Data sources (CSV, S3/DBFS-style paths):**
- `customers.csv` — 10,000 rows. Fields: `customer_id` (INT, PK),
  `customer_name` (STRING), `email` (STRING), `country` (STRING),
  `signup_date` (DATE), `customer_segment` (STRING:
  Premium/Standard/Basic), `lifetime_value` (DECIMAL).
- `orders.csv` — 100,000 rows. Fields: `order_id` (INT, PK), `customer_id`
  (INT, FK → customers), `order_date` (DATE), `product_id` (INT, FK →
  products), `quantity` (INT), `unit_price` (DECIMAL), `total_amount`
  (DECIMAL), `order_status` (STRING: Pending/Completed/Cancelled),
  `payment_date` (DATE, nullable).
- `products.csv` — 500 rows. Fields: `product_id` (INT, PK), `product_name`
  (STRING), `category` (STRING), `price` (DECIMAL), `cost` (DECIMAL),
  `stock_quantity` (INT), `reorder_level` (INT).

**Intentional data quality issues to be generated (and later caught in
Silver):**
- customers: 50 rows NULL email, 10 rows duplicate `customer_id`
- orders: 100 rows NULL `customer_id`, 200 rows NULL `product_id`,
  50 rows `customer_id` not in customers, 30 rows `product_id` not in
  products, 20 duplicate `order_id` rows
- Total ~700 problematic rows out of ~100,000 (~0.7%)

**Silver-layer quality checks required (exactly 4):**
1. Completeness — no NULLs in `email`, `customer_id`, `product_id`
2. Uniqueness — no duplicate `order_id`, `customer_id`
3. Referential integrity — every `customer_id`/`product_id` exists in parent table
4. (Type validation / business-logic check — see individual component prompt)

Bad rows are flagged via a `quality_check_result` column, never deleted.

**Gold-layer aggregations required (exactly 3):**
1. Sales by Product — `product_id, product_name, category, total_orders,
   total_revenue, avg_order_value`
2. Revenue by Customer — `customer_id, customer_name, customer_segment,
   total_orders, total_revenue, avg_order_value, lifetime_value_actual`
3. Customer Segmentation — `segment_type
   (High-Value/Repeat/One-Time/Inactive), customer_count, avg_revenue,
   total_revenue`

**Dashboard:** 3+ tiles — Top 10 products by revenue (bar), customer revenue
distribution (histogram), customer segmentation (pie).

**Repo structure:** See `README.md` / repo root for the full required file
layout. Every component should land in its exact specified filename under
`src/<layer>/`.

**Constraint:** This is a training/capability exercise with a small,
intentionally-bounded scope — do not over-engineer beyond what's asked.
