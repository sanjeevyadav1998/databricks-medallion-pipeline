# Data Model

Conceptual overview of the e-commerce sales entities and how they evolve
across the medallion layers. For exact column-level DDL, see
[database/schema.sql](database/schema.sql). For CSV-to-Bronze column
mapping, see [database/seed-data-notes.md](database/seed-data-notes.md).

## Entity relationships

This is a classic star-schema shape at the transaction grain:

```
customers (1) ──────< orders >────── (1) products
```

- **customers** relate one-to-many to **orders** via `customer_id`.
- **products** relate one-to-many to **orders** via `product_id`.
- **orders** is the fact table (one row per purchase transaction);
  **customers** and **products** are dimension tables.

## Business meaning

| Entity | Meaning |
|---|---|
| **customers** | Who buys — registered shoppers with profile and segment attributes. |
| **products** | What's sold — catalog items with pricing, cost, and inventory fields. |
| **orders** | Each purchase transaction — links a customer to a product with quantity, pricing, status, and payment timing. |

## How the model changes across layers

| Layer | Shape | Purpose |
|---|---|---|
| **Bronze** | Raw entities as ingested — `bronze_customers`, `bronze_orders`, `bronze_products` with no cleaning or filtering. | Faithful copy of source CSVs, including intentional quality defects. |
| **Silver** | Same three entities, same row counts, plus `quality_check_result` on every row. | Validation and flagging — bad rows are marked, never deleted. |
| **Gold** | Four aggregated business views derived from Silver's PASSED rows and Completed orders only — no entity tables at transaction grain. | Analytics-ready metrics: sales by product, revenue by customer, daily/weekly trends, customer segmentation. |
| **Dashboard** | Read-only queries against Gold tables. | Visualization layer; no new tables written. |

Gold tables:

- `gold_sales_by_product` — product-level order and revenue rollups.
- `gold_revenue_by_customer` — customer-level order and revenue rollups.
- `gold_daily_weekly_trends` — time-series revenue by calendar day (with a week label column).
- `gold_customer_segmentation` — customers grouped into derived behavioral tiers.

## Derived concepts (not in source CSVs)

Two important fields are **computed by the pipeline**, not present in the
original seed data:

1. **`quality_check_result`** (Silver) — appended to every Silver table.
   Indicates whether a row passed all quality checks (`'PASSED'`) or which
   `FAIL_*` codes apply. See [data-quality-strategy.md](data-quality-strategy.md)
   for the check framework.

2. **`segment_type`** (Gold) — behavioral customer tier assigned in
   `gold_customer_segmentation` via priority-ordered logic: High-Value →
   Repeat → One-Time → Inactive. This is **not** the same as the existing
   `customer_segment` column (Premium / Standard / Basic) that arrives
   with the customer record — that column is preserved as-is through Bronze
   and Silver and appears on `gold_revenue_by_customer`, while `segment_type`
   is a separate Gold-layer derivation based on actual order history.
