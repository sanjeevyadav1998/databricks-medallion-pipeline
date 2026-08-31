-- Sales by Product: one row per PASSED product, including zero-order products.
-- ASSUMPTION: Only Completed orders count toward revenue; Pending is unrealized,
-- Cancelled is reversed — same filter applied in passed_orders below.

WITH passed_parent AS (
  SELECT *
  FROM workspace.default.silver_products
  WHERE quality_check_result = 'PASSED'
),
passed_orders AS (
  SELECT *
  FROM workspace.default.silver_orders
  WHERE quality_check_result = 'PASSED'
    AND order_status = 'Completed'
)
SELECT
  p.product_id,
  p.product_name,
  p.category,
  COUNT(o.order_id) AS total_orders,
  ROUND(COALESCE(SUM(o.total_amount), 0), 2) AS total_revenue,
  ROUND(
    COALESCE(SUM(o.total_amount), 0) / NULLIF(COUNT(o.order_id), 0),
    2
  ) AS avg_order_value
FROM passed_parent p
LEFT JOIN passed_orders o ON p.product_id = o.product_id
GROUP BY
  p.product_id,
  p.product_name,
  p.category
