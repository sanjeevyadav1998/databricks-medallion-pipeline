-- =============================================================================
-- SCHEMA REFERENCE — Databricks Medallion Pipeline (e-commerce sales)
-- =============================================================================
--
-- This file documents the schema that the pipeline scripts create via
-- `.saveAsTable(...)` in src/bronze/, src/silver/, and src/gold/. It is NOT
-- part of the normal setup flow and is not executed by any project script.
--
-- Bronze and Silver sections below use known, exact column types (matching the
-- literal DDL strings in the Bronze ingestion scripts) and are safe to run
-- standalone if desired. The Gold section is intentionally commented out and
-- must never be uncommented and run before create_gold_tables.py has
-- established the real column types — Spark infers DECIMAL precision/scale for
-- computed columns at write time, and a hand-written guess could cause a
-- schema-mismatch error on subsequent `.saveAsTable(mode="overwrite")` calls.
--
-- Unity Catalog namespace: workspace.default.<table_name>
-- Storage format: Delta Lake
-- =============================================================================


-- -----------------------------------------------------------------------------
-- BRONZE LAYER (raw ingest, no transformation)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workspace.default.bronze_customers (
    customer_id INT,
    customer_name STRING,
    email STRING,
    country STRING,
    signup_date DATE,
    customer_segment STRING,
    lifetime_value DECIMAL(10,2)
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.default.bronze_orders (
    order_id INT,
    customer_id INT,
    order_date DATE,
    product_id INT,
    quantity INT,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    order_status STRING,
    payment_date DATE
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.default.bronze_products (
    product_id INT,
    product_name STRING,
    category STRING,
    price DECIMAL(10,2),
    cost DECIMAL(10,2),
    stock_quantity INT,
    reorder_level INT
)
USING DELTA;


-- -----------------------------------------------------------------------------
-- SILVER LAYER (validated + quality_check_result appended)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS workspace.default.silver_customers (
    customer_id INT,
    customer_name STRING,
    email STRING,
    country STRING,
    signup_date DATE,
    customer_segment STRING,
    lifetime_value DECIMAL(10,2),
    quality_check_result STRING
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.default.silver_orders (
    order_id INT,
    customer_id INT,
    order_date DATE,
    product_id INT,
    quantity INT,
    unit_price DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    order_status STRING,
    payment_date DATE,
    quality_check_result STRING
)
USING DELTA;

CREATE TABLE IF NOT EXISTS workspace.default.silver_products (
    product_id INT,
    product_name STRING,
    category STRING,
    price DECIMAL(10,2),
    cost DECIMAL(10,2),
    stock_quantity INT,
    reorder_level INT,
    quality_check_result STRING
)
USING DELTA;


-- -----------------------------------------------------------------------------
-- GOLD LAYER (business aggregations, PASSED+Completed orders only)
-- (reference only — DO NOT run this section)
-- -----------------------------------------------------------------------------

-- CREATE TABLE IF NOT EXISTS workspace.default.gold_sales_by_product (
--     product_id INT,
--     product_name STRING,
--     category STRING,
--     total_orders BIGINT,
--     total_revenue DECIMAL(38,2),  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_sales_by_product if byte-exact matching is required
--     avg_order_value DECIMAL(38,2)  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_sales_by_product if byte-exact matching is required
-- )
-- USING DELTA;

-- CREATE TABLE IF NOT EXISTS workspace.default.gold_revenue_by_customer (
--     customer_id INT,
--     customer_name STRING,
--     customer_segment STRING,
--     total_orders BIGINT,
--     total_revenue DECIMAL(38,2),  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_revenue_by_customer if byte-exact matching is required
--     avg_order_value DECIMAL(38,2),  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_revenue_by_customer if byte-exact matching is required
--     lifetime_value_actual DECIMAL(38,2)  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_revenue_by_customer if byte-exact matching is required
-- )
-- USING DELTA;

-- CREATE TABLE IF NOT EXISTS workspace.default.gold_daily_weekly_trends (
--     order_date DATE,
--     order_week TIMESTAMP,
--     total_orders BIGINT,
--     total_revenue DECIMAL(38,2)  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_daily_weekly_trends if byte-exact matching is required
-- )
-- USING DELTA;

-- CREATE TABLE IF NOT EXISTS workspace.default.gold_customer_segmentation (
--     segment_type STRING,
--     customer_count BIGINT,
--     avg_revenue DECIMAL(38,2),  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_customer_segmentation if byte-exact matching is required
--     total_revenue DECIMAL(38,2)  -- ASSUMPTION: exact precision/scale may differ from live table; verify via DESCRIBE TABLE workspace.default.gold_customer_segmentation if byte-exact matching is required
-- )
-- USING DELTA;
