-- Dashboard queries for Databricks SQL Dashboard (read-only, Gold layer only).
-- Each query is intended to be pasted into its own dashboard tile as a separate dataset.
-- Unity Catalog namespace: workspace.default.gold_*

-- QUERY 1: Top 10 Products by Revenue (bar chart)
-- ASSUMPTION: :category widget default value is 'All'; exact widget-binding
-- syntax may need minor adjustment once wired in the Databricks SQL Dashboard UI.
SELECT
  product_id,
  product_name,
  category,
  total_orders,
  total_revenue,
  avg_order_value
FROM workspace.default.gold_sales_by_product
WHERE (:category = 'All' OR category = :category)
ORDER BY total_revenue DESC
LIMIT 10;

-- QUERY 2: Customer Revenue Distribution (histogram)
SELECT
  customer_id,
  customer_name,
  customer_segment,
  total_revenue
FROM workspace.default.gold_revenue_by_customer;

-- QUERY 3: Customer Segmentation (pie chart)
SELECT
  segment_type,
  customer_count,
  avg_revenue,
  total_revenue
FROM workspace.default.gold_customer_segmentation;

-- QUERY 4: Daily/Weekly Revenue Trend (line chart)
-- ASSUMPTION: :date_range.min / :date_range.max is the native-parameter syntax;
-- some Databricks SQL Dashboard versions use legacy Redash-style Jinja templating
-- instead ({{ date_range.start }} / {{ date_range.end }}). Verify against the
-- live "Add filter" widget dialog before finalizing.
-- ASSUMPTION: This tile is an addition beyond the three required tiles (bar,
-- histogram, pie); gold_daily_weekly_trends already exists as the 4th Gold table.
SELECT
  order_date,
  order_week,
  total_orders,
  total_revenue
FROM workspace.default.gold_daily_weekly_trends
WHERE order_date BETWEEN :date_range.min AND :date_range.max
ORDER BY order_date;
