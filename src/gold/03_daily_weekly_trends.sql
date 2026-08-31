-- Daily order/revenue trends with a Monday-start week column for dashboard rollups.
-- ASSUMPTION: Only Completed orders count toward revenue; Pending is unrealized,
-- Cancelled is reversed.
-- ASSUMPTION: Grain is one row per calendar day; order_week supports weekly
-- GROUP BY in the dashboard without a separate Gold table.

WITH passed_orders AS (
  SELECT *
  FROM workspace.default.silver_orders
  WHERE quality_check_result = 'PASSED'
    AND order_status = 'Completed'
)
SELECT
  o.order_date,
  date_trunc('week', o.order_date) AS order_week,
  COUNT(o.order_id) AS total_orders,
  ROUND(COALESCE(SUM(o.total_amount), 0), 2) AS total_revenue
FROM passed_orders o
GROUP BY
  o.order_date,
  date_trunc('week', o.order_date)
