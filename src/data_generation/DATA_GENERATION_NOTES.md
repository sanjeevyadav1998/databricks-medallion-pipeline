# Data Generation Notes

Script: `src/data_generation/generate_sample_data.py`  
Output: `src/data_generation/data/` (`customers.csv`, `orders.csv`, `products.csv`)

## How data is generated

- **Reproducibility:** All randomness uses seed `42` via `random.Random`.
- **Libraries:** The script checks for `pandas` and `Faker` at import time. If neither is present, it falls back to the Python standard library (`csv`, `random`, `datetime`) — matching the current project environment.
- **Products (500 rows):** Clean primary keys `product_id` 1–500, synthetic names, eight retail categories, prices between roughly $10–$500, costs below price, and inventory fields (`stock_quantity`, `reorder_level`).
- **Customers (10,000 rows):** Primary keys nominally 1–10,000 with realistic names, emails, countries, signup dates, segments (`Premium` / `Standard` / `Basic`), and `lifetime_value` capped at 5,000. The last 10 rows reuse `customer_id` 1–10, so ids 9991–10000 appear only once in the initial pass and are replaced—9,990 distinct customer ids remain in the file.
- **Orders (100,000 rows):** Primary keys nominally 1–100,000. Clean rows draw `customer_id` from ids actually present in `customers.csv` (avoiding accidental orphans from duplicate PK injection). `quantity` 1–10, `unit_price` from the product catalog, and `total_amount = quantity × unit_price`. `payment_date` follows status rules: null for `Pending`, populated for `Completed`, optionally null for `Cancelled`.

## Intentional data quality issues

Each issue simulates a common upstream export or integration defect that the Silver layer should flag (never silently drop).

| Issue | Count | Where / why |
|-------|------:|-------------|
| NULL `email` (customers) | 50 | Rows 201–250 — mimics incomplete CRM signup or masked PII in a partial export. |
| Duplicate `customer_id` (customers) | 10 | Last 10 rows reuse `customer_id` 1–10 — simulates a bad merge or re-load appending rows instead of upserting. |
| NULL `customer_id` (orders) | 100 | First 100 order rows — guest checkout or ETL column mapping failure. |
| NULL `product_id` (orders) | 200 | Rows 101–300 — line-item feed missing product reference. |
| Orphan `customer_id` (orders) | 50 | Rows 301–350 use ids 10001–10050 — stale customer deleted in source but orders still reference them. |
| Orphan `product_id` (orders) | 30 | Rows 351–380 use ids 501–530 — discontinued SKU removed from catalog but historical orders retained. |
| Duplicate `order_id` (orders) | 20 | Rows 381–400 reuse `order_id` 1–20 — duplicate file append or retry without idempotency. |

Issue rows are placed in **disjoint index ranges** so each defect type is independently countable and testable in Silver (completeness, uniqueness, referential integrity).

Run verification:

```bash
python src/data_generation/generate_sample_data.py
```

The script prints total row counts and the measured count of each injected issue.
