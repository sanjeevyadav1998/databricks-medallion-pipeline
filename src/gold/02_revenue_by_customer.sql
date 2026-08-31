-- Revenue by Customer: one row per PASSED customer, including zero-order customers.
-- ASSUMPTION: Only Completed orders count toward revenue; Pending is unrealized,
-- Cancelled is reversed — same filter applied in passed_orders below.

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
)
SELECT
  c.customer_id,
  c.customer_name,
  c.customer_segment,
  COUNT(o.order_id) AS total_orders,
  ROUND(COALESCE(SUM(o.total_amount), 0), 2) AS total_revenue,
  ROUND(
    COALESCE(SUM(o.total_amount), 0) / NULLIF(COUNT(o.order_id), 0),
    2
  ) AS avg_order_value,
  ROUND(COALESCE(SUM(o.total_amount), 0), 2) AS lifetime_value_actual
FROM passed_parent c
LEFT JOIN passed_orders o ON c.customer_id = o.customer_id
GROUP BY
  c.customer_id,
  c.customer_name,
  c.customer_segment
