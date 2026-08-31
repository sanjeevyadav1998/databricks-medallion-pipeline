-- Customer Segmentation: High-Value / Repeat / One-Time / Inactive buckets.
-- ASSUMPTION: Only Completed orders count toward revenue; Pending is unrealized,
-- Cancelled is reversed — same filter applied in passed_orders below.
-- ASSUMPTION: 80th percentile of total_revenue (among customers with at least one
-- completed order) is the High-Value cutoff; tune this threshold if product changes.

WITH passed_parent AS (
  SELECT *
  FROM workspace.default.silver_customers
  WHERE quality_check_result = 'PASSED'
),
passed_orders AS (
  SELECT *
  FROM workspace.default.silver_orders
  WHERE quality_check_result = 'PASSED'
    AND order_status = 'Completed'
),
per_customer AS (
  SELECT
    c.customer_id,
    COUNT(o.order_id) AS total_orders,
    COALESCE(SUM(o.total_amount), 0) AS total_revenue
  FROM passed_parent c
  LEFT JOIN passed_orders o ON c.customer_id = o.customer_id
  GROUP BY c.customer_id
),
percentile_threshold AS (
  SELECT
    PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY total_revenue) AS high_value_threshold
  FROM per_customer
  WHERE total_orders > 0
),
segmented AS (
  SELECT
    pc.customer_id,
    pc.total_orders,
    pc.total_revenue,
    CASE
      WHEN pc.total_revenue >= pt.high_value_threshold THEN 'High-Value'
      WHEN pc.total_orders >= 2 THEN 'Repeat'
      WHEN pc.total_orders = 1 THEN 'One-Time'
      ELSE 'Inactive'
    END AS segment_type
  FROM per_customer pc
  CROSS JOIN percentile_threshold pt
)
SELECT
  segment_type,
  COUNT(*) AS customer_count,
  ROUND(AVG(total_revenue), 2) AS avg_revenue,
  ROUND(SUM(total_revenue), 2) AS total_revenue
FROM segmented
GROUP BY segment_type
